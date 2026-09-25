"""Preregistered, descriptive OTG–GUN hourly relationship analysis.

All statistical functions are pure. The optional CLI reads only the ratified
aligned snapshot from staging and writes aggregate artifacts locally.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
import math
import random
import statistics
from typing import Any, Mapping, Sequence

from .market_analytics import (
    ALIGNED_COLUMNS, CANONICAL_END, CANONICAL_HOURS, CANONICAL_START,
    EXPECTED_NANSEN_IDENTITY_DIGEST, content_digest, read_analytics_rows,
    staging_readonly_connection, utc_hour_spine,
)

EXPECTED_SNAPSHOT_DIGEST = "9ac2109500aea84160555928d297b7efdcd551e23f3259bee5482a1ae5ed19f8"
METHODOLOGY_VERSION = "034-preregistered-v1"
DRIVERS = ("gun_price_return_1h", "flow_imbalance_share")
OUTCOMES = ("market_trade_tx_count", "market_native_gun_amount_truncated", "market_unique_buyers")
OUTCOME_FORMS = ("hour_of_week_seasonal_residual", "delta_log1p_1h")
LAGS = (0, 1, 6, 24)
BLOCK_COUNT = 8
BLOCK_SIZE = 1542
EVENT_HORIZONS = (0, 1, 6, 24)
BOOTSTRAP_REPLICATES = 2000
BOOTSTRAP_BASE_SEED = 3401

RELATIONSHIP_FIELDS = (
    "driver", "outcome", "outcome_form", "lag_hours", "n", "pearson_r",
    "spearman_rho", "block_valid_count", "block_spearman_median",
    "block_spearman_min", "block_spearman_max", "block_positive_count",
    "block_negative_count", "block_zero_count",
)
EVENT_FIELDS = (
    "direction", "outcome", "horizon_hours", "event_count", "threshold_return",
    "mean_response", "median_response", "q25", "q75",
    "bootstrap_median_ci_low", "bootstrap_median_ci_high", "low_event_count",
)


def _finite(value: Any) -> bool:
    if value is None:
        return False
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError, OverflowError):
        return False


def average_ranks(values: Sequence[float]) -> list[float]:
    indexed = sorted(enumerate(values), key=lambda item: item[1])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(indexed):
        j = i + 1
        while j < len(indexed) and indexed[j][1] == indexed[i][1]:
            j += 1
        rank = ((i + 1) + j) / 2.0
        for k in range(i, j):
            ranks[indexed[k][0]] = rank
        i = j
    return ranks


def pearson(x: Sequence[float | None], y: Sequence[float | None]) -> float | None:
    pairs = [(float(a), float(b)) for a, b in zip(x, y) if _finite(a) and _finite(b)]
    n = len(pairs)
    if n < 3:
        return None
    mx = sum(a for a, _ in pairs) / n
    my = sum(b for _, b in pairs) / n
    numerator = sum((a - mx) * (b - my) for a, b in pairs)
    sx = sum((a - mx) ** 2 for a, _ in pairs)
    sy = sum((b - my) ** 2 for _, b in pairs)
    denominator = math.sqrt(sx * sy)
    return None if denominator == 0 else numerator / denominator


def spearman(x: Sequence[float | None], y: Sequence[float | None]) -> float | None:
    pairs = [(float(a), float(b)) for a, b in zip(x, y) if _finite(a) and _finite(b)]
    if len(pairs) < 3:
        return None
    return pearson(average_ranks([a for a, _ in pairs]), average_ranks([b for _, b in pairs]))


def deterministic_quantile(values: Sequence[float], q: float) -> float:
    if not values or not 0 <= q <= 1:
        raise ValueError("quantile requires nonempty values and q in [0,1]")
    ordered = sorted(float(v) for v in values)
    position = (len(ordered) - 1) * q
    lower, upper = math.floor(position), math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def hour_of_week(hour: datetime) -> int:
    if hour.tzinfo is None:
        raise ValueError("hour must be timezone-aware")
    utc = hour.astimezone(timezone.utc)
    return utc.weekday() * 24 + utc.hour


def log1p_values(values: Sequence[Any]) -> list[float | None]:
    result = []
    for value in values:
        if value is None:
            result.append(None)
            continue
        number = float(value)
        if not math.isfinite(number) or number < 0:
            raise ValueError("market outcomes must be finite and nonnegative")
        result.append(math.log1p(number))
    return result


def seasonal_residual(values: Sequence[Any], hours: Sequence[datetime]) -> tuple[list[float | None], int]:
    if len(values) != len(hours):
        raise ValueError("values and hours differ in length")
    transformed = log1p_values(values)
    groups: dict[int, list[float]] = {i: [] for i in range(168)}
    for value, hour in zip(transformed, hours):
        if value is not None:
            groups[hour_of_week(hour)].append(value)
    if any(not groups[i] for i in range(168)):
        raise ValueError("canonical sample does not cover all 168 hour-of-week groups")
    medians = {key: statistics.median(group) for key, group in groups.items()}
    return [None if value is None else value - medians[hour_of_week(hour)]
            for value, hour in zip(transformed, hours)], sum(bool(v) for v in groups.values())


def delta_log1p(values: Sequence[Any]) -> list[float | None]:
    transformed = log1p_values(values)
    return [None if i == 0 or value is None or transformed[i - 1] is None
            else value - transformed[i - 1] for i, value in enumerate(transformed)]


def pair_at_lag(driver: Sequence[Any], outcome: Sequence[Any], lag_hours: int) -> tuple[list[Any], list[Any]]:
    if len(driver) != len(outcome) or lag_hours < 0:
        raise ValueError("driver/outcome lengths or lag are invalid")
    xs, ys = [], []
    for t, y in enumerate(outcome):
        source = t - lag_hours
        if source >= 0:
            xs.append(driver[source])
            ys.append(y)
    return xs, ys


def _valid_pair_count(x: Sequence[Any], y: Sequence[Any]) -> int:
    return sum(_finite(a) and _finite(b) for a, b in zip(x, y))


def block_stability(driver: Sequence[Any], outcome: Sequence[Any], lag: int) -> dict[str, Any]:
    coefficients: list[float] = []
    for block in range(BLOCK_COUNT):
        start, end = block * BLOCK_SIZE, (block + 1) * BLOCK_SIZE
        # Pair by global canonical positions, then retain outcomes in this block.
        xs, ys = [], []
        for t in range(start, end):
            source = t - lag
            if source >= 0:
                xs.append(driver[source])
                ys.append(outcome[t])
        if _valid_pair_count(xs, ys) >= 20:
            coefficient = spearman(xs, ys)
            if coefficient is not None:
                coefficients.append(coefficient)
    return {
        "block_valid_count": len(coefficients),
        "block_spearman_median": statistics.median(coefficients) if coefficients else None,
        "block_spearman_min": min(coefficients) if coefficients else None,
        "block_spearman_max": max(coefficients) if coefficients else None,
        "block_positive_count": sum(v > 0 for v in coefficients),
        "block_negative_count": sum(v < 0 for v in coefficients),
        "block_zero_count": sum(v == 0 for v in coefficients),
    }


def build_drivers(rows: Sequence[Mapping[str, Any]]) -> dict[str, list[float | None]]:
    prices = [row["gun_price_return_1h"] for row in rows]
    imbalance = []
    for row in rows:
        total = row["flow_count_total"]
        value = row["flow_count_imbalance"]
        imbalance.append(None if total is None or value is None or float(total) <= 0
                         else float(value) / float(total))
    return {"gun_price_return_1h": prices, "flow_imbalance_share": imbalance}


def build_relationship_matrix(rows: Sequence[Mapping[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    hours = [row["hour_start"] for row in rows]
    result: list[dict[str, Any]] = []
    coverage: dict[str, Any] = {}
    for outcome_name in OUTCOMES:
        values = [row[outcome_name] for row in rows]
        seasonal, covered = seasonal_residual(values, hours)
        coverage[outcome_name] = covered
        forms = {OUTCOME_FORMS[0]: seasonal, OUTCOME_FORMS[1]: delta_log1p(values)}
        for form in OUTCOME_FORMS:
            outcome_values = forms[form]
            for driver_name in DRIVERS:
                driver = build_drivers(rows)[driver_name]
                for lag in LAGS:
                    x, y = pair_at_lag(driver, outcome_values, lag)
                    valid_n = _valid_pair_count(x, y)
                    record = {
                        "driver": driver_name, "outcome": outcome_name,
                        "outcome_form": form, "lag_hours": lag, "n": valid_n,
                        "pearson_r": pearson(x, y), "spearman_rho": spearman(x, y),
                    }
                    record.update(block_stability(driver, outcome_values, lag))
                    result.append(record)
    result.sort(key=lambda r: (r["driver"], r["outcome"], r["outcome_form"], r["lag_hours"]))
    if len(result) != 48:
        raise RuntimeError("relationship matrix is not the preregistered 48 cells")
    return result, coverage


def decluster_candidates(candidates: Sequence[int], returns: Sequence[float | None], *, gap_hours: int = 24) -> list[int]:
    ordered = sorted(candidates)
    clusters: list[list[int]] = []
    for index in ordered:
        if not clusters or index - clusters[-1][-1] > gap_hours:
            clusters.append([index])
        else:
            clusters[-1].append(index)
    return [min(cluster, key=lambda i: (-abs(float(returns[i])), i)) for cluster in clusters]


def eligible_events(candidates: Sequence[int], length: int, *, pre: int = 1, post: int = 24) -> list[int]:
    return [i for i in candidates if i - pre >= 0 and i + post < length]


def event_responses(rows: Sequence[Mapping[str, Any]], events: Sequence[int]) -> dict[tuple[int, str], list[float]]:
    responses: dict[tuple[int, str], list[float]] = {(h, o): [] for h in EVENT_HORIZONS for o in OUTCOMES}
    for event in events:
        for outcome in OUTCOMES:
            baseline_value = float(rows[event - 1][outcome])
            baseline = math.log1p(baseline_value)
            for horizon in EVENT_HORIZONS:
                target = float(rows[event + horizon][outcome])
                responses[(horizon, outcome)].append(math.log1p(target) - baseline)
    return responses


def bootstrap_median_interval(values: Sequence[float], seed: int, *, replicates: int = BOOTSTRAP_REPLICATES) -> tuple[float | None, float | None]:
    if not values:
        return None, None
    rng = random.Random(seed)
    n = len(values)
    medians = [statistics.median(rng.choices(values, k=n)) for _ in range(replicates)]
    return deterministic_quantile(medians, 0.025), deterministic_quantile(medians, 0.975)


def build_event_summary(rows: Sequence[Mapping[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    returns = [row["gun_price_return_1h"] for row in rows]
    valid_returns = [float(value) for value in returns if _finite(value)]
    q05, q95 = deterministic_quantile(valid_returns, 0.05), deterministic_quantile(valid_returns, 0.95)
    raw = {
        "positive": [i for i, value in enumerate(returns) if _finite(value) and float(value) >= q95],
        "negative": [i for i, value in enumerate(returns) if _finite(value) and float(value) <= q05],
    }
    selected: dict[str, list[int]] = {}
    declustered: dict[str, list[int]] = {}
    for direction in ("positive", "negative"):
        declustered[direction] = decluster_candidates(raw[direction], returns)
        selected[direction] = eligible_events(declustered[direction], len(rows))
    summary: list[dict[str, Any]] = []
    direction_index = {"positive": 0, "negative": 1}
    outcome_index = {name: i for i, name in enumerate(OUTCOMES)}
    horizon_index = {h: i for i, h in enumerate(EVENT_HORIZONS)}
    thresholds = {"positive": q95, "negative": q05}
    for direction in ("positive", "negative"):
        responses = event_responses(rows, selected[direction])
        for outcome in OUTCOMES:
            for horizon in EVENT_HORIZONS:
                values = responses[(horizon, outcome)]
                n = len(values)
                med = statistics.median(values) if values else None
                seed = (BOOTSTRAP_BASE_SEED + direction_index[direction] * 100
                        + outcome_index[outcome] * 10 + horizon_index[horizon])
                ci_low, ci_high = bootstrap_median_interval(values, seed)
                summary.append({
                    "direction": direction, "outcome": outcome, "horizon_hours": horizon,
                    "event_count": n, "threshold_return": thresholds[direction],
                    "mean_response": sum(values) / n if n else None, "median_response": med,
                    "q25": deterministic_quantile(values, 0.25) if values else None,
                    "q75": deterministic_quantile(values, 0.75) if values else None,
                    "bootstrap_median_ci_low": ci_low, "bootstrap_median_ci_high": ci_high,
                    "low_event_count": "YES" if n < 20 else "NO",
                })
    summary.sort(key=lambda r: (r["direction"], r["outcome"], r["horizon_hours"]))
    return summary, {
        "q05": q05, "q95": q95,
        "positive_candidate_count": len(raw["positive"]),
        "negative_candidate_count": len(raw["negative"]),
        "positive_declustered_event_count": len(declustered["positive"]),
        "negative_declustered_event_count": len(declustered["negative"]),
        "positive_eligible_event_count": len(selected["positive"]),
        "negative_eligible_event_count": len(selected["negative"]),
    }


def _normalize(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("non-finite artifact value")
        return format(value, ".17g")
    if isinstance(value, (int, str, bool)):
        return value
    raise TypeError(f"unsupported artifact value type: {type(value).__name__}")


def csv_bytes(rows: Sequence[Mapping[str, Any]], fields: Sequence[str]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n", extrasaction="raise")
    writer.writeheader()
    for row in rows:
        writer.writerow({key: "" if row.get(key) is None else _normalize(row.get(key)) for key in fields})
    return stream.getvalue().encode("utf-8")


def logical_rows_digest(rows: Sequence[Mapping[str, Any]], fields: Sequence[str]) -> str:
    payload = [[_normalize(row.get(field)) for field in fields] for row in rows]
    return hashlib.sha256(json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("utf-8")).hexdigest()


def summary_digest(summary: Mapping[str, Any]) -> str:
    payload = {key: value for key, value in summary.items() if key != "analysis_summary_digest"}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_snapshot(rows: Sequence[Mapping[str, Any]]) -> str:
    if len(rows) != CANONICAL_HOURS:
        raise ValueError("analysis snapshot row count mismatch")
    actual = [row["hour_start"].astimezone(timezone.utc) for row in rows]
    if actual != list(utc_hour_spine()):
        raise ValueError("analysis snapshot UTC identities mismatch")
    digest = content_digest(rows, ALIGNED_COLUMNS)
    if digest != EXPECTED_SNAPSHOT_DIGEST:
        raise ValueError("analysis snapshot digest mismatch")
    return digest


def analyze_rows(rows: Sequence[Mapping[str, Any]], snapshot_digest: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    if len(rows) != CANONICAL_HOURS or snapshot_digest != EXPECTED_SNAPSHOT_DIGEST:
        raise ValueError("snapshot contract mismatch")
    matrix, group_coverage = build_relationship_matrix(rows)
    events, event_meta = build_event_summary(rows)
    matrix_digest = logical_rows_digest(matrix, RELATIONSHIP_FIELDS)
    event_digest = logical_rows_digest(events, EVENT_FIELDS)
    hours = [row["hour_start"].astimezone(timezone.utc) for row in rows]
    summary = {
        "methodology_version": METHODOLOGY_VERSION,
        "snapshot_row_count": len(rows), "snapshot_digest": snapshot_digest,
        "canonical_start": hours[0].isoformat().replace("+00:00", "Z"),
        "canonical_end": hours[-1].isoformat().replace("+00:00", "Z"),
        "drivers": list(DRIVERS), "outcomes": list(OUTCOMES), "outcome_forms": list(OUTCOME_FORMS),
        "fixed_lags": list(LAGS), "hour_of_week_group_coverage": group_coverage,
        "block_count": BLOCK_COUNT, "block_size": BLOCK_SIZE,
        "event_quantiles": {"negative": 0.05, "positive": 0.95},
        "event_threshold_returns": {"q05": event_meta["q05"], "q95": event_meta["q95"]},
        "event_decluster_hours": 24, "event_horizons": list(EVENT_HORIZONS),
        "bootstrap_replicates": BOOTSTRAP_REPLICATES, "bootstrap_base_seed": BOOTSTRAP_BASE_SEED,
        "positive_candidate_count": event_meta["positive_candidate_count"],
        "negative_candidate_count": event_meta["negative_candidate_count"],
        "positive_declustered_event_count": event_meta["positive_declustered_event_count"],
        "negative_declustered_event_count": event_meta["negative_declustered_event_count"],
        "positive_eligible_event_count": event_meta["positive_eligible_event_count"],
        "negative_eligible_event_count": event_meta["negative_eligible_event_count"],
        "relationship_matrix_digest": matrix_digest, "event_summary_digest": event_digest,
    }
    summary["analysis_summary_digest"] = summary_digest(summary)
    return matrix, events, summary


def _resource() -> dict[str, Any]:
    try:
        import psutil
        vm, swap = psutil.virtual_memory(), psutil.swap_memory()
        return {"cpu_percent": psutil.cpu_percent(interval=0.1), "available_ram_bytes": vm.available,
                "committed_bytes": swap.used, "commit_limit_bytes": swap.total,
                "free_commit_bytes": max(0, swap.total - swap.used)}
    except Exception:
        return {"status": "unavailable"}


def run_readonly(output_dir: str = "DEV/analysis") -> dict[str, Any]:
    from pathlib import Path
    observations: dict[str, Any] = {"before_staging_read": _resource()}
    connection = staging_readonly_connection()
    try:
        db, read_only = connection.execute("SELECT current_database(), current_setting('transaction_read_only')").fetchone()
        if db != "server_otg_staging" or read_only != "on":
            raise RuntimeError("analysis requires a read-only server_otg_staging connection")
        rows = read_analytics_rows(connection, "otg_nansen_hourly", ALIGNED_COLUMNS)
    finally:
        connection.rollback()
        connection.close()
    observations["after_snapshot_read"] = _resource()
    digest = validate_snapshot(rows)
    matrix, events, summary = analyze_rows(rows, digest)
    observations["after_relationship_matrix"] = _resource()
    observations["after_event_analysis"] = _resource()
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    matrix_path, event_path, summary_path = (out / "034_relationship_matrix.csv", out / "034_price_shock_event_summary.csv", out / "034_analysis_summary.json")
    matrix_path.write_bytes(csv_bytes(matrix, RELATIONSHIP_FIELDS))
    event_path.write_bytes(csv_bytes(events, EVENT_FIELDS))
    summary_path.write_text(json.dumps(summary, sort_keys=True, indent=2, ensure_ascii=True, allow_nan=False) + "\n", encoding="utf-8")
    observations["after_artifact_serialization"] = _resource()
    return {"rows": rows, "matrix": matrix, "events": events, "summary": summary, "resources": observations}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run preregistered descriptive analysis on the staging snapshot.")
    parser.add_argument("--execute-readonly", action="store_true", required=True)
    parser.add_argument("--output-dir", default="DEV/analysis")
    args = parser.parse_args(argv)
    result = run_readonly(args.output_dir)
    for key, value in result["summary"].items():
        print(f"{key.upper()}={value}")
    for key, value in result["resources"].items():
        print(f"RESOURCE_{key.upper()}={json.dumps(value, sort_keys=True)}")
    print("STAGING_CONNECTION_MODE=READ_ONLY")
    print("NANSEN_API_CALLS_TASK034=0")
    print("ONCHAIN_RPC_CALLS_TASK034=0")
    print("PRODUCTION_CONNECTIONS_TASK034=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
