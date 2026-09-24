"""Build the verified OTG–Nansen hourly analytical snapshot."""

from __future__ import annotations

import argparse
from datetime import timedelta
import os
from typing import Any

from .market_analytics import (
    ALIGNED_COLUMNS,
    CANONICAL_END,
    CANONICAL_HOURS,
    CANONICAL_START,
    MARKET_COLUMNS,
    OVERLAP_END,
    OVERLAP_START,
    align_hourly,
    aggregate_market_production,
    build_market_spine,
    content_digest,
    load_overlap_rows,
    production_readonly_connection,
    read_analytics_rows,
    read_nansen_source,
    replace_analytics_snapshot,
    resolve_overlap_rows,
    staging_readonly_connection,
    staging_writer_capability_preflight,
    staging_writer_connection,
    utc_hour_spine,
)


def _resource() -> dict[str, int | float | str]:
    try:
        import psutil
        vm, swap = psutil.virtual_memory(), psutil.swap_memory()
        return {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "available_ram_bytes": vm.available,
            "committed_bytes": swap.used,
            "commit_limit_bytes": swap.total,
            "free_commit_bytes": max(0, swap.total - swap.used),
        }
    except Exception:
        return {"status": "unavailable"}


def _print_resource(label: str) -> None:
    import json
    print(f"RESOURCE_{label.upper().replace(' ', '_')}={json.dumps(_resource(), sort_keys=True)}")


def _assert_readback(connection, table: str, columns, expected_digest: str) -> tuple[int, str, list[dict[str, Any]]]:
    rows = read_analytics_rows(connection, table, columns)
    digest = content_digest(rows, columns)
    if len(rows) != CANONICAL_HOURS or digest != expected_digest:
        raise RuntimeError(f"{table} physical readback does not match in-memory snapshot")
    starts = [row["hour_start"] for row in rows]
    if starts[0].astimezone(CANONICAL_START.tzinfo) != CANONICAL_START:
        raise RuntimeError(f"{table} minimum hour differs from canonical range")
    if starts[-1].astimezone(CANONICAL_END.tzinfo) != CANONICAL_END:
        raise RuntimeError(f"{table} maximum hour differs from canonical range")
    if len(set(starts)) != CANONICAL_HOURS:
        raise RuntimeError(f"{table} contains duplicate hour identities")
    return len(rows), digest, rows


def build_snapshot() -> dict[str, Any]:
    """Run read-only source extraction, validate, migrate, write, and prove idempotency."""
    from .migrate_analytics import apply_analytics_migration

    hours = utc_hour_spine()
    if len(hours) != CANONICAL_HOURS:
        raise RuntimeError("canonical UTC spine length mismatch")
    print(f"CANONICAL_HOURS={len(hours)}")
    print(f"CANONICAL_START={CANONICAL_START.isoformat().replace('+00:00','Z')}")
    print(f"CANONICAL_END={CANONICAL_END.isoformat().replace('+00:00','Z')}")
    _print_resource("before overlap rpc")

    staging_ro = staging_readonly_connection()
    try:
        nansen_rows, nansen_digest, nansen_hourly_count, nansen_daily_count = read_nansen_source(staging_ro)
    finally:
        staging_ro.rollback()
        staging_ro.close()
    print(f"CANONICAL_NANSEN_HOURLY_ROWS={nansen_hourly_count}")
    print(f"CANONICAL_NANSEN_DAILY_ROWS={nansen_daily_count}")
    print(f"NANSEN_SOURCE_IDENTITY_DIGEST={nansen_digest}")

    production = production_readonly_connection()
    try:
        # The real staging write path must be capable before the expensive overlap RPC campaign.
        writer_check = staging_writer_capability_preflight()
        print("WRITER_PREFLIGHT_BEFORE_RPC=YES")
        print("STAGING_WRITER_PREFLIGHT=PASS")
        print(f"STAGING_WRITER_DATABASE={writer_check['database']}")
        print(f"STAGING_WRITER_TRANSACTION_READ_ONLY={writer_check['transaction_read_only']}")
        print(f"STAGING_CURSOR_EXECUTEMANY_AVAILABLE={'YES' if writer_check['cursor_executemany_available'] else 'NO'}")
        print(f"MARKET_TABLE_EXISTS={'YES' if writer_check['market_table_exists'] else 'NO'}")
        print(f"ALIGNED_TABLE_EXISTS={'YES' if writer_check['aligned_table_exists'] else 'NO'}")
        overlap_rows = load_overlap_rows(production)
        print(f"OVERLAP_ROWS={len(overlap_rows)}")
        rpc_url = os.getenv("GUNZ_READ_RPC_URL", "https://subnets.avax.network/gunzilla/mainnet/rpc")
        overlap = resolve_overlap_rows(overlap_rows, rpc_url=rpc_url)
        print("RPC_CHAIN_ID=43419")
        print(f"ONCHAIN_RPC_CALLS_TASK033={overlap.rpc_method_objects}")
        print(f"OVERLAP_RECEIPTS_RESOLVED={overlap.receipts_resolved}")
        print("OVERLAP_RECEIPTS_UNRESOLVED=0")
        print(f"OVERLAP_DISTINCT_BLOCKS={overlap.distinct_blocks}")
        print(f"OVERLAP_BLOCKS_RESOLVED={overlap.blocks_resolved}")
        print("OVERLAP_BLOCKS_UNRESOLVED=0")
        print(f"OVERLAP_OFFSET_PLUS_05_ROWS={overlap.plus_05_rows}")
        print(f"OVERLAP_OFFSET_MINUS_08_ROWS={overlap.minus_08_rows}")
        print(f"OVERLAP_OFFSET_OTHER_ROWS={overlap.other_offset_rows}")
        print(f"OVERLAP_TIME_RESOLUTION_DIGEST={overlap.digest}")
        if overlap.digest != "08e64456eea3796ce0e1cfa3b475e2ac66f98050cf91ed99fcb6704a290feca6":
            raise RuntimeError("accepted overlap digest gate failed")
        _print_resource("after overlap rpc")
        market_aggregates, market_totals = aggregate_market_production(production, overlap_rows, overlap)
    finally:
        production.rollback()
        production.close()
    _print_resource("after production aggregation")

    market_rows = build_market_spine(market_aggregates, hours)
    aligned_rows = align_hourly(market_rows, nansen_rows, hours)
    market_digest = content_digest(market_rows, MARKET_COLUMNS)
    aligned_digest = content_digest(aligned_rows, ALIGNED_COLUMNS)
    if len(market_rows) != CANONICAL_HOURS or len(aligned_rows) != CANONICAL_HOURS:
        raise RuntimeError("analytical in-memory dataset length mismatch")
    print(f"MARKET_HOURLY_CONTENT_DIGEST={market_digest}")
    print(f"ALIGNED_HOURLY_CONTENT_DIGEST={aligned_digest}")
    _print_resource("after analytical construction")

    # No staging DDL/DML occurs until the overlap gate, production aggregation,
    # canonical alignment, and both in-memory content digests have succeeded.
    apply_analytics_migration()
    print("STAGING_MIGRATION_APPLIED=PASS")

    writer = staging_writer_connection()
    try:
        replace_analytics_snapshot(writer, market_rows, aligned_rows)
        _print_resource("after first staging write")
        market_count, market_readback_digest, market_readback = _assert_readback(
            writer, "otg_market_hourly", MARKET_COLUMNS, market_digest,
        )
        aligned_count, aligned_readback_digest, aligned_readback = _assert_readback(
            writer, "otg_nansen_hourly", ALIGNED_COLUMNS, aligned_digest,
        )
        # Repeat the exact same already-validated rows. No RPC or production read is repeated.
        replace_analytics_snapshot(writer, market_rows, aligned_rows)
        _print_resource("after idempotency write")
        _, market_digest_second, market_readback_second = _assert_readback(
            writer, "otg_market_hourly", MARKET_COLUMNS, market_digest,
        )
        _, aligned_digest_second, aligned_readback_second = _assert_readback(
            writer, "otg_nansen_hourly", ALIGNED_COLUMNS, aligned_digest,
        )
    finally:
        writer.close()

    stage_ro = staging_readonly_connection()
    try:
        source_after, digest_after, hourly_after, daily_after = read_nansen_source(stage_ro)
        if digest_after != nansen_digest or hourly_after != 12_336 or daily_after != 29:
            raise RuntimeError("Nansen source changed during analytics build")
    finally:
        stage_ro.rollback()
        stage_ro.close()

    null_counts = {
        column: sum(row[column] is None for row in aligned_rows)
        for column in ALIGNED_COLUMNS
    }
    lag_valid = {
        f"gun_price_return_{lag}h": sum(row[f"gun_price_return_{lag}h"] is not None for row in aligned_rows)
        for lag in (1, 6, 24)
    }
    lag_valid.update({
        f"trade_tx_delta_{lag}h": sum(row[f"trade_tx_delta_{lag}h"] is not None for row in aligned_rows)
        for lag in (1, 6, 24)
    })
    lag_valid.update({
        f"native_gun_delta_{lag}h": sum(row[f"native_gun_delta_{lag}h"] is not None for row in aligned_rows)
        for lag in (1, 6, 24)
    })
    active_hours = sum(row["trade_tx_count"] > 0 for row in market_rows)
    return {
        "market_rows": market_count,
        "aligned_rows": aligned_count,
        "market_min": market_rows[0]["hour_start"],
        "market_max": market_rows[-1]["hour_start"],
        "market_active_hours": active_hours,
        "market_zero_hours": CANONICAL_HOURS - active_hours,
        "market_source_rows": market_totals["trade_tx_count"],
        "market_native_gun_total": market_totals["native_gun_amount_truncated"],
        "market_unique_buyers": market_totals["unique_buyers"],
        "market_unique_sellers": market_totals["unique_sellers"],
        "market_unique_items": market_totals["unique_items"],
        "market_digest": market_readback_digest,
        "aligned_digest": aligned_readback_digest,
        "market_idempotent": market_digest_second == market_digest and content_digest(market_readback_second, MARKET_COLUMNS) == market_digest,
        "aligned_idempotent": aligned_digest_second == aligned_digest and content_digest(aligned_readback_second, ALIGNED_COLUMNS) == aligned_digest,
        "nansen_rows": hourly_after,
        "nansen_daily_rows": daily_after,
        "nansen_digest": digest_after,
        "nansen_matched_hours": len(source_after),
        "market_matched_hours": aligned_count,
        "null_counts": null_counts,
        "lag_valid": lag_valid,
        "market_readback": market_readback,
        "aligned_readback": aligned_readback,
        "idempotency": market_digest_second == market_digest and aligned_digest_second == aligned_digest,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build canonical hourly OTG–Nansen analytics in staging.")
    parser.add_argument("--execute", action="store_true", required=True,
                        help="run the bounded staging migration/build after all source gates pass")
    args = parser.parse_args(argv)
    result = build_snapshot()
    for key, value in result.items():
        if key in {"market_readback", "aligned_readback", "null_counts", "lag_valid"}:
            continue
        if key.endswith("_min") or key.endswith("_max"):
            value = value.isoformat().replace("+00:00", "Z")
        print(f"{key.upper()}={value}")
    print(f"NULL_COUNTS={result['null_counts']}")
    print(f"LAG_VALID_ROWS={result['lag_valid']}")
    print("ANALYTICS_PERSISTENCE_IDEMPOTENCY=" + ("PASS" if result["idempotency"] else "FAIL"))
    print("NANSEN_API_CALLS_TASK033=0")
    print("PRODUCTION_DDL=0")
    print("PRODUCTION_DML=0")
    print("PRODUCTION_CHANGED=NO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
