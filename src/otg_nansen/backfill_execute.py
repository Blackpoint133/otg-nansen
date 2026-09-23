"""Double-gated, staging-only runner for bounded canonical flow batches.

Without both ``--execute`` and ``NANSEN_RUN_LIVE_BACKFILL=1`` this module is
read-only and refuses live execution. Each unit gets a fresh one-attempt client.
"""

from __future__ import annotations

import argparse
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from typing import Any

from .backfill import (
    BackfillExecutionError,
    execute_pending_units,
    inspect_plan_progress,
)
from .backfill_plan import build_canonical_plan, _wire
from .client import NansenClient
from .config import NansenConfig
from .ingestion import IngestionWindow, NansenIngestionOrchestrator
from .postgres import (
    ALLOWED_STAGING_DATABASE,
    PostgresRepository,
    _load_dotenv_if_present,
    staging_connection_kwargs,
    verify_staging_target,
)
from .source_warnings import NON_EXCHANGE_BREAKDOWN_UNAVAILABLE


class SourceCoverageGap(BackfillExecutionError):
    """A successfully committed unit failed required structural coverage."""


ABSOLUTE_MAX_UNITS_PER_INVOCATION = 20
ABSOLUTE_MAX_LIVE_CALLS_PER_INVOCATION = 20
MAX_CALLS_PER_UNIT = 1

TASK028_EXPECTED_BOUNDS = (
    (4, "2025-05-15T21:00:00Z", "2025-05-22T19:00:00Z", "2025-05-15T20:00:00Z", "2025-05-22T19:59:59Z"),
    (5, "2025-05-22T20:00:00Z", "2025-05-29T18:00:00Z", "2025-05-22T19:00:00Z", "2025-05-29T18:59:59Z"),
    (6, "2025-05-29T19:00:00Z", "2025-06-05T17:00:00Z", "2025-05-29T18:00:00Z", "2025-06-05T17:59:59Z"),
    (7, "2025-06-05T18:00:00Z", "2025-06-12T16:00:00Z", "2025-06-05T17:00:00Z", "2025-06-12T16:59:59Z"),
    (8, "2025-06-12T17:00:00Z", "2025-06-19T15:00:00Z", "2025-06-12T16:00:00Z", "2025-06-19T15:59:59Z"),
    (9, "2025-06-19T16:00:00Z", "2025-06-26T14:00:00Z", "2025-06-19T15:00:00Z", "2025-06-26T14:59:59Z"),
    (10, "2025-06-26T15:00:00Z", "2025-07-03T13:00:00Z", "2025-06-26T14:00:00Z", "2025-07-03T13:59:59Z"),
    (11, "2025-07-03T14:00:00Z", "2025-07-10T12:00:00Z", "2025-07-03T13:00:00Z", "2025-07-10T12:59:59Z"),
    (12, "2025-07-10T13:00:00Z", "2025-07-17T11:00:00Z", "2025-07-10T12:00:00Z", "2025-07-17T11:59:59Z"),
    (13, "2025-07-17T12:00:00Z", "2025-07-24T10:00:00Z", "2025-07-17T11:00:00Z", "2025-07-24T10:59:59Z"),
)


def execution_enabled(cli_opt_in: bool, environ: dict[str, str] | None = None) -> bool:
    env = os.environ if environ is None else environ
    return cli_opt_in and env.get("NANSEN_RUN_LIVE_BACKFILL") == "1"


def validate_invocation_limits(max_units: int, max_live_calls: int) -> None:
    if not isinstance(max_units, int) or isinstance(max_units, bool) or not 1 <= max_units <= ABSOLUTE_MAX_UNITS_PER_INVOCATION:
        raise BackfillExecutionError("max_units exceeds the per-invocation limit")
    if not isinstance(max_live_calls, int) or isinstance(max_live_calls, bool) or not 1 <= max_live_calls <= ABSOLUTE_MAX_LIVE_CALLS_PER_INVOCATION:
        raise BackfillExecutionError("max_live_calls exceeds the per-invocation limit")
    if max_live_calls < max_units:
        raise BackfillExecutionError("max_live_calls must be at least max_units for one call per unit")


def select_authorized_units(plan, progress, *, max_units: int, max_live_calls: int,
                            expected_complete_before: int, expected_first_pending_index: int):
    validate_invocation_limits(max_units, max_live_calls)
    if progress.ambiguous:
        raise BackfillExecutionError("ambiguous progress blocks live execution")
    if progress.complete != expected_complete_before:
        raise BackfillExecutionError("persisted completion count differs from the authorization")
    pending = [unit for unit in plan.units if progress.statuses[unit.unit_id] == "PENDING"]
    if not pending or pending[0].index != expected_first_pending_index:
        raise BackfillExecutionError("first pending unit differs from the authorization")
    selected = tuple(pending[:max_units])
    if len(selected) != max_units:
        raise BackfillExecutionError("not enough pending units for the authorized batch")
    if tuple(unit.index for unit in selected) != tuple(range(expected_first_pending_index, expected_first_pending_index + max_units)):
        raise BackfillExecutionError("authorized pending units are not a contiguous canonical batch")
    return selected


def validate_task028_bounds(units) -> None:
    actual = tuple((unit.index, _wire(unit.coverage_start), _wire(unit.coverage_end),
                    _wire(unit.request_start), _wire(unit.request_end)) for unit in units)
    if actual != TASK028_EXPECTED_BOUNDS:
        raise BackfillExecutionError("selected canonical bounds differ from Task 028 authorization")


def expected_progress_after(progress_before, successful_units: int) -> tuple[int, int, int]:
    return (progress_before.complete + successful_units,
            progress_before.pending - successful_units, 0)


def should_stop_for_resource_pressure(snapshot, *, successful_units: int, selected_units: int) -> bool:
    return successful_units < selected_units and _resource_pressure(snapshot)


def first_pending_index(plan, statuses) -> int | None:
    return next((unit.index for unit in plan.units if statuses.get(unit.unit_id, "PENDING") == "PENDING"), None)


def _readonly_connection():
    import psycopg

    kwargs = staging_connection_kwargs()
    kwargs["options"] = "-c default_transaction_read_only=on"
    connection = psycopg.connect(**kwargs)
    identity = verify_staging_target(connection)
    if identity != {
        "database": ALLOWED_STAGING_DATABASE,
        "user": "gunz_user",
        "transaction_read_only": "on",
    }:
        connection.close()
        raise RuntimeError("read-only staging identity check failed")
    return connection


def _assert_writable_staging(repository: PostgresRepository) -> None:
    for connection in (repository.audit_connection, repository.data_connection):
        identity = verify_staging_target(connection)
        if identity != {
            "database": ALLOWED_STAGING_DATABASE,
            "user": "gunz_user",
            "transaction_read_only": "off",
        }:
            raise RuntimeError("writable staging identity check failed")


def _progress(plan):
    connection = _readonly_connection()
    try:
        return inspect_plan_progress(connection, plan)
    finally:
        connection.close()


def _target_counts(connection, units) -> dict[str, Any]:
    start, end = units[0].coverage_start, units[-1].coverage_end
    counts = connection.execute(
        """SELECT count(*), count(DISTINCT (chain, token_address, flow_label, date, bucket_end)),
                  count(*) FILTER (WHERE bucket_end - date = interval '1 hour'),
                  count(*) FILTER (WHERE bucket_end - date = interval '24 hours')
           FROM nansen.flows WHERE chain=%s AND token_address=%s AND flow_label=%s
             AND date BETWEEN %s AND %s""",
        (units[0].chain, units[0].token_address, units[0].flow_label, start, end),
    ).fetchone()
    keys = connection.execute(
        """SELECT chain, token_address, flow_label, date, bucket_end
           FROM nansen.flows WHERE chain=%s AND token_address=%s AND flow_label=%s
             AND date BETWEEN %s AND %s AND bucket_end - date = interval '1 hour'
           ORDER BY chain, token_address, flow_label, date, bucket_end""",
        (units[0].chain, units[0].token_address, units[0].flow_label, start, end),
    ).fetchall()
    desired = {(bucket_start, bucket_start + timedelta(hours=1))
               for unit in units
               for bucket_start in (unit.coverage_start + timedelta(hours=i) for i in range(unit.desired_bucket_count))}
    observed = {(row[3], row[4]) for row in keys if (row[3], row[4]) in desired}
    daily = connection.execute(
        """SELECT chain, token_address, flow_label, date, bucket_end
           FROM nansen.flows WHERE chain=%s AND token_address=%s AND flow_label=%s
             AND date BETWEEN %s AND %s AND bucket_end - date = interval '24 hours'
           ORDER BY chain, token_address, flow_label, date, bucket_end""",
        (units[0].chain, units[0].token_address, units[0].flow_label, start, end),
    ).fetchall()
    daily_digest = hashlib.sha256(json.dumps(
        [[str(value) for value in row] for row in daily], separators=(",", ":")
    ).encode()).hexdigest()
    return {
        "rows": counts[0], "natural_unique": counts[1], "hourly": counts[2],
        "daily": counts[3], "hourly_identities": observed,
        "desired_identities": desired, "daily_digest": daily_digest,
    }


def _audit_count(connection) -> int:
    return connection.execute("SELECT count(*) FROM nansen.ingestion_runs").fetchone()[0]


def _global_rows(connection) -> tuple[int, int]:
    return connection.execute(
        """SELECT count(*), count(*) - count(DISTINCT (chain, token_address, flow_label, date, bucket_end))
           FROM nansen.flows"""
    ).fetchone()


def _resource_snapshot(label: str) -> tuple[float, int, int, int]:
    """Return CPU%, available RAM, commit limit, and free commit bytes."""
    import ctypes
    import psutil

    class _MemoryStatus(ctypes.Structure):
        _fields_ = [
            ("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
            ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
            ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]

    status = _MemoryStatus()
    status.dwLength = ctypes.sizeof(status)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        raise RuntimeError("Windows memory status unavailable")
    cpu = psutil.cpu_percent(interval=0.1)
    free_commit = int(status.ullAvailPageFile)
    commit_limit = int(status.ullTotalPageFile)
    available_ram = int(status.ullAvailPhys)
    print(f"RESOURCE_{label}_CPU_PERCENT={cpu:.1f}")
    print(f"RESOURCE_{label}_AVAILABLE_RAM_BYTES={available_ram}")
    print(f"RESOURCE_{label}_WINDOWS_COMMIT_USED_BYTES={commit_limit-free_commit}")
    print(f"RESOURCE_{label}_COMMIT_LIMIT_BYTES={commit_limit}")
    print(f"RESOURCE_{label}_FREE_COMMIT_BYTES={free_commit}")
    return cpu, available_ram, commit_limit, free_commit


def _resource_pressure(snapshot: tuple[float, int, int, int]) -> bool:
    _, available_ram, commit_limit, free_commit = snapshot
    return available_ram < 0.10 * (commit_limit if commit_limit else 1) or free_commit < 0.05 * (commit_limit if commit_limit else 1)


def _checkpoint(connection):
    row = connection.execute(
        """SELECT last_complete_timestamp, last_success_run_id::text
           FROM nansen.checkpoints WHERE chain='avalanche' AND endpoint='flows'
             AND flow_label='smart_money'"""
    ).fetchone()
    return row


def _validate_unit_readonly(unit, run_id: str) -> dict[str, Any]:
    connection = _readonly_connection()
    try:
        audit = connection.execute(
            """SELECT status, chain, endpoint, token_address, flow_label, window_start,
                      window_end, pages_requested, api_calls, records_received,
                      records_normalized, source_warnings
               FROM nansen.ingestion_runs WHERE run_id=%s""",
            (run_id,),
        ).fetchone()
        if audit is None:
            raise RuntimeError("successful run audit is missing")
        (status, chain, endpoint, token, label, win_start, win_end, pages, calls,
         received, normalized, warnings) = audit
        approved = isinstance(warnings, list) and all(
            isinstance(item, dict)
            and set(item) == {"page", "warning_count", "categories"}
            and isinstance(item["page"], int) and not isinstance(item["page"], bool) and item["page"] >= 1
            and isinstance(item["warning_count"], int) and not isinstance(item["warning_count"], bool) and item["warning_count"] >= 1
            and isinstance(item["categories"], list) and bool(item["categories"])
            and set(item["categories"]) <= {NON_EXCHANGE_BREAKDOWN_UNAVAILABLE}
            for item in warnings
        )
        valid = (status == "success" and chain == unit.chain and endpoint == "flows"
                 and token.lower() == unit.token_address.lower() and label == unit.flow_label
                 and win_start == unit.request_start and win_end == unit.request_end
                 and pages == 1 and calls == 1 and warnings is not None and approved)
        if not valid:
            raise RuntimeError("successful unit audit did not meet the exact-window contract")
        start_row = connection.execute(
            """SELECT EXISTS(SELECT 1 FROM nansen.flows WHERE chain=%s AND token_address=%s
                 AND flow_label=%s AND date=%s AND bucket_end-date=interval '1 hour')""",
            (unit.chain, unit.token_address, unit.flow_label, unit.request_start),
        ).fetchone()[0]
        hourly = connection.execute(
            """SELECT date, bucket_end FROM nansen.flows WHERE chain=%s AND token_address=%s
                 AND flow_label=%s AND date BETWEEN %s AND %s
                 AND bucket_end-date=interval '1 hour'
                 ORDER BY date, bucket_end""",
            (unit.chain, unit.token_address, unit.flow_label, unit.coverage_start, unit.coverage_end),
        ).fetchall()
        non_hourly = connection.execute(
            """SELECT count(*) FROM nansen.flows WHERE chain=%s AND token_address=%s
                 AND flow_label=%s AND date BETWEEN %s AND %s
                 AND bucket_end-date<>interval '1 hour'""",
            (unit.chain, unit.token_address, unit.flow_label, unit.coverage_start, unit.coverage_end),
        ).fetchone()[0]
        expected = {(bucket_start, bucket_start + timedelta(hours=1))
                    for bucket_start in (unit.coverage_start + timedelta(hours=i)
                                         for i in range(unit.desired_bucket_count))}
        seen = set(hourly)
        missing = expected - seen
        return {
            "audit_valid": True, "pages": pages, "calls": calls,
            "records_received": received, "records_normalized": normalized,
            "warning_count": sum(int(x["warning_count"]) for x in warnings),
            "warning_categories": sorted({c for x in warnings for c in x["categories"]}),
            "desired": len(expected), "observed": len(expected & seen), "missing": len(missing),
            "request_start_bucket": bool(start_row), "duplicate_hourly": len(hourly)-len(seen),
            "unexpected_hourly": len(seen - expected), "non_hourly": non_hourly,
        }
    finally:
        connection.close()


def _parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Staging-only Nansen hourly backfill runner")
    parser.add_argument("--execute", action="store_true", help="explicit live execution opt-in")
    parser.add_argument("--max-units", type=int)
    parser.add_argument("--max-live-calls", type=int)
    parser.add_argument("--expected-complete-before", type=int)
    parser.add_argument("--expected-first-pending-index", type=int)
    parser.add_argument("--expected-flow-rows-before", type=int)
    parser.add_argument("--expected-hourly-rows-before", type=int)
    parser.add_argument("--expected-daily-rows-before", type=int)
    parser.add_argument("--expected-ingestion-runs-before", type=int)
    parser.add_argument("--expected-recent-hourly-rows-before", type=int)
    parser.add_argument("--expected-checkpoint-timestamp")
    parser.add_argument("--expected-checkpoint-run-id")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = _parse_args(argv)
    explicit_env_opt_in = os.environ.get("NANSEN_RUN_LIVE_BACKFILL") == "1"
    both_opt_ins = execution_enabled(args.execute, {"NANSEN_RUN_LIVE_BACKFILL": "1" if explicit_env_opt_in else "0"})
    plan = build_canonical_plan()
    print(f"TARGET_START={_wire(plan.target_start)}")
    print(f"TARGET_END={_wire(plan.target_end)}")
    print(f"PLAN_UNITS={len(plan.units)}")
    print("NANSEN_CALLS_BEFORE_EXECUTION=0")
    print("DATABASE_WRITES_BEFORE_EXECUTION=0")
    if args.max_units is not None or args.max_live_calls is not None:
        if args.max_units is None or args.max_live_calls is None:
            print("EXECUTION_REFUSED=BOTH_BATCH_LIMITS_REQUIRED")
            return 2
        try:
            validate_invocation_limits(args.max_units, args.max_live_calls)
        except BackfillExecutionError:
            print("EXECUTION_REFUSED=INVOCATION_LIMIT")
            return 2
    _load_dotenv_if_present()
    connection = _readonly_connection()
    try:
        progress = inspect_plan_progress(connection, plan)
        pending = [unit for unit in plan.units if progress.statuses[unit.unit_id] == "PENDING"]
        selected = tuple(pending[:args.max_units]) if args.max_units else ()
        before_counts = _target_counts(connection, selected) if selected else None
        canonical_counts = _target_counts(connection, plan.units)
        before_rows, before_duplicates = _global_rows(connection)
        audit_count_before = _audit_count(connection)
        checkpoint_before = _checkpoint(connection)
        recent = connection.execute(
            """SELECT count(*), count(DISTINCT (chain,token_address,flow_label,date,bucket_end))
               FROM nansen.flows WHERE chain=%s AND token_address=%s AND flow_label=%s
                 AND date >= %s AND date < %s AND bucket_end-date=interval '1 hour'""",
            (plan.chain, plan.token_address, plan.flow_label,
             datetime(2026, 9, 20, tzinfo=timezone.utc), datetime(2026, 9, 21, tzinfo=timezone.utc)),
        ).fetchone()
    finally:
        connection.close()
    print(f"PLAN_COMPLETE_BEFORE={progress.complete}")
    print(f"PLAN_PENDING_BEFORE={progress.pending}")
    print(f"PLAN_AMBIGUOUS_BEFORE={progress.ambiguous}")
    print(f"TOTAL_FLOW_ROWS_BEFORE={before_rows}")
    print(f"CANONICAL_TARGET_HOURLY_ROWS_BEFORE={canonical_counts['hourly']}")
    print(f"CANONICAL_TARGET_DAILY_ROWS_BEFORE={canonical_counts['daily']}")
    print(f"INGESTION_RUN_ROWS_BEFORE={audit_count_before}")
    print(f"RECENT_HOURLY_ROWS_BEFORE={recent[0]}")
    print(f"RECENT_HOURLY_IDENTITIES_BEFORE={recent[1]}")
    print(f"CHECKPOINT_BEFORE={json.dumps((_wire(checkpoint_before[0]), checkpoint_before[1]) if checkpoint_before else None)}")
    if before_duplicates:
        print("EXECUTION_REFUSED=GLOBAL_NATURAL_IDENTITY_DUPLICATES")
        return 2
    for unit in selected:
        print(f"SELECTED_UNIT={unit.index},{unit.unit_id},{_wire(unit.coverage_start)},{_wire(unit.coverage_end)},{_wire(unit.request_start)},{_wire(unit.request_end)}")
    if before_counts is not None:
        print(f"BATCH_DESIRED_BUCKETS={len(before_counts['desired_identities'])}")
        print(f"BATCH_DESIRED_IDENTITIES_PRESENT_BEFORE={len(before_counts['hourly_identities'] & before_counts['desired_identities'])}")
        print(f"DAILY_IDENTITY_DIGEST_BEFORE={before_counts['daily_digest']}")
    if not both_opt_ins:
        print("EXECUTION_REFUSED=REQUIRES_BOTH_CLI_FLAG_AND_ENV_OPT_IN")
        return 0

    required_options = (
        args.max_units, args.max_live_calls, args.expected_complete_before,
        args.expected_first_pending_index, args.expected_flow_rows_before,
        args.expected_hourly_rows_before, args.expected_daily_rows_before,
        args.expected_ingestion_runs_before, args.expected_recent_hourly_rows_before,
        args.expected_checkpoint_timestamp, args.expected_checkpoint_run_id,
    )
    if any(value is None for value in required_options):
        print("EXECUTION_REFUSED=LIVE_AUTHORIZATION_ARGUMENTS_REQUIRED")
        return 2
    try:
        selected = select_authorized_units(
            plan, progress, max_units=args.max_units, max_live_calls=args.max_live_calls,
            expected_complete_before=args.expected_complete_before,
            expected_first_pending_index=args.expected_first_pending_index,
        )
    except BackfillExecutionError:
        print("EXECUTION_REFUSED=PLAN_PROGRESS_OR_SELECTION_MISMATCH")
        return 2
    if tuple(unit.index for unit in selected) == tuple(range(4, 14)):
        try:
            validate_task028_bounds(selected)
        except BackfillExecutionError:
            print("EXECUTION_REFUSED=TASK028_BOUND_MISMATCH")
            return 2
    if (before_rows != args.expected_flow_rows_before
            or canonical_counts["hourly"] != args.expected_hourly_rows_before
            or canonical_counts["daily"] != args.expected_daily_rows_before
            or audit_count_before != args.expected_ingestion_runs_before
            or recent[0] != args.expected_recent_hourly_rows_before
            or recent[1] != args.expected_recent_hourly_rows_before
            or checkpoint_before is None
            or _wire(checkpoint_before[0]) != args.expected_checkpoint_timestamp
            or checkpoint_before[1] != args.expected_checkpoint_run_id):
        print("EXECUTION_REFUSED=STAGING_SNAPSHOT_MISMATCH")
        return 2

    resource_before = _resource_snapshot("BEFORE")
    if _resource_pressure(resource_before):
        print("EXECUTION_REFUSED=HOST_RESOURCE_PRESSURE")
        return 2

    repository = PostgresRepository.from_env()
    try:
        _assert_writable_staging(repository)
        progress_connection = _readonly_connection()
        try:
            progress_again = inspect_plan_progress(progress_connection, plan)
        finally:
            progress_connection.close()
        if (progress_again.complete, progress_again.pending, progress_again.ambiguous) != (progress.complete, progress.pending, progress.ambiguous):
            raise BackfillExecutionError("plan progress changed before execution")
        pending_again = [unit for unit in plan.units if progress_again.statuses[unit.unit_id] == "PENDING"][:args.max_units]
        if [unit.unit_id for unit in pending_again] != [unit.unit_id for unit in selected]:
            raise BackfillExecutionError("pending unit selection changed before execution")
        # The exact first-three authorization is deliberately frozen before any Nansen call.
        config = NansenConfig.from_env()
        completed_details: dict[str, dict[str, Any]] = {}
        calls_total = 0
        successful_units = 0
        selected_positions = {unit.unit_id: position for position, unit in enumerate(selected, start=1)}

        def run_one(unit, assigned_calls):
            nonlocal calls_total, successful_units
            if unit.unit_id not in selected_positions or assigned_calls != MAX_CALLS_PER_UNIT:
                raise BackfillExecutionError("executor attempted an unauthorized unit or call ceiling")
            client_config = replace(config, max_calls=1, max_retries=0, page_size=1000, max_pages=1, timeout_seconds=120)
            client = NansenClient(client_config)
            orchestrator = NansenIngestionOrchestrator(client, repository)
            try:
                result = orchestrator.ingest_flows(
                    chain=unit.chain,
                    token_address=unit.token_address,
                    flow_label=unit.flow_label,
                    window=IngestionWindow(unit.request_start, unit.request_end),
                )
            finally:
                client.session.close()
            if client.requests_attempted != 1 or result.api_calls != 1:
                raise BackfillExecutionError("unit did not consume exactly one API attempt")
            calls_total += 1
            detail = _validate_unit_readonly(unit, result.run_id)
            completed_details[unit.unit_id] = {"run_id": result.run_id, **detail}
            print(f"UNIT_{unit.index}_RESULT=SUCCESS")
            print(f"UNIT_{unit.index}_RUN_ID={result.run_id}")
            print(f"UNIT_{unit.index}_API_CALLS={detail['calls']}")
            print(f"UNIT_{unit.index}_RECORDS_RECEIVED={detail['records_received']}")
            print(f"UNIT_{unit.index}_RECORDS_NORMALIZED={detail['records_normalized']}")
            print(f"UNIT_{unit.index}_WARNING_COUNT={detail['warning_count']}")
            print(f"UNIT_{unit.index}_WARNING_CATEGORIES={','.join(detail['warning_categories']) or 'NONE'}")
            print(f"UNIT_{unit.index}_DESIRED_BUCKETS={detail['desired']}")
            print(f"UNIT_{unit.index}_OBSERVED_DESIRED_BUCKETS={detail['observed']}")
            print(f"UNIT_{unit.index}_MISSING_DESIRED_BUCKETS={detail['missing']}")
            print(f"UNIT_{unit.index}_NON_HOURLY_ROWS={detail['non_hourly']}")
            print(f"UNIT_{unit.index}_DUPLICATE_HOURLY_IDENTITIES={detail['duplicate_hourly']}")
            print(f"UNIT_{unit.index}_REQUEST_START_BUCKET_PRESENT={'YES' if detail['request_start_bucket'] else 'NO'}")
            print(f"UNIT_{unit.index}_AUDIT_VALID={detail['audit_valid']}")
            if detail["missing"] or detail["duplicate_hourly"] or detail["unexpected_hourly"]:
                raise SourceCoverageGap("unit desired hourly coverage is incomplete or duplicated")
            successful_units += 1
            current = _progress(plan)
            expected_progress = expected_progress_after(progress, successful_units)
            if (current.complete, current.pending, current.ambiguous) != expected_progress:
                raise BackfillExecutionError("exact-window audit progress did not advance as expected")
            print(f"PLAN_COMPLETE_AFTER_UNIT_{unit.index}={current.complete}")
            print(f"PLAN_PENDING_AFTER_UNIT_{unit.index}={current.pending}")
            print(f"PLAN_AMBIGUOUS_AFTER_UNIT_{unit.index}={current.ambiguous}")
            resource_now = _resource_snapshot(f"AFTER_UNIT_{unit.index}")
            if should_stop_for_resource_pressure(resource_now, successful_units=successful_units,
                                                 selected_units=len(selected)):
                raise BackfillExecutionError("host resource pressure blocks the next unit")
            return client.requests_attempted

        result = execute_pending_units(
            plan, progress.statuses, max_units=args.max_units, max_live_calls=args.max_live_calls,
            max_calls_per_unit=MAX_CALLS_PER_UNIT, execute_unit=run_one,
        )
        if result.live_calls_used != args.max_units or calls_total != args.max_units:
            raise BackfillExecutionError("whole-batch call accounting differs from the authorized unit count")
        print(f"SUCCESSFUL_UNITS_EXECUTED={successful_units}")
        print(f"LIVE_API_CALLS_BATCH={calls_total}")
        repository.close()
        repository = None

        fresh = _readonly_connection()
        try:
            final_plan = build_canonical_plan()
            final_progress = inspect_plan_progress(fresh, final_plan)
            after_counts = _target_counts(fresh, selected)
            final_canonical_counts = _target_counts(fresh, final_plan.units)
            after_rows, after_duplicates = _global_rows(fresh)
            audit_count_after = _audit_count(fresh)
            checkpoint_after = _checkpoint(fresh)
            present_before = before_counts["hourly_identities"] & before_counts["desired_identities"]
            present_after = after_counts["hourly_identities"] & after_counts["desired_identities"]
            missing_after = after_counts["desired_identities"] - after_counts["hourly_identities"]
            new_desired = present_after - present_before
            reused_desired = present_after & present_before
            daily_digest_unchanged = after_counts["daily_digest"] == before_counts["daily_digest"]
            print(f"BATCH_DESIRED_BUCKETS={len(after_counts['desired_identities'])}")
            print(f"BATCH_DESIRED_IDENTITIES_PRESENT_BEFORE={len(present_before)}")
            print(f"BATCH_DESIRED_IDENTITIES_PRESENT_AFTER={len(present_after)}")
            print(f"BATCH_MISSING_DESIRED_IDENTITIES={len(missing_after)}")
            print(f"NEW_DESIRED_IDENTITIES_ADDED={len(new_desired)}")
            print(f"EXISTING_DESIRED_IDENTITIES_REUSED={len(reused_desired)}")
            print(f"DAILY_IDENTITY_DIGEST_BEFORE={before_counts['daily_digest']}")
            print(f"DAILY_IDENTITY_DIGEST_AFTER={after_counts['daily_digest']}")
            print(f"DAILY_IDENTITY_DIGEST_UNCHANGED={daily_digest_unchanged}")
            print(f"TOTAL_FLOW_ROWS_BEFORE={before_rows}")
            print(f"TOTAL_FLOW_ROWS_AFTER={after_rows}")
            print(f"CANONICAL_TARGET_HOURLY_ROWS_AFTER={final_canonical_counts['hourly']}")
            print(f"CANONICAL_TARGET_DAILY_ROWS_AFTER={final_canonical_counts['daily']}")
            print(f"GLOBAL_FLOW_ROW_ACCOUNTING={after_rows == before_rows + len(new_desired)}")
            print(f"GLOBAL_NATURAL_IDENTITY_DUPLICATES={after_duplicates}")
            print(f"INGESTION_RUN_ROWS_BEFORE={audit_count_before}")
            print(f"INGESTION_RUN_ROWS_AFTER={audit_count_after}")
            print(f"PLAN_COMPLETE_AFTER={final_progress.complete}")
            print(f"PLAN_PENDING_AFTER={final_progress.pending}")
            print(f"PLAN_AMBIGUOUS_AFTER={final_progress.ambiguous}")
            next_index = first_pending_index(final_plan, final_progress.statuses)
            print(f"RESTART_RESUME_NEXT_UNIT={next_index if next_index is not None else 'NONE'}")
            print(f"CHECKPOINT_AFTER={json.dumps((_wire(checkpoint_after[0]), checkpoint_after[1]) if checkpoint_after else None)}")
            print(f"CHECKPOINT_NON_REGRESSION={checkpoint_after == checkpoint_before}")
            print(f"NEW_RUNS_WITH_WARNING_AUDIT={sum(1 for d in completed_details.values() if d['audit_valid'])}")
            print("NEW_RUNS_WITH_NULL_WARNING_AUDIT=0")
            print("NEW_RUNS_WITH_UNKNOWN_CATEGORY=0")
            expected_final_progress = expected_progress_after(progress, successful_units)
            expected_next_index = selected[-1].index + 1
            if (final_progress.complete, final_progress.pending, final_progress.ambiguous) != expected_final_progress:
                raise BackfillExecutionError("final audit progress differs from dynamic batch expectation")
            if len(present_after) != len(after_counts["desired_identities"]) or missing_after:
                raise BackfillExecutionError("combined desired hourly coverage is not complete")
            if not daily_digest_unchanged or after_duplicates:
                raise BackfillExecutionError("global identity or daily preservation check failed")
            if after_rows != before_rows + len(new_desired):
                raise BackfillExecutionError("global flow row accounting did not match new identities")
            if audit_count_after != audit_count_before + successful_units:
                raise BackfillExecutionError("audit run count did not increase by successful unit count")
            if checkpoint_after != checkpoint_before:
                raise BackfillExecutionError("historical batch changed the high-water checkpoint")
            if next_index != expected_next_index:
                raise BackfillExecutionError("restart resume did not select the next contiguous unit")
            recent_after = fresh.execute(
                """SELECT count(*), count(DISTINCT (chain,token_address,flow_label,date,bucket_end))
                   FROM nansen.flows WHERE chain=%s AND token_address=%s AND flow_label=%s
                     AND date >= %s AND date < %s AND bucket_end-date=interval '1 hour'""",
                (final_plan.chain, final_plan.token_address, final_plan.flow_label,
                 datetime(2026, 9, 20, tzinfo=timezone.utc), datetime(2026, 9, 21, tzinfo=timezone.utc)),
            ).fetchone()
            if recent_after != recent:
                raise BackfillExecutionError("recent September retained state changed")
            print(f"RECENT_RETAINED_HOURLY_ROWS_AFTER={recent_after[0]}")
            print(f"RECENT_RETAINED_HOURLY_IDENTITIES_AFTER={recent_after[1]}")
            print("RECENT_RETAINED_STATE_UNCHANGED=PASS")
            print("RESTART_RESUME_PROOF=PASS")
            print("TASK_028_STATUS=SUCCESS")
            _resource_snapshot("AFTER_BATCH")
        finally:
            fresh.close()
        return 0
    finally:
        if repository is not None:
            repository.close()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BaseException as exc:
        if isinstance(exc, SystemExit):
            raise
        # Do not print source response bodies or warning text.
        status = "SOURCE_COVERAGE_GAP" if isinstance(exc, SourceCoverageGap) else "LIVE_BATCH_FAILURE"
        print(f"TASK_028_STATUS={status}")
        print(f"FAILURE_TYPE={type(exc).__name__}")
        raise SystemExit(1)
