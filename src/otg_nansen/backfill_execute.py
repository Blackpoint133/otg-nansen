"""Double-gated, staging-only runner for the first canonical flow units.

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
import sys
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


def execution_enabled(cli_opt_in: bool, environ: dict[str, str] | None = None) -> bool:
    env = os.environ if environ is None else environ
    return cli_opt_in and env.get("NANSEN_RUN_LIVE_BACKFILL") == "1"


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
    desired = {(start := unit.coverage_start + timedelta(hours=i), start + timedelta(hours=1))
               for unit in units for i in range(unit.desired_bucket_count)}
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
        expected = {(start := unit.coverage_start + timedelta(hours=i), start + timedelta(hours=1))
                    for i in range(unit.desired_bucket_count)}
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
    parser.add_argument("--max-units", type=int, default=3)
    parser.add_argument("--max-live-calls", type=int, default=3)
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = _parse_args(argv)
    plan = build_canonical_plan()
    print(f"TARGET_START={_wire(plan.target_start)}")
    print(f"TARGET_END={_wire(plan.target_end)}")
    print(f"PLAN_UNITS={len(plan.units)}")
    print("NANSEN_CALLS_BEFORE_EXECUTION=0")
    print("DATABASE_WRITES_BEFORE_EXECUTION=0")
    _load_dotenv_if_present()
    connection = _readonly_connection()
    try:
        progress = inspect_plan_progress(connection, plan)
        pending = [unit for unit in plan.units if progress.statuses[unit.unit_id] == "PENDING"]
        selected = pending[:3]
        before_counts = _target_counts(connection, selected) if selected else None
        canonical_counts = _target_counts(connection, plan.units)
        before_rows, before_duplicates = _global_rows(connection)
        audit_count_before = _audit_count(connection)
        checkpoint_before = _checkpoint(connection)
    finally:
        connection.close()
    print(f"PLAN_COMPLETE_BEFORE={progress.complete}")
    print(f"PLAN_PENDING_BEFORE={progress.pending}")
    print(f"PLAN_AMBIGUOUS_BEFORE={progress.ambiguous}")
    print(f"TOTAL_FLOW_ROWS_BEFORE={before_rows}")
    print(f"CANONICAL_TARGET_HOURLY_ROWS_BEFORE={canonical_counts['hourly']}")
    print(f"CANONICAL_TARGET_DAILY_ROWS_BEFORE={canonical_counts['daily']}")
    print(f"INGESTION_RUN_ROWS_BEFORE={audit_count_before}")
    print(f"CHECKPOINT_BEFORE={json.dumps(checkpoint_before, default=str)}")
    if (before_rows, canonical_counts["hourly"], canonical_counts["daily"], audit_count_before,
            checkpoint_before, before_duplicates) != (
            219, 190, 29, 5,
            (datetime(2026, 9, 20, 23, 59, 59, tzinfo=timezone.utc),
             "1d535cae-c74b-49ef-bd5e-0c46f2301a3d"), 0):
        print("EXECUTION_REFUSED=STAGING_STATE_MISMATCH")
        return 2
    if progress.ambiguous:
        print("EXECUTION_REFUSED=AMBIGUOUS_PROGRESS")
        return 2
    if len(selected) != 3:
        print("EXECUTION_REFUSED=FEWER_THAN_THREE_PENDING_UNITS")
        return 2
    expected = ((1, "2025-04-25T00:00:00Z", "2025-05-01T22:00:00Z", "2025-04-24T23:00:00Z", "2025-05-01T22:59:59Z"),
                (2, "2025-05-01T23:00:00Z", "2025-05-08T21:00:00Z", "2025-05-01T22:00:00Z", "2025-05-08T21:59:59Z"),
                (3, "2025-05-08T22:00:00Z", "2025-05-15T20:00:00Z", "2025-05-08T21:00:00Z", "2025-05-15T20:59:59Z"))
    actual = tuple((u.index, _wire(u.coverage_start), _wire(u.coverage_end), _wire(u.request_start), _wire(u.request_end)) for u in selected)
    if actual != expected:
        print("EXECUTION_REFUSED=PENDING_SELECTION_DRIFT")
        return 2
    for unit in selected:
        print(f"SELECTED_UNIT={unit.index},{unit.unit_id},{_wire(unit.request_start)},{_wire(unit.request_end)}")
    if not execution_enabled(args.execute):
        print("EXECUTION_REFUSED=REQUIRES_BOTH_CLI_FLAG_AND_ENV_OPT_IN")
        return 0
    if args.max_units != 3 or args.max_live_calls != 3:
        print("EXECUTION_REFUSED=AUTHORIZED_BUDGET_MUST_BE_3_AND_3")
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
        pending_again = [unit for unit in plan.units if progress_again.statuses[unit.unit_id] == "PENDING"][:3]
        if [unit.unit_id for unit in pending_again] != [unit.unit_id for unit in selected]:
            raise BackfillExecutionError("pending unit selection changed before execution")
        # The exact first-three authorization is deliberately frozen before any Nansen call.
        config = NansenConfig.from_env()
        completed_details: dict[str, dict[str, Any]] = {}
        calls_total = 0

        def run_one(unit, assigned_calls):
            nonlocal calls_total
            client_config = replace(config, max_calls=1, max_retries=0, page_size=1000, max_pages=1, timeout_seconds=120)
            client = NansenClient(client_config)
            orchestrator = NansenIngestionOrchestrator(client, repository)
            result = orchestrator.ingest_flows(
                chain=unit.chain,
                token_address=unit.token_address,
                flow_label=unit.flow_label,
                window=IngestionWindow(unit.request_start, unit.request_end),
            )
            if client.requests_attempted != 1 or result.api_calls != 1:
                raise BackfillExecutionError("unit did not consume exactly one API attempt")
            calls_total += 1
            detail = _validate_unit_readonly(unit, result.run_id)
            completed_details[unit.unit_id] = {"run_id": result.run_id, **detail}
            print(f"UNIT_RESULT={unit.index},success,{result.run_id},{detail['calls']},{detail['records_received']},{detail['records_normalized']},{detail['warning_count']},{','.join(detail['warning_categories']) or 'NONE'},{detail['desired']},{detail['observed']},{detail['missing']},{detail['non_hourly']},{detail['duplicate_hourly']},{int(detail['request_start_bucket'])},{detail['audit_valid']}")
            if detail["missing"] or detail["duplicate_hourly"] or detail["unexpected_hourly"]:
                raise SourceCoverageGap("unit desired hourly coverage is incomplete or duplicated")
            current = _progress(plan)
            expected_complete = len(completed_details)
            if (current.complete, current.pending, current.ambiguous) != (expected_complete, 74-expected_complete, 0):
                raise BackfillExecutionError("exact-window audit progress did not advance as expected")
            print(f"PROGRESS_AFTER_UNIT={unit.index},{current.complete},{current.pending},{current.ambiguous}")
            resource_now = _resource_snapshot(f"AFTER_UNIT_{unit.index}")
            if unit.index < 3 and _resource_pressure(resource_now):
                raise BackfillExecutionError("host resource pressure blocks the next unit")
            return client.requests_attempted

        result = execute_pending_units(
            plan, progress.statuses, max_units=3, max_live_calls=3,
            max_calls_per_unit=1, execute_unit=run_one,
        )
        if result.live_calls_used != 3 or calls_total != 3:
            raise BackfillExecutionError("whole-batch call accounting did not equal three")
        print(f"LIVE_API_CALLS_TASK027={calls_total}")
        print("DATABASE_WRITES_TASK027=3")
        repository.close()
        repository = None

        fresh = _readonly_connection()
        try:
            final_progress = inspect_plan_progress(fresh, build_canonical_plan())
            after_counts = _target_counts(fresh, selected)
            after_rows, after_duplicates = _global_rows(fresh)
            audit_count_after = _audit_count(fresh)
            checkpoint_after = _checkpoint(fresh)
            print(f"BATCH_DESIRED_UNIQUE_HOURLY_BEFORE={len(before_counts['hourly_identities'] & before_counts['desired_identities'])}")
            print(f"BATCH_DESIRED_UNIQUE_HOURLY_AFTER={len(after_counts['hourly_identities'] & after_counts['desired_identities'])}")
            print(f"NEW_DESIRED_IDENTITIES_ADDED={len(after_counts['hourly_identities']-before_counts['hourly_identities'])}")
            print(f"EXISTING_DESIRED_IDENTITIES_REUSED={len(before_counts['hourly_identities'] & before_counts['desired_identities'])}")
            print(f"DAILY_IDENTITY_DIGEST_UNCHANGED={after_counts['daily_digest']==before_counts['daily_digest']}")
            print(f"TOTAL_FLOW_ROWS_BEFORE={before_rows}")
            print(f"TOTAL_FLOW_ROWS_AFTER={after_rows}")
            print(f"GLOBAL_NATURAL_IDENTITY_DUPLICATES={after_duplicates}")
            print(f"INGESTION_RUN_ROWS_BEFORE={audit_count_before}")
            print(f"INGESTION_RUN_ROWS_AFTER={audit_count_after}")
            print(f"PLAN_COMPLETE_AFTER={final_progress.complete}")
            print(f"PLAN_PENDING_AFTER={final_progress.pending}")
            print(f"PLAN_AMBIGUOUS_AFTER={final_progress.ambiguous}")
            next_pending = [u for u in build_canonical_plan().units if final_progress.statuses[u.unit_id] == "PENDING"]
            print(f"RESTART_RESUME_NEXT_UNIT={next_pending[0].index if next_pending else 'NONE'}")
            print(f"CHECKPOINT_NON_REGRESSION={checkpoint_after == checkpoint_before}")
            print(f"NEW_RUNS_WITH_WARNING_AUDIT={sum(1 for d in completed_details.values() if d['audit_valid'])}")
            print("NEW_RUNS_WITH_NULL_WARNING_AUDIT=0")
            print("NEW_RUNS_WITH_UNKNOWN_CATEGORY=0")
            if (final_progress.complete, final_progress.pending, final_progress.ambiguous) != (3, 71, 0):
                raise BackfillExecutionError("final audit progress differs from authorized batch")
            if len(after_counts["hourly_identities"] & after_counts["desired_identities"]) != 501:
                raise BackfillExecutionError("combined desired hourly coverage is not complete")
            if after_counts["daily_digest"] != before_counts["daily_digest"] or after_duplicates:
                raise BackfillExecutionError("global identity or daily preservation check failed")
            if audit_count_after != audit_count_before + 3:
                raise BackfillExecutionError("audit run count did not increase by three")
            if checkpoint_after != checkpoint_before:
                raise BackfillExecutionError("historical batch changed the high-water checkpoint")
            if next_pending[0].index != 4:
                raise BackfillExecutionError("restart resume did not select unit four")
            print("RESTART_RESUME_PROOF=PASS")
            print("TASK_027_STATUS=SUCCESS")
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
        print(f"TASK_027_STATUS={status}")
        print(f"FAILURE_TYPE={type(exc).__name__}")
        raise SystemExit(1)
