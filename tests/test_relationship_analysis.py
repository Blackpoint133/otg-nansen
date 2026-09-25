from datetime import datetime, timezone
import math
from zoneinfo import ZoneInfo

import pytest

from otg_nansen import relationship_analysis as ra
from otg_nansen.market_analytics import utc_hour_spine

UTC = timezone.utc


def test_pearson_positive_negative_and_constant():
    assert ra.pearson([1, 2, 3], [2, 4, 6]) == pytest.approx(1)
    assert ra.pearson([1, 2, 3], [6, 4, 2]) == pytest.approx(-1)
    assert ra.pearson([1, 1, 1], [2, 3, 4]) is None


def test_rank_ties_and_spearman():
    assert ra.average_ranks([4, 1, 1, 8]) == [3, 1.5, 1.5, 4]
    assert ra.spearman([1, 2, 3], [10, 20, 30]) == pytest.approx(1)
    assert ra.spearman([1, 2, 3], [30, 20, 10]) == pytest.approx(-1)
    assert ra.spearman([1, 1, 2, 3], [4, 4, 5, 6]) == pytest.approx(1)
    assert ra.spearman([1, 1, 1], [1, 2, 3]) is None


def test_missing_pair_filtering():
    assert ra.pearson([1, None, 3, math.inf, 5], [1, 2, 3, 4, 5]) == pytest.approx(1)
    assert ra.spearman([1, None, 3, 4], [1, 2, 3, 4]) == pytest.approx(1)


def test_quantile_interpolates_preregistered_position():
    assert ra.deterministic_quantile([4, 1, 3, 2], 0.25) == pytest.approx(1.75)
    assert ra.deterministic_quantile([4, 1, 3, 2], 0.95) == pytest.approx(3.85)


def test_hour_of_week_and_residual_coverage():
    hours = utc_hour_spine()[:168]
    assert {ra.hour_of_week(hour) for hour in hours} == set(range(168))
    values = [0] * len(hours)
    residuals, coverage = ra.seasonal_residual(values, hours)
    assert coverage == 168
    assert residuals == [0.0] * 168


def test_delta_log1p_first_is_null():
    result = ra.delta_log1p([0, 1, 3])
    assert result[0] is None
    assert result[1] == pytest.approx(math.log(2))
    assert result[2] == pytest.approx(math.log(4) - math.log(2))


def test_lag_direction_and_all_fixed_lags():
    driver = list(range(40))
    outcome = [100 + i for i in range(40)]
    for lag in ra.LAGS:
        x, y = ra.pair_at_lag(driver, outcome, lag)
        assert x == driver[:len(driver) - lag] if lag else x == driver
        assert y == outcome[lag:]
        if lag:
            assert x[-1] == driver[-1 - lag]
            assert y[-1] == outcome[-1]


def _synthetic_full_rows():
    hours = utc_hour_spine()
    rows = []
    for i, hour in enumerate(hours):
        rows.append({
            "hour_start": hour,
            "gun_price_return_1h": (i % 101 - 50) / 10000,
            "flow_count_imbalance": (i % 9) - 4,
            "flow_count_total": 20,
            "market_trade_tx_count": i % 30,
            "market_native_gun_amount_truncated": i % 17,
            "market_unique_buyers": i % 12,
        })
    return rows


def test_relationship_matrix_has_48_cells_and_eight_fixed_blocks():
    rows = _synthetic_full_rows()
    matrix, coverage = ra.build_relationship_matrix(rows)
    assert len(matrix) == 48
    assert set(coverage.values()) == {168}
    assert {(r["driver"], r["outcome"], r["outcome_form"], r["lag_hours"]) for r in matrix}.__len__() == 48
    stats = ra.block_stability([1.0] * 12336, [float(i) for i in range(12336)], 0)
    assert stats["block_valid_count"] == 0  # rank coefficient undefined for constant driver
    assert stats["block_positive_count"] + stats["block_negative_count"] + stats["block_zero_count"] <= 8
    varying = ra.block_stability([float(i) for i in range(12336)], [float(i) for i in range(12336)], 0)
    assert ra.BLOCK_COUNT == 8 and ra.BLOCK_SIZE == 1542
    assert varying["block_valid_count"] == 8
    assert varying["block_spearman_median"] == pytest.approx(1)


def test_block_coefficients_null_with_insufficient_valid_pairs():
    driver = [None] * 12336
    outcome = [float(i) for i in range(12336)]
    stats = ra.block_stability(driver, outcome, 0)
    assert stats["block_valid_count"] == 0
    assert stats["block_spearman_median"] is None


def test_event_thresholds_decluster_extreme_and_earliest_tie():
    returns = [0.0] * 80
    returns[10], returns[20], returns[45] = 0.2, -0.9, 0.9
    assert ra.decluster_candidates([10, 20, 45], returns) == [20, 45]
    # Equal absolute values in one cluster retain the earliest candidate.
    returns[10], returns[34] = 0.9, -0.9
    assert ra.decluster_candidates([10, 34], returns) == [10]


def test_event_boundary_eligibility_and_response_baseline():
    assert ra.eligible_events([0, 1, 5, 6], 31) == [1, 5, 6]
    rows = [{name: i for name in ra.OUTCOMES} for i in range(30)]
    responses = ra.event_responses(rows, [3])
    for horizon in ra.EVENT_HORIZONS:
        expected = math.log1p(3 + horizon) - math.log1p(2)
        assert responses[(horizon, ra.OUTCOMES[0])][0] == pytest.approx(expected)


def test_bootstrap_is_reproducible_and_seed_specific(monkeypatch):
    values = [-2.0, -1.0, 1.0, 3.0]
    first = ra.bootstrap_median_interval(values, 3401)
    assert first == ra.bootstrap_median_interval(values, 3401)
    seeds = []
    original = ra.bootstrap_median_interval

    def recording_bootstrap(values, seed, **kwargs):
        seeds.append(seed)
        return original(values, seed, **kwargs)

    monkeypatch.setattr(ra, "bootstrap_median_interval", recording_bootstrap)
    ra.build_event_summary(_synthetic_full_rows())
    # The fixed formula gives 24 distinct direction/outcome/horizon streams.
    expected = {
        3401 + direction * 100 + outcome * 10 + horizon
        for direction in (0, 1) for outcome in range(3) for horizon in range(4)
    }
    assert len(expected) == 24
    assert set(seeds) == expected


def test_event_summary_has_24_aggregate_cells_without_timestamps():
    rows = _synthetic_full_rows()
    summary, metadata = ra.build_event_summary(rows)
    assert len(summary) == 24
    assert set(r["horizon_hours"] for r in summary) == {0, 1, 6, 24}
    serialized = ra.csv_bytes(summary, ra.EVENT_FIELDS).decode()
    assert "hour_start" not in serialized
    assert "timestamp" not in serialized
    assert metadata["positive_candidate_count"] > 0
    assert metadata["negative_candidate_count"] > 0
    valid = [float(row["gun_price_return_1h"]) for row in rows]
    assert metadata["q05"] == ra.deterministic_quantile(valid, 0.05)
    assert metadata["q95"] == ra.deterministic_quantile(valid, 0.95)


def test_deterministic_artifact_order_and_digest():
    rows = [{"driver": "b", "lag_hours": 1}, {"driver": "a", "lag_hours": 0}]
    ordered = sorted(rows, key=lambda r: (r["driver"], r["lag_hours"]))
    assert ra.csv_bytes(ordered, ("driver", "lag_hours")) == ra.csv_bytes(ordered, ("driver", "lag_hours"))
    assert ra.logical_rows_digest(ordered, ("driver", "lag_hours")) == ra.logical_rows_digest(ordered, ("driver", "lag_hours"))
    assert ra.logical_rows_digest(ordered, ("driver", "lag_hours")) != ra.logical_rows_digest(list(reversed(ordered)), ("driver", "lag_hours"))


def test_snapshot_digest_fails_closed(monkeypatch):
    monkeypatch.setattr(ra, "content_digest", lambda *_: "wrong")
    monkeypatch.setattr(ra, "CANONICAL_HOURS", 0)
    monkeypatch.setattr(ra, "utc_hour_spine", lambda: ())
    with pytest.raises(ValueError, match="digest mismatch"):
        ra.validate_snapshot([])


def test_fall_back_distinct_instants_are_not_collapsed_after_utc_normalization():
    zone = ZoneInfo("America/Los_Angeles")
    first = datetime(2025, 11, 2, 8, 30, tzinfo=UTC).astimezone(zone)
    second = datetime(2025, 11, 2, 9, 30, tzinfo=UTC).astimezone(zone)
    assert first.hour == second.hour == 1
    assert first.fold != second.fold
    assert first == second  # demonstrates local ZoneInfo comparison hazard
    assert first.astimezone(UTC) != second.astimezone(UTC)
    sequence = [
        datetime(2025, 11, 2, 7, 0, tzinfo=UTC).astimezone(zone),
        first, second,
        datetime(2025, 11, 2, 10, 0, tzinfo=UTC).astimezone(zone),
    ]
    normalized = [value.astimezone(UTC) for value in sequence]
    assert len(set(normalized)) == 4
    assert normalized == sorted(normalized)
