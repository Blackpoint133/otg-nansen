"""Dry-run summary for the canonical Avalanche hourly flow backfill plan."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone

from .backfill import inspect_plan_progress, plan_hourly_flow_backfill
from .config import TOKEN_IDENTITIES

TARGET_START = datetime(2025, 4, 25, 0, tzinfo=timezone.utc)
TARGET_END = datetime(2026, 9, 20, 23, tzinfo=timezone.utc)


def _wire(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def build_canonical_plan():
    return plan_hourly_flow_backfill(
        TARGET_START,
        TARGET_END,
        chain="avalanche",
        token_address=TOKEN_IDENTITIES["avalanche"],
        flow_label="smart_money",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Print a dry-run summary for the hourly Nansen backfill plan.")
    parser.add_argument("--staging-progress", action="store_true", help="also inspect exact-window audits through a read-only staging connection")
    args = parser.parse_args(argv)
    plan = build_canonical_plan()
    first, second, final = plan.units[0], plan.units[1], plan.units[-1]
    durations = [unit.request_duration for unit in plan.units]
    print(f"TARGET_START={_wire(plan.target_start)}")
    print(f"TARGET_END={_wire(plan.target_end)}")
    print(f"DESIRED_BUCKET_COUNT={plan.desired_bucket_count}")
    print(f"MAX_DESIRED_BUCKETS_PER_REQUEST={plan.max_desired_buckets_per_request}")
    print(f"TOTAL_PLAN_UNITS={len(plan.units)}")
    print(f"MAX_LIVE_CALLS={plan.max_live_calls}")
    print(f"FIRST_UNIT_ID={first.unit_id}")
    print(f"FIRST_UNIT_COVERAGE={_wire(first.coverage_start)}/{_wire(first.coverage_end)}")
    print(f"FIRST_UNIT_REQUEST={_wire(first.request_start)}/{_wire(first.request_end)}")
    print(f"SECOND_UNIT_ID={second.unit_id}")
    print(f"SECOND_UNIT_COVERAGE={_wire(second.coverage_start)}/{_wire(second.coverage_end)}")
    print(f"SECOND_UNIT_REQUEST={_wire(second.request_start)}/{_wire(second.request_end)}")
    print(f"FINAL_UNIT_ID={final.unit_id}")
    print(f"FINAL_UNIT_COVERAGE={_wire(final.coverage_start)}/{_wire(final.coverage_end)}")
    print(f"FINAL_UNIT_REQUEST={_wire(final.request_start)}/{_wire(final.request_end)}")
    print(f"MAX_REQUEST_DURATION={max(durations)}")
    print("LIVE_API_CALLS=0")
    print("DATABASE_WRITES=0")
    if args.staging_progress:
        import psycopg
        from .postgres import staging_connection_kwargs, verify_staging_target

        kwargs = staging_connection_kwargs()
        kwargs["options"] = "-c default_transaction_read_only=on"
        with psycopg.connect(**kwargs) as connection:
            identity = verify_staging_target(connection)
            if identity["database"] != "server_otg_staging" or identity["user"] != "gunz_user" or identity["transaction_read_only"] != "on":
                raise RuntimeError("read-only staging target verification failed")
            progress = inspect_plan_progress(connection, plan)
        print(f"PLAN_UNITS_COMPLETE={progress.complete}")
        print(f"PLAN_UNITS_PENDING={progress.pending}")
        print(f"PLAN_UNITS_AMBIGUOUS={progress.ambiguous}")
        print("DATABASE_READ_ONLY=YES")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
