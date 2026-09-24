from contextlib import nullcontext
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import re

import pytest

from otg_nansen import market_analytics as ma

UTC = timezone.utc


def test_fixed_utc_plus_05_conversion():
    stored = datetime(2025, 5, 1, 5)
    assert ma.reconstruct_non_overlap_timestamp(stored) == datetime(2025, 5, 1, tzinfo=UTC)


def test_pacific_standard_and_daylight_conversions():
    assert ma.reconstruct_non_overlap_timestamp(datetime(2026, 3, 1, 1)) == datetime(2026, 3, 1, 9, tzinfo=UTC)
    assert ma.reconstruct_non_overlap_timestamp(datetime(2026, 8, 10, 1)) == datetime(2026, 8, 10, 8, tzinfo=UTC)


def test_pacific_spring_forward_behavior():
    assert ma.reconstruct_non_overlap_timestamp(datetime(2026, 3, 8, 3, 30)) == datetime(2026, 3, 8, 10, 30, tzinfo=UTC)
    with pytest.raises(ma.AnalyticsContractError, match="nonexistent"):
        ma.reconstruct_non_overlap_timestamp(datetime(2026, 3, 8, 2, 30))


@pytest.mark.parametrize("value", [ma.OVERLAP_START, ma.OVERLAP_END - timedelta(seconds=1)])
def test_overlap_range_requires_exact_block(value):
    with pytest.raises(ma.AnalyticsContractError, match="overlap"):
        ma.reconstruct_non_overlap_timestamp(value)


def test_canonical_hour_boundaries_and_spine():
    hours = ma.utc_hour_spine()
    assert len(hours) == 12_336
    assert hours[0] == datetime(2025, 4, 25, tzinfo=UTC)
    assert hours[-1] == datetime(2026, 9, 20, 23, tzinfo=UTC)
    assert all(b - a == timedelta(hours=1) for a, b in zip(hours, hours[1:]))
    assert ma.utc_hour_spine(datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 1, 1, 1, tzinfo=UTC)) == hours[:0] + (
        datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 1, 1, 1, tzinfo=UTC))


def _tiny_rpc_contract(monkeypatch):
    old = datetime(2026, 2, 28, 6, 8, 18, tzinfo=UTC)
    new = datetime(2026, 2, 28, 6, 9, 10, tzinfo=UTC)
    monkeypatch.setattr(ma, "OVERLAP_ROWS", 2)
    monkeypatch.setattr(ma, "OVERLAP_BLOCKS", 2)
    monkeypatch.setattr(ma, "OVERLAP_PLUS_05_ROWS", 1)
    monkeypatch.setattr(ma, "OVERLAP_MINUS_08_ROWS", 1)
    monkeypatch.setattr(ma, "OVERLAP_LAST_OLD_UTC", ma._iso_utc(old))
    monkeypatch.setattr(ma, "OVERLAP_FIRST_NEW_UTC", ma._iso_utc(new))
    monkeypatch.setattr(ma, "OVERLAP_UTC_MIN", ma._iso_utc(old))
    monkeypatch.setattr(ma, "OVERLAP_UTC_MAX", ma._iso_utc(new))
    monkeypatch.setattr(ma, "OVERLAP_DISTINCT_SECONDS", 2)
    tuples = [
        ("2026-02-28T11:08:18", ma._iso_utc(old), "UTC+05:00"),
        ("2026-02-27T22:09:10", ma._iso_utc(new), "UTC-08:00"),
    ]
    monkeypatch.setattr(ma, "OVERLAP_DIGEST", ma.overlap_digest_tuples(tuples))
    return old, new


class FakeRPC:
    def __init__(self, old, new, unresolved_receipt=None, unresolved_block=None, unexpected=False):
        self.old, self.new = old, new
        self.unresolved_receipt = unresolved_receipt
        self.unresolved_block = unresolved_block
        self.unexpected = unexpected
        self.calls = []

    def post(self, url, *, json, timeout):
        del url, timeout
        if isinstance(json, dict):
            self.calls.append((json["method"], tuple(json["params"])))
            return FakeResponse({"result": hex(ma.GUNZ_CHAIN_ID)})
        results = []
        for item in json:
            method, params = item["method"], item["params"]
            self.calls.append((method, tuple(params)))
            if method == "eth_getTransactionReceipt":
                tx = params[0]
                if tx == self.unresolved_receipt:
                    results.append({"jsonrpc": "2.0", "id": item["id"], "result": None})
                else:
                    results.append({"jsonrpc": "2.0", "id": item["id"], "result": {"blockNumber": "0x1" if tx.startswith("old") else "0x2"}})
            elif method == "eth_getBlockByNumber":
                block = params[0]
                if block == self.unresolved_block:
                    results.append({"jsonrpc": "2.0", "id": item["id"], "result": None})
                    continue
                instant = self.old if block == "0x1" else self.new
                if self.unexpected and block == "0x2":
                    instant = datetime(2026, 2, 28, 6, 9, 11, tzinfo=UTC)
                results.append({"jsonrpc": "2.0", "id": item["id"], "result": {"timestamp": hex(int(instant.timestamp()))}})
        return FakeResponse(results)


class FakeResponse:
    def __init__(self, payload): self.payload = payload
    def raise_for_status(self): pass
    def json(self): return self.payload


def _tiny_rows():
    return [
        ("old", datetime(2026, 2, 28, 11, 8, 18)),
        ("new", datetime(2026, 2, 27, 22, 9, 10)),
    ]


def test_overlap_digest_and_rpc_block_cache(monkeypatch):
    old, new = _tiny_rpc_contract(monkeypatch)
    session = FakeRPC(old, new)
    evidence = ma.resolve_overlap_rows(_tiny_rows(), session=session, batch_size=1)
    assert evidence.rows == 2
    assert evidence.digest == ma.OVERLAP_DIGEST
    assert evidence.plus_05_rows == 1 and evidence.minus_08_rows == 1
    block_calls = [call for call in session.calls if call[0] == "eth_getBlockByNumber"]
    assert len(block_calls) == 2
    assert len({call[1][0] for call in block_calls}) == 2
    assert evidence.rpc_method_objects == 5


def test_multiple_receipts_share_one_cached_block_request(monkeypatch):
    old, new = _tiny_rpc_contract(monkeypatch)
    monkeypatch.setattr(ma, "OVERLAP_ROWS", 3)
    monkeypatch.setattr(ma, "OVERLAP_PLUS_05_ROWS", 2)
    tuples = [
        ("2026-02-28T11:08:18", ma._iso_utc(old), "UTC+05:00"),
        ("2026-02-28T11:08:18", ma._iso_utc(old), "UTC+05:00"),
        ("2026-02-27T22:09:10", ma._iso_utc(new), "UTC-08:00"),
    ]
    monkeypatch.setattr(ma, "OVERLAP_DIGEST", ma.overlap_digest_tuples(tuples))
    rows = [
        ("old-1", datetime(2026, 2, 28, 11, 8, 18)),
        ("old-2", datetime(2026, 2, 28, 11, 8, 18)),
        ("new", datetime(2026, 2, 27, 22, 9, 10)),
    ]
    session = FakeRPC(old, new)
    evidence = ma.resolve_overlap_rows(rows, session=session, batch_size=3)
    block_calls = [call for call in session.calls if call[0] == "eth_getBlockByNumber"]
    assert evidence.distinct_blocks == 2
    assert len(block_calls) == 2


def test_overlap_unresolved_receipt_fails_closed(monkeypatch):
    old, new = _tiny_rpc_contract(monkeypatch)
    with pytest.raises(ma.AnalyticsContractError, match="receipts"):
        ma.resolve_overlap_rows(_tiny_rows(), session=FakeRPC(old, new, unresolved_receipt="new"), batch_size=2)


def test_overlap_unresolved_block_fails_closed(monkeypatch):
    old, new = _tiny_rpc_contract(monkeypatch)
    with pytest.raises(ma.AnalyticsContractError, match="blocks"):
        ma.resolve_overlap_rows(_tiny_rows(), session=FakeRPC(old, new, unresolved_block="0x2"), batch_size=2)


def test_overlap_unexpected_offset_fails_closed(monkeypatch):
    old, new = _tiny_rpc_contract(monkeypatch)
    with pytest.raises(ma.AnalyticsContractError, match="unexpected overlap offset"):
        ma.resolve_overlap_rows(_tiny_rows(), session=FakeRPC(old, new, unexpected=True), batch_size=2)


def test_overlap_budget_preflight_fails_closed(monkeypatch):
    old, new = _tiny_rpc_contract(monkeypatch)
    monkeypatch.setattr(ma, "RPC_METHOD_CAP", 2)
    session = FakeRPC(old, new)
    with pytest.raises(ma.AnalyticsContractError, match="budget"):
        ma.resolve_overlap_rows(_tiny_rows(), session=session, batch_size=2)
    assert [call[0] for call in session.calls] == ["eth_chainId"]


def test_overlap_digest_contract_gate_rejects_change(monkeypatch):
    _tiny_rpc_contract(monkeypatch)
    evidence = ma.OverlapEvidence(
        exact_utc_by_tx={str(i): datetime(2026, 1, 1, tzinfo=UTC) for i in range(2)},
        digest=ma.OVERLAP_DIGEST, rows=2, receipts_resolved=2, blocks_resolved=2, distinct_blocks=2,
        plus_05_rows=1, minus_08_rows=1, other_offset_rows=0,
        last_old_utc=datetime.fromisoformat(ma.OVERLAP_LAST_OLD_UTC.replace("Z", "+00:00")),
        first_new_utc=datetime.fromisoformat(ma.OVERLAP_FIRST_NEW_UTC.replace("Z", "+00:00")),
        utc_min=datetime.fromisoformat(ma.OVERLAP_UTC_MIN.replace("Z", "+00:00")),
        utc_max=datetime.fromisoformat(ma.OVERLAP_UTC_MAX.replace("Z", "+00:00")),
        distinct_utc_seconds=2, rpc_method_objects=5,
    )
    ma.validate_overlap_contract(evidence)
    with pytest.raises(ma.AnalyticsContractError):
        ma.validate_overlap_contract(ma.OverlapEvidence(**{**evidence.__dict__, "digest": "0" * 64}))


def test_read_only_and_staging_database_guards():
    ma.verify_connection_identity("server_otg", "on", "server_otg")
    with pytest.raises(ma.AnalyticsContractError): ma.verify_connection_identity("server_otg", "off", "server_otg")
    with pytest.raises(ma.AnalyticsContractError): ma.verify_connection_identity("server_otg_staging", "on", "server_otg")
    ma.verify_staging_writer_identity("server_otg_staging")
    with pytest.raises(ma.AnalyticsContractError): ma.verify_staging_writer_identity("server_otg")


def test_zero_activity_hour_preserved_and_market_aggregate_values():
    h0, h1 = datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 1, 1, 1, tzinfo=UTC)
    groups, totals = ma.aggregate_market_records([
        {"event_utc": h0 + timedelta(minutes=1), "price": Decimal("4"), "buyer": "b1", "seller": "s1", "token_id": 10},
        {"event_utc": h0 + timedelta(minutes=2), "price": Decimal("2"), "buyer": "b1", "seller": "s2", "token_id": 11},
        {"event_utc": h1 + timedelta(minutes=1), "price": Decimal("5"), "buyer": "b2", "seller": "s1", "token_id": 11},
    ])
    rows = ma.build_market_spine(groups, (h0, h1, h1 + timedelta(hours=1)))
    assert [r["trade_tx_count"] for r in rows] == [2, 1, 0]
    assert [r["native_gun_amount_truncated"] for r in rows] == [Decimal(6), Decimal(5), Decimal(0)]
    assert rows[-1]["unique_buyers"] == rows[-1]["unique_sellers"] == rows[-1]["unique_items"] == 0
    assert totals == {"trade_tx_count": 3, "native_gun_amount_truncated": Decimal(11), "unique_buyers": 2, "unique_sellers": 2, "unique_items": 2}


def test_distinct_counts_are_not_summed_across_partitions():
    boundary = datetime(2026, 2, 28, 6, tzinfo=UTC)
    records = [
        {"event_utc": boundary + timedelta(minutes=1), "price": 1, "buyer": "same", "seller": "s1", "token_id": 9},
        {"event_utc": boundary + timedelta(minutes=2), "price": 1, "buyer": "same", "seller": "s2", "token_id": 9},
    ]
    groups, totals = ma.aggregate_market_records(records)
    assert groups[boundary]["unique_buyers"] == 1
    assert groups[boundary]["unique_items"] == 1
    assert totals["unique_buyers"] == 1
    assert totals["unique_sellers"] == 2


def test_percent_change_zero_denominator_is_null():
    assert ma.percent_change(Decimal(4), Decimal(0)) is None
    assert ma.percent_change(None, Decimal(1)) is None
    assert ma.percent_change(Decimal(3), Decimal(2)) == Decimal("0.5")


def test_alignment_lags_and_flow_arithmetic():
    hours = ma.utc_hour_spine(datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 1, 2, 1, tzinfo=UTC))
    markets = ma.build_market_spine({}, hours)
    nansen = {
        hour: {"price_usd": Decimal("2") if i == 0 else Decimal(0) if i == 1 else Decimal(i + 2),
               "token_amount": Decimal(i), "value_usd": Decimal(i), "holders_count": 7,
               "total_inflows_count": Decimal(5), "total_outflows_count": Decimal(2)}
        for i, hour in enumerate(hours)
    }
    aligned = ma.align_hourly(markets, nansen, hours)
    assert aligned[0]["flow_count_imbalance"] == Decimal(3)
    assert aligned[0]["flow_count_total"] == Decimal(7)
    assert aligned[1]["gun_price_return_1h"] == Decimal(-1)
    assert aligned[2]["gun_price_return_1h"] is None  # zero lag denominator
    assert aligned[8]["gun_price_return_6h"] == Decimal(10) / Decimal(4) - 1
    assert aligned[24]["gun_price_return_24h"] == Decimal(26) / Decimal(2) - 1
    assert aligned[0]["trade_tx_delta_1h"] is None
    assert aligned[24]["trade_tx_delta_24h"] == 0


def test_exact_nansen_hour_alignment_required():
    hours = ma.utc_hour_spine(datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 1, 1, tzinfo=UTC))
    market = ma.build_market_spine({}, hours)
    with pytest.raises(ma.AnalyticsContractError, match="exactly match"):
        ma.align_hourly(market, {}, hours)


def test_deterministic_digest_decimal_and_utc_serialization():
    rows = [{"hour_start": datetime(2026, 1, 1, tzinfo=UTC), "value": Decimal("10.5000"), "null": None}]
    assert ma.content_digest(rows, ("hour_start", "value", "null")) == ma.content_digest(rows, ("hour_start", "value", "null"))
    assert ma.decimal_wire(Decimal("1E+4")) == "10000"
    assert ma.decimal_wire(Decimal("0.000")) == "0"
    assert re.fullmatch(r"[0-9a-f]{64}", ma.content_digest(rows, ("hour_start", "value", "null")))


class FakeWriter:
    def __init__(self, database="server_otg_staging", read_only="off"):
        self.database, self.read_only = database, read_only
        self.deletes = []
        self.inserted = {"market": 0, "aligned": 0}
    def execute(self, sql):
        if sql == "SELECT current_database()": return FakeFetch((self.database,))
        if sql == "SHOW transaction_read_only": return FakeFetch((self.read_only,))
        if sql.startswith("DELETE FROM"):
            self.deletes.append(sql)
        return FakeFetch(None)
    def executemany(self, sql, rows):
        bucket = "market" if "otg_market_hourly" in sql else "aligned"
        self.inserted[bucket] += len(rows)
    def transaction(self): return nullcontext()
    def rollback(self): pass


class FakeFetch:
    def __init__(self, value): self.value = value
    def fetchone(self): return self.value


def test_atomic_staging_replacement_is_idempotent_and_pinned():
    hours = ma.utc_hour_spine()
    market = ma.build_market_spine({}, hours)
    nansen = {h: {"price_usd": Decimal(1), "token_amount": Decimal(0), "value_usd": Decimal(0),
                  "holders_count": 0, "total_inflows_count": Decimal(0), "total_outflows_count": Decimal(0)} for h in hours}
    aligned = ma.align_hourly(market, nansen, hours)
    writer = FakeWriter()
    ma.replace_analytics_snapshot(writer, market, aligned)
    ma.replace_analytics_snapshot(writer, market, aligned)
    assert len(writer.deletes) == 4
    assert writer.inserted == {"market": 2 * ma.CANONICAL_HOURS, "aligned": 2 * ma.CANONICAL_HOURS}
    with pytest.raises(ma.AnalyticsContractError): ma.replace_analytics_snapshot(FakeWriter("server_otg"), market, aligned)
