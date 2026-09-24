"""Read-only OTG sales ingestion, UTC alignment, and staging analytics helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from hashlib import sha256
import json
import re
from typing import Any, Iterable, Mapping, Sequence
from zoneinfo import ZoneInfo

UTC = timezone.utc
CANONICAL_START = datetime(2025, 4, 25, tzinfo=UTC)
CANONICAL_END = datetime(2026, 9, 20, 23, tzinfo=UTC)
CANONICAL_HOURS = 12_336
OVERLAP_START = datetime(2026, 2, 27, 22, 8, 18)
OVERLAP_END = datetime(2026, 2, 28, 11, 9, 10)
OVERLAP_ROWS = 5_632
OVERLAP_BLOCKS = 4_886
OVERLAP_PLUS_05_ROWS = 3_459
OVERLAP_MINUS_08_ROWS = 2_173
OVERLAP_DIGEST = "08e64456eea3796ce0e1cfa3b475e2ac66f98050cf91ed99fcb6704a290feca6"
OVERLAP_LAST_OLD_UTC = "2026-02-28T06:08:18Z"
OVERLAP_FIRST_NEW_UTC = "2026-02-28T06:09:10Z"
OVERLAP_UTC_MIN = "2026-02-27T17:09:13Z"
OVERLAP_UTC_MAX = "2026-02-28T19:09:04Z"
OVERLAP_DISTINCT_SECONDS = 4_886
EXPECTED_NANSEN_IDENTITY_DIGEST = "73291cb74398292cc1ed38f728e8c686973920fe7c18701c12bea154eb7335a7"
GUNZ_CHAIN_ID = 43_419
DEFAULT_GUNZ_RPC_URL = "https://subnets.avax.network/gunzilla/mainnet/rpc"
RPC_METHOD_CAP = 11_265
PACIFIC = ZoneInfo("America/Los_Angeles")

MARKET_COLUMNS = (
    "hour_start", "hour_end", "trade_tx_count", "native_gun_amount_truncated",
    "unique_buyers", "unique_sellers", "unique_items",
)
ALIGNED_COLUMNS = (
    "hour_start", "hour_end", "market_trade_tx_count", "market_native_gun_amount_truncated",
    "market_unique_buyers", "market_unique_sellers", "market_unique_items",
    "nansen_price_usd", "nansen_token_amount", "nansen_value_usd", "nansen_holders_count",
    "nansen_total_inflows_count", "nansen_total_outflows_count",
    "gun_price_return_1h", "gun_price_return_6h", "gun_price_return_24h",
    "flow_count_imbalance", "flow_count_total",
    "trade_tx_delta_1h", "trade_tx_delta_6h", "trade_tx_delta_24h",
    "native_gun_delta_1h", "native_gun_delta_6h", "native_gun_delta_24h",
)


class AnalyticsContractError(RuntimeError):
    """Raised when source or destination evidence fails the analytics contract."""


@dataclass(frozen=True)
class OverlapEvidence:
    exact_utc_by_tx: Mapping[str, datetime]
    digest: str
    rows: int
    receipts_resolved: int
    blocks_resolved: int
    distinct_blocks: int
    plus_05_rows: int
    minus_08_rows: int
    other_offset_rows: int
    last_old_utc: datetime
    first_new_utc: datetime
    utc_min: datetime
    utc_max: datetime
    distinct_utc_seconds: int
    rpc_method_objects: int


def utc_hour_spine(start: datetime = CANONICAL_START, end: datetime = CANONICAL_END) -> tuple[datetime, ...]:
    """Return an inclusive, UTC-aligned hourly spine."""
    if start.tzinfo is None or end.tzinfo is None:
        raise ValueError("canonical boundaries must be timezone-aware")
    first, last = start.astimezone(UTC), end.astimezone(UTC)
    if any((x.minute, x.second, x.microsecond) != (0, 0, 0) for x in (first, last)) or last < first:
        raise ValueError("canonical boundaries must be ordered hour starts")
    count = int((last - first) / timedelta(hours=1)) + 1
    return tuple(first + i * timedelta(hours=1) for i in range(count))


def reconstruct_non_overlap_timestamp(stored: datetime) -> datetime:
    """Reconstruct UTC outside the conservative overlap using accepted regimes."""
    if stored.tzinfo is not None:
        raise ValueError("stored sales timestamp must be naive")
    if OVERLAP_START <= stored < OVERLAP_END:
        raise AnalyticsContractError("overlap timestamps require exact containing-block resolution")
    if stored < OVERLAP_START:
        return (stored - timedelta(hours=5)).replace(tzinfo=UTC)
    candidates = []
    for fold in (0, 1):
        local = stored.replace(tzinfo=PACIFIC, fold=fold)
        instant = local.astimezone(UTC)
        if instant.astimezone(PACIFIC).replace(tzinfo=None) == stored:
            candidates.append(instant)
    distinct = set(candidates)
    if not distinct:
        raise AnalyticsContractError("nonexistent Pacific local time cannot be reconstructed")
    if len(distinct) > 1:
        raise AnalyticsContractError("ambiguous Pacific local time cannot be reconstructed")
    return next(iter(distinct))


def _iso_naive(value: datetime) -> str:
    if value.tzinfo is not None:
        raise ValueError("stored timestamp must be naive")
    return value.isoformat(timespec="seconds")


def _iso_utc(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValueError("UTC timestamp must be aware")
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def overlap_digest_tuples(tuples: Iterable[tuple[str, str, str]]) -> str:
    """Hash the accepted sorted compact-JSON overlap evidence representation."""
    normalized = sorted(tuple(item) for item in tuples)
    if any(len(item) != 3 or item[2] not in {"UTC+05:00", "UTC-08:00"} for item in normalized):
        raise ValueError("invalid overlap evidence tuple")
    encoded = json.dumps(normalized, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return sha256(encoded).hexdigest()


def validate_overlap_contract(evidence: OverlapEvidence) -> None:
    """Fail closed unless the current chain mapping matches accepted evidence."""
    checks = (
        evidence.rows == OVERLAP_ROWS,
        evidence.receipts_resolved == OVERLAP_ROWS,
        evidence.blocks_resolved == OVERLAP_BLOCKS,
        evidence.distinct_blocks == OVERLAP_BLOCKS,
        evidence.plus_05_rows == OVERLAP_PLUS_05_ROWS,
        evidence.minus_08_rows == OVERLAP_MINUS_08_ROWS,
        evidence.other_offset_rows == 0,
        _iso_utc(evidence.last_old_utc) == OVERLAP_LAST_OLD_UTC,
        _iso_utc(evidence.first_new_utc) == OVERLAP_FIRST_NEW_UTC,
        evidence.last_old_utc < evidence.first_new_utc,
        _iso_utc(evidence.utc_min) == OVERLAP_UTC_MIN,
        _iso_utc(evidence.utc_max) == OVERLAP_UTC_MAX,
        evidence.distinct_utc_seconds == OVERLAP_DISTINCT_SECONDS,
        evidence.digest == OVERLAP_DIGEST,
        evidence.rpc_method_objects <= RPC_METHOD_CAP,
        len(evidence.exact_utc_by_tx) == OVERLAP_ROWS,
    )
    if not all(checks):
        raise AnalyticsContractError("overlap chain evidence differs from accepted contract")


def verify_connection_identity(database: str, transaction_read_only: str, expected_database: str) -> None:
    if database != expected_database:
        raise AnalyticsContractError("database identity does not match pinned target")
    if transaction_read_only != "on":
        raise AnalyticsContractError("connection is not transaction read-only")


def verify_staging_writer_identity(database: str) -> None:
    if database != "server_otg_staging":
        raise AnalyticsContractError("refusing analytics writes outside server_otg_staging")


def resolve_overlap_rows(
    rows: Sequence[tuple[str, datetime]],
    *,
    rpc_url: str = DEFAULT_GUNZ_RPC_URL,
    session: Any | None = None,
    batch_size: int = 50,
) -> OverlapEvidence:
    """Resolve the accepted overlap using chain ID, one receipt per row, and a block cache."""
    import requests

    if len(rows) != OVERLAP_ROWS:
        raise AnalyticsContractError("overlap row population differs from accepted count")
    if session is None:
        session = requests.Session()
    method_objects = 0

    def send(method: str, params: list[Any]) -> Any:
        nonlocal method_objects
        if method_objects + 1 > RPC_METHOD_CAP:
            raise AnalyticsContractError("GUNZ RPC method-object budget exceeded")
        method_objects += 1
        response = session.post(rpc_url, json={"jsonrpc": "2.0", "id": method_objects, "method": method, "params": params}, timeout=120)
        response.raise_for_status()
        payload = response.json()
        if "error" in payload or "result" not in payload or payload["result"] is None:
            raise AnalyticsContractError("GUNZ RPC read was unresolved")
        return payload["result"]

    chain_id = int(send("eth_chainId", []), 16)
    if chain_id != GUNZ_CHAIN_ID:
        raise AnalyticsContractError("unexpected GUNZ RPC chain id")

    def batch(method: str, values: Sequence[str], params_for: Any) -> dict[str, Any]:
        nonlocal method_objects
        resolved: dict[str, Any] = {}
        for base in range(0, len(values), batch_size):
            chunk = values[base:base + batch_size]
            if method_objects + len(chunk) > RPC_METHOD_CAP:
                raise AnalyticsContractError("GUNZ RPC method-object budget exceeded")
            requests_payload = []
            for value in chunk:
                method_objects += 1
                requests_payload.append({"jsonrpc": "2.0", "id": method_objects, "method": method, "params": params_for(value)})
            response = session.post(rpc_url, json=requests_payload, timeout=120)
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, list):
                raise AnalyticsContractError("GUNZ RPC batch response shape is invalid")
            by_id = {item.get("id"): item for item in payload if isinstance(item, dict)}
            for request_item, value in zip(requests_payload, chunk):
                item = by_id.get(request_item["id"])
                if item is not None and "error" not in item and item.get("result") is not None:
                    resolved[value] = item["result"]
        return resolved

    hashes = [tx_hash for tx_hash, _ in rows]
    if len(set(hashes)) != len(hashes):
        raise AnalyticsContractError("duplicate tx hash in overlap input")
    receipt_payloads = batch("eth_getTransactionReceipt", hashes, lambda tx: [tx])
    tx_to_block: dict[str, str] = {}
    for tx_hash, receipt in receipt_payloads.items():
        block = receipt.get("blockNumber")
        if block is not None:
            tx_to_block[tx_hash] = block
    if len(tx_to_block) != OVERLAP_ROWS:
        raise AnalyticsContractError("one or more overlap receipts are unresolved")
    distinct_blocks = sorted(set(tx_to_block.values()), key=lambda value: int(value, 16))
    block_payloads = batch("eth_getBlockByNumber", distinct_blocks, lambda block: [block, False])
    block_to_utc = {
        block: datetime.fromtimestamp(int(payload["timestamp"], 16), UTC)
        for block, payload in block_payloads.items() if payload.get("timestamp") is not None
    }
    if len(block_to_utc) != len(distinct_blocks):
        raise AnalyticsContractError("one or more overlap blocks are unresolved")

    exact_by_tx: dict[str, datetime] = {}
    offset_counts = {"UTC+05:00": 0, "UTC-08:00": 0, "OTHER": 0}
    tuples: list[tuple[str, str, str]] = []
    by_offset: dict[str, list[datetime]] = {"UTC+05:00": [], "UTC-08:00": []}
    all_instants: list[datetime] = []
    for tx_hash, stored in rows:
        block = tx_to_block[tx_hash]
        exact = block_to_utc[block]
        offset = int((stored.replace(tzinfo=UTC) - exact).total_seconds())
        offset_class = "UTC+05:00" if offset == 18_000 else "UTC-08:00" if offset == -28_800 else "OTHER"
        offset_counts[offset_class] += 1
        if offset_class != "OTHER":
            by_offset[offset_class].append(exact)
        exact_by_tx[tx_hash] = exact
        all_instants.append(exact)
        if offset_class != "OTHER":
            tuples.append((_iso_naive(stored), _iso_utc(exact), offset_class))
    if offset_counts["OTHER"]:
        raise AnalyticsContractError("unexpected overlap offset")
    if not by_offset["UTC+05:00"] or not by_offset["UTC-08:00"]:
        raise AnalyticsContractError("one accepted offset regime is absent")
    last_old, first_new = max(by_offset["UTC+05:00"]), min(by_offset["UTC-08:00"])
    digest = overlap_digest_tuples(tuples)
    evidence = OverlapEvidence(
        exact_utc_by_tx=exact_by_tx, digest=digest, rows=len(rows),
        receipts_resolved=len(receipt_payloads), blocks_resolved=len(block_to_utc),
        distinct_blocks=len(distinct_blocks), plus_05_rows=offset_counts["UTC+05:00"],
        minus_08_rows=offset_counts["UTC-08:00"], other_offset_rows=offset_counts["OTHER"],
        last_old_utc=last_old, first_new_utc=first_new,
        utc_min=min(all_instants), utc_max=max(all_instants),
        distinct_utc_seconds=len(set(all_instants)), rpc_method_objects=method_objects,
    )
    validate_overlap_contract(evidence)
    return evidence


def decimal_wire(value: Decimal | None) -> str | None:
    if value is None:
        return None
    if not value.is_finite():
        raise ValueError("non-finite decimal is not serializable")
    if value == 0:
        return "0"
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def _digest_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return _iso_utc(value)
    if isinstance(value, Decimal):
        return decimal_wire(value)
    if isinstance(value, bool) or value is None or isinstance(value, int):
        return value
    raise TypeError(f"unsupported digest value type: {type(value).__name__}")


def content_digest(rows: Sequence[Mapping[str, Any]], columns: Sequence[str]) -> str:
    ordered = sorted(rows, key=lambda row: row["hour_start"])
    payload = [[_digest_value(row[column]) for column in columns] for row in ordered]
    return sha256(json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("utf-8")).hexdigest()


def build_market_spine(aggregates: Mapping[datetime, Mapping[str, Any]], hours: Sequence[datetime]) -> list[dict[str, Any]]:
    result = []
    for hour in hours:
        source = aggregates.get(hour, {})
        row = {
            "hour_start": hour,
            "hour_end": hour + timedelta(hours=1),
            "trade_tx_count": int(source.get("trade_tx_count", 0)),
            "native_gun_amount_truncated": source.get("native_gun_amount_truncated", Decimal(0)),
            "unique_buyers": int(source.get("unique_buyers", 0)),
            "unique_sellers": int(source.get("unique_sellers", 0)),
            "unique_items": int(source.get("unique_items", 0)),
        }
        if row["trade_tx_count"] < 0 or row["native_gun_amount_truncated"] < 0:
            raise AnalyticsContractError("negative market aggregate")
        result.append(row)
    if len(result) != len(hours) or len({row["hour_start"] for row in result}) != len(hours):
        raise AnalyticsContractError("market spine is not one row per hour")
    return result


def aggregate_market_records(records: Iterable[Mapping[str, Any]]) -> tuple[dict[datetime, dict[str, Any]], dict[str, Any]]:
    """Reference aggregation preserving DISTINCT semantics across all input partitions."""
    groups: dict[datetime, dict[str, Any]] = {}
    all_buyers: set[Any] = set()
    all_sellers: set[Any] = set()
    all_items: set[Any] = set()
    total_count = 0
    total_amount = Decimal(0)
    for record in records:
        instant = record["event_utc"]
        if instant.tzinfo is None:
            raise ValueError("event_utc must be timezone-aware")
        utc = instant.astimezone(UTC)
        hour = utc.replace(minute=0, second=0, microsecond=0)
        group = groups.setdefault(hour, {
            "trade_tx_count": 0, "native_gun_amount_truncated": Decimal(0),
            "buyers": set(), "sellers": set(), "items": set(),
        })
        amount = Decimal(record["price"])
        if amount < 0:
            raise AnalyticsContractError("negative native GUN amount")
        group["trade_tx_count"] += 1
        group["native_gun_amount_truncated"] += amount
        for field, key, global_set in (("buyer", "buyers", all_buyers), ("seller", "sellers", all_sellers), ("token_id", "items", all_items)):
            value = record[field]
            if value is not None:
                group[key].add(value)
                global_set.add(value)
        total_count += 1
        total_amount += amount
    for group in groups.values():
        group["unique_buyers"] = len(group.pop("buyers"))
        group["unique_sellers"] = len(group.pop("sellers"))
        group["unique_items"] = len(group.pop("items"))
    totals = {
        "trade_tx_count": total_count,
        "native_gun_amount_truncated": total_amount,
        "unique_buyers": len(all_buyers),
        "unique_sellers": len(all_sellers),
        "unique_items": len(all_items),
    }
    return groups, totals


def percent_change(current: Decimal | None, prior: Decimal | None) -> Decimal | None:
    if current is None or prior is None or prior == 0:
        return None
    return current / prior - Decimal(1)


def _lag_value(rows: Sequence[Mapping[str, Any]], index: int, lag: int, key: str) -> Any:
    return rows[index - lag][key] if index >= lag else None


def align_hourly(
    market_rows: Sequence[Mapping[str, Any]],
    nansen_rows: Mapping[datetime, Mapping[str, Any]],
    hours: Sequence[datetime],
) -> list[dict[str, Any]]:
    """Join exact UTC hour identities and calculate mechanical descriptive features."""
    if tuple(row["hour_start"] for row in market_rows) != tuple(hours):
        raise AnalyticsContractError("market rows do not match canonical UTC spine")
    if set(nansen_rows) != set(hours):
        raise AnalyticsContractError("Nansen rows do not exactly match canonical hours")
    rows: list[dict[str, Any]] = []
    for index, (hour, market) in enumerate(zip(hours, market_rows)):
        nansen = nansen_rows[hour]
        inflows = Decimal(nansen["total_inflows_count"])
        outflows = Decimal(nansen["total_outflows_count"])
        row = {
            "hour_start": hour, "hour_end": hour + timedelta(hours=1),
            "market_trade_tx_count": market["trade_tx_count"],
            "market_native_gun_amount_truncated": market["native_gun_amount_truncated"],
            "market_unique_buyers": market["unique_buyers"],
            "market_unique_sellers": market["unique_sellers"],
            "market_unique_items": market["unique_items"],
            "nansen_price_usd": nansen["price_usd"],
            "nansen_token_amount": nansen["token_amount"],
            "nansen_value_usd": nansen["value_usd"],
            "nansen_holders_count": int(nansen["holders_count"]),
            "nansen_total_inflows_count": inflows,
            "nansen_total_outflows_count": outflows,
            "flow_count_imbalance": inflows - outflows,
            "flow_count_total": inflows + outflows,
        }
        for lag in (1, 6, 24):
            prior_price = _lag_value(rows, index, lag, "nansen_price_usd")
            row[f"gun_price_return_{lag}h"] = percent_change(row["nansen_price_usd"], prior_price)
            prior_count = _lag_value(market_rows, index, lag, "trade_tx_count")
            row[f"trade_tx_delta_{lag}h"] = None if prior_count is None else market["trade_tx_count"] - prior_count
            prior_gun = _lag_value(market_rows, index, lag, "native_gun_amount_truncated")
            row[f"native_gun_delta_{lag}h"] = None if prior_gun is None else market["native_gun_amount_truncated"] - prior_gun
        rows.append(row)
    if len(rows) != len(hours) or len({row["hour_start"] for row in rows}) != len(rows):
        raise AnalyticsContractError("aligned output is not one row per canonical hour")
    return rows


def _env_postgres_kwargs(database: str) -> dict[str, Any]:
    from .postgres import _load_dotenv_if_present
    import os

    _load_dotenv_if_present()
    return {
        "host": os.environ.get("POSTGRES_HOST", "127.0.0.1"),
        "port": int(os.environ.get("POSTGRES_PORT", "5432")),
        "user": os.environ.get("POSTGRES_USER", ""),
        "password": os.environ.get("POSTGRES_PASSWORD", ""),
        "dbname": database,
    }


def production_readonly_connection():
    import psycopg

    kwargs = _env_postgres_kwargs("server_otg")
    kwargs["options"] = "-c default_transaction_read_only=on"
    connection = psycopg.connect(**kwargs)
    connection.execute("SET TRANSACTION READ ONLY")
    database, read_only = connection.execute("SELECT current_database(), current_setting('transaction_read_only')").fetchone()
    verify_connection_identity(database, read_only, "server_otg")
    return connection


def staging_readonly_connection():
    import psycopg

    kwargs = _env_postgres_kwargs("server_otg_staging")
    kwargs["options"] = "-c default_transaction_read_only=on"
    connection = psycopg.connect(**kwargs)
    connection.execute("SET TRANSACTION READ ONLY")
    database, read_only = connection.execute("SELECT current_database(), current_setting('transaction_read_only')").fetchone()
    verify_connection_identity(database, read_only, "server_otg_staging")
    return connection


def staging_writer_connection():
    import psycopg

    connection = psycopg.connect(**_env_postgres_kwargs("server_otg_staging"), autocommit=True)
    database = connection.execute("SELECT current_database()").fetchone()[0]
    verify_staging_writer_identity(database)
    return connection


def read_nansen_source(connection) -> tuple[dict[datetime, dict[str, Any]], str, int, int]:
    """Read and validate only canonical hourly rows, plus retained daily count."""
    hours = utc_hour_spine()
    target = set(hours)
    address = "0x26debd39d5ed069770406fca10a0e4f8d2c743eb"
    hourly_query = """SELECT date, bucket_end, price_usd, token_amount, value_usd, holders_count,
                             total_inflows_count, total_outflows_count
                      FROM nansen.flows
                      WHERE chain='avalanche' AND token_address=%s AND flow_label='smart_money'
                        AND is_complete IS TRUE AND bucket_end-date=interval '1 hour'
                        AND date >= %s AND date <= %s
                      ORDER BY date"""
    rows = connection.execute(hourly_query, (address, CANONICAL_START, CANONICAL_END)).fetchall()
    nansen: dict[datetime, dict[str, Any]] = {}
    identity_pairs = []
    for start, end, price, amount, value, holders, inflows, outflows in rows:
        start_utc = start.astimezone(UTC)
        end_utc = end.astimezone(UTC)
        if start_utc not in target or end_utc != start_utc + timedelta(hours=1) or start_utc in nansen:
            raise AnalyticsContractError("canonical Nansen hourly source contains invalid identity")
        nansen[start_utc] = {
            "price_usd": price, "token_amount": amount, "value_usd": value,
            "holders_count": holders, "total_inflows_count": inflows,
            "total_outflows_count": outflows,
        }
        identity_pairs.append([_iso_utc(start_utc), _iso_utc(end_utc)])
    if set(nansen) != target or len(rows) != CANONICAL_HOURS:
        raise AnalyticsContractError("canonical Nansen hourly source is incomplete")
    identity_digest = sha256(json.dumps(identity_pairs, separators=(",", ":")).encode("utf-8")).hexdigest()
    if identity_digest != EXPECTED_NANSEN_IDENTITY_DIGEST:
        raise AnalyticsContractError("canonical Nansen identity digest changed")
    daily_count = connection.execute(
        """SELECT count(*) FROM nansen.flows WHERE chain='avalanche' AND token_address=%s
             AND flow_label='smart_money' AND is_complete IS TRUE AND bucket_end-date=interval '24 hours'""",
        (address,),
    ).fetchone()[0]
    if daily_count != 29:
        raise AnalyticsContractError("retained canonical Nansen daily count changed")
    return nansen, identity_digest, len(rows), daily_count


def load_overlap_rows(connection) -> list[tuple[str, datetime]]:
    rows = connection.execute(
        "SELECT tx_hash, timestamp FROM public.sales WHERE timestamp >= %s AND timestamp < %s ORDER BY tx_hash",
        (OVERLAP_START, OVERLAP_END),
    ).fetchall()
    if len(rows) != OVERLAP_ROWS:
        raise AnalyticsContractError("production overlap population differs from accepted count")
    return [(str(tx_hash), stored) for tx_hash, stored in rows]


def aggregate_market_production(connection, overlap_rows: Sequence[tuple[str, datetime]], evidence: OverlapEvidence):
    """Aggregate one logical reconstructed production row stream in PostgreSQL."""
    tx_hashes = [tx for tx, _ in overlap_rows]
    exact_times = [evidence.exact_utc_by_tx[tx] for tx in tx_hashes]
    sql = """WITH overlap_map AS (
                 SELECT * FROM unnest(%s::text[], %s::timestamptz[]) AS m(tx_hash, exact_utc)
             ), resolved AS (
                 SELECT s.tx_hash, s.price, s.buyer, s.seller, s.token_id,
                        CASE
                          WHEN s.timestamp < %s::timestamp
                            THEN (s.timestamp - interval '5 hours') AT TIME ZONE 'UTC'
                          WHEN s.timestamp >= %s::timestamp
                            THEN s.timestamp AT TIME ZONE 'America/Los_Angeles'
                          ELSE m.exact_utc
                        END AS event_utc
                 FROM public.sales AS s
                 LEFT JOIN overlap_map AS m ON m.tx_hash=s.tx_hash
                 WHERE s.timestamp >= %s::timestamp AND s.timestamp < %s::timestamp
                   AND (s.timestamp < %s::timestamp OR s.timestamp >= %s::timestamp OR m.tx_hash IS NOT NULL)
             ), scoped AS (
                 SELECT tx_hash, price, buyer, seller, token_id,
                        date_trunc('hour', event_utc AT TIME ZONE 'UTC') AT TIME ZONE 'UTC' AS hour_start
                 FROM resolved
                 WHERE event_utc >= %s::timestamptz AND event_utc < %s::timestamptz
             ), aggregates AS (
                 SELECT hour_start, count(*)::bigint AS trade_tx_count,
                        coalesce(sum(price),0)::numeric AS native_gun_amount_truncated,
                        count(DISTINCT buyer)::bigint AS unique_buyers,
                        count(DISTINCT seller)::bigint AS unique_sellers,
                        count(DISTINCT token_id)::bigint AS unique_items,
                        grouping(hour_start) AS is_total
                 FROM scoped
                 GROUP BY GROUPING SETS ((hour_start),())
             )
             SELECT hour_start, trade_tx_count, native_gun_amount_truncated,
                    unique_buyers, unique_sellers, unique_items, is_total
             FROM aggregates ORDER BY is_total, hour_start"""
    broad_start = datetime(2025, 4, 24)
    broad_end = datetime(2026, 9, 22)
    params = (
        tx_hashes, exact_times, OVERLAP_START, OVERLAP_END, broad_start, broad_end,
        OVERLAP_START, OVERLAP_END, CANONICAL_START, CANONICAL_END + timedelta(hours=1),
    )
    rows = connection.execute(sql, params).fetchall()
    hourly: dict[datetime, dict[str, Any]] = {}
    totals = None
    for hour_start, count, amount, buyers, sellers, items, is_total in rows:
        aggregate = {
            "trade_tx_count": int(count), "native_gun_amount_truncated": amount,
            "unique_buyers": int(buyers), "unique_sellers": int(sellers), "unique_items": int(items),
        }
        if is_total:
            totals = aggregate
        else:
            utc_start = hour_start.astimezone(UTC)
            if utc_start in hourly:
                raise AnalyticsContractError("production aggregation produced duplicate hour")
            hourly[utc_start] = aggregate
    if totals is None:
        totals = {"trade_tx_count": 0, "native_gun_amount_truncated": Decimal(0), "unique_buyers": 0, "unique_sellers": 0, "unique_items": 0}
    return hourly, totals


def replace_analytics_snapshot(connection, market_rows: Sequence[Mapping[str, Any]], aligned_rows: Sequence[Mapping[str, Any]]) -> None:
    """Atomically replace only the two pinned staging analytics tables."""
    database = connection.execute("SELECT current_database()").fetchone()[0]
    verify_staging_writer_identity(database)
    if connection.execute("SHOW transaction_read_only").fetchone()[0] != "off":
        raise AnalyticsContractError("staging writer connection is unexpectedly read-only")
    if len(market_rows) != CANONICAL_HOURS or len(aligned_rows) != CANONICAL_HOURS:
        raise AnalyticsContractError("refusing to persist incomplete analytical snapshot")
    try:
        with connection.transaction():
            connection.execute("DELETE FROM nansen.otg_nansen_hourly")
            connection.execute("DELETE FROM nansen.otg_market_hourly")
            connection.executemany(
                """INSERT INTO nansen.otg_market_hourly
                   (hour_start,hour_end,trade_tx_count,native_gun_amount_truncated,unique_buyers,unique_sellers,unique_items)
                   VALUES (%(hour_start)s,%(hour_end)s,%(trade_tx_count)s,%(native_gun_amount_truncated)s,%(unique_buyers)s,%(unique_sellers)s,%(unique_items)s)""",
                market_rows,
            )
            connection.executemany(
                """INSERT INTO nansen.otg_nansen_hourly
                   (hour_start,hour_end,market_trade_tx_count,market_native_gun_amount_truncated,market_unique_buyers,
                    market_unique_sellers,market_unique_items,nansen_price_usd,nansen_token_amount,nansen_value_usd,
                    nansen_holders_count,nansen_total_inflows_count,nansen_total_outflows_count,gun_price_return_1h,
                    gun_price_return_6h,gun_price_return_24h,flow_count_imbalance,flow_count_total,trade_tx_delta_1h,
                    trade_tx_delta_6h,trade_tx_delta_24h,native_gun_delta_1h,native_gun_delta_6h,native_gun_delta_24h)
                   VALUES (%(hour_start)s,%(hour_end)s,%(market_trade_tx_count)s,%(market_native_gun_amount_truncated)s,
                    %(market_unique_buyers)s,%(market_unique_sellers)s,%(market_unique_items)s,%(nansen_price_usd)s,
                    %(nansen_token_amount)s,%(nansen_value_usd)s,%(nansen_holders_count)s,%(nansen_total_inflows_count)s,
                    %(nansen_total_outflows_count)s,%(gun_price_return_1h)s,%(gun_price_return_6h)s,%(gun_price_return_24h)s,
                    %(flow_count_imbalance)s,%(flow_count_total)s,%(trade_tx_delta_1h)s,%(trade_tx_delta_6h)s,
                    %(trade_tx_delta_24h)s,%(native_gun_delta_1h)s,%(native_gun_delta_6h)s,%(native_gun_delta_24h)s)""",
                aligned_rows,
            )
    except Exception:
        connection.rollback()
        raise


def read_analytics_rows(connection, table: str, columns: Sequence[str]) -> list[dict[str, Any]]:
    if table not in {"otg_market_hourly", "otg_nansen_hourly"}:
        raise ValueError("unsupported analytics readback table")
    if tuple(columns) not in {MARKET_COLUMNS, ALIGNED_COLUMNS}:
        raise ValueError("unsupported analytics column selection")
    selected = ",".join(columns)
    result = connection.execute(f"SELECT {selected} FROM nansen.{table} ORDER BY hour_start").fetchall()
    return [dict(zip(columns, row)) for row in result]
