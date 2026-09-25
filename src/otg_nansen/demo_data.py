"""Digest-validated access to committed Task 034 aggregate artifacts."""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any

from .relationship_analysis import (
    EVENT_FIELDS,
    RELATIONSHIP_FIELDS,
    logical_rows_digest,
    summary_digest,
)

EXPECTED_SNAPSHOT_ROWS = 12_336
EXPECTED_SNAPSHOT_DIGEST = "9ac2109500aea84160555928d297b7efdcd551e23f3259bee5482a1ae5ed19f8"
EXPECTED_RELATIONSHIP_DIGEST = "81004c088b886eee4289151803a18c27d8ee4a75132f178ce6a8be584b1831ef"
EXPECTED_EVENT_DIGEST = "5f3e89ed359275c65977acaf02ad45d14b2a8329fcc4902c8e3b590396bff772"
EXPECTED_SUMMARY_DIGEST = "e7a16b3b2a84c15d20b5ce019e7463357b06513b60ed7e48754113df2e844e74"

_RELATIONSHIP_INTS = {
    "lag_hours", "n", "block_valid_count", "block_positive_count",
    "block_negative_count", "block_zero_count",
}
_EVENT_INTS = {"horizon_hours", "event_count"}


class HistoricalArtifactError(ValueError):
    """A committed analysis artifact failed its immutable content contract."""


def _parse_csv(path: Path, fields: tuple[str, ...], integer_fields: set[str]) -> list[dict[str, Any]]:
    try:
        with path.open("r", encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream)
            if tuple(reader.fieldnames or ()) != fields:
                raise HistoricalArtifactError("historical artifact columns do not match the committed contract")
            rows: list[dict[str, Any]] = []
            for raw in reader:
                row: dict[str, Any] = {}
                for key in fields:
                    value = raw[key]
                    if value == "":
                        row[key] = None
                    elif key in integer_fields:
                        row[key] = int(value)
                    elif key in fields and key not in {"driver", "outcome", "outcome_form", "direction", "low_event_count"}:
                        row[key] = float(value)
                        if not math.isfinite(row[key]):
                            raise HistoricalArtifactError("historical artifact contains a non-finite value")
                    else:
                        row[key] = value
                rows.append(row)
            return rows
    except (OSError, UnicodeError, csv.Error, ValueError, TypeError) as exc:
        if isinstance(exc, HistoricalArtifactError):
            raise
        raise HistoricalArtifactError("historical artifact could not be read or parsed") from exc


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_historical_artifacts(root: Path | None = None) -> dict[str, Any]:
    """Load and verify Task 034 artifacts; fail closed on any change."""
    base = (root or _repo_root()) / "DEV" / "analysis"
    try:
        summary = json.loads((base / "034_analysis_summary.json").read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise HistoricalArtifactError("historical summary artifact is unavailable or invalid") from exc

    if not isinstance(summary, dict):
        raise HistoricalArtifactError("historical summary artifact has an invalid shape")
    if summary.get("analysis_summary_digest") != EXPECTED_SUMMARY_DIGEST or summary_digest(summary) != EXPECTED_SUMMARY_DIGEST:
        raise HistoricalArtifactError("historical summary digest mismatch")
    if summary.get("snapshot_row_count") != EXPECTED_SNAPSHOT_ROWS or summary.get("snapshot_digest") != EXPECTED_SNAPSHOT_DIGEST:
        raise HistoricalArtifactError("historical source snapshot contract mismatch")
    if summary.get("relationship_matrix_digest") != EXPECTED_RELATIONSHIP_DIGEST:
        raise HistoricalArtifactError("historical relationship digest metadata mismatch")
    if summary.get("event_summary_digest") != EXPECTED_EVENT_DIGEST:
        raise HistoricalArtifactError("historical event digest metadata mismatch")

    relationships = _parse_csv(base / "034_relationship_matrix.csv", RELATIONSHIP_FIELDS, _RELATIONSHIP_INTS)
    events = _parse_csv(base / "034_price_shock_event_summary.csv", EVENT_FIELDS, _EVENT_INTS)
    if len(relationships) != 48 or logical_rows_digest(relationships, RELATIONSHIP_FIELDS) != EXPECTED_RELATIONSHIP_DIGEST:
        raise HistoricalArtifactError("historical relationship matrix failed validation")
    if len(events) != 24 or logical_rows_digest(events, EVENT_FIELDS) != EXPECTED_EVENT_DIGEST:
        raise HistoricalArtifactError("historical event summary failed validation")

    q05 = summary.get("event_threshold_returns", {}).get("q05")
    q95 = summary.get("event_threshold_returns", {}).get("q95")
    if not isinstance(q05, (int, float)) or not isinstance(q95, (int, float)):
        raise HistoricalArtifactError("historical event thresholds are unavailable")
    if not math.isfinite(q05) or not math.isfinite(q95) or q05 >= q95:
        raise HistoricalArtifactError("historical event thresholds are invalid")

    relationship_view = [
        {
            "outcome": row["outcome"],
            "lag_hours": row["lag_hours"],
            "spearman_rho": row["spearman_rho"],
        }
        for row in relationships
        if row["driver"] == "gun_price_return_1h"
        and row["outcome_form"] == "hour_of_week_seasonal_residual"
    ]
    if len(relationship_view) != 12:
        raise HistoricalArtifactError("historical primary relationship panel is incomplete")
    return {
        "snapshot_row_count": EXPECTED_SNAPSHOT_ROWS,
        "snapshot_digest": EXPECTED_SNAPSHOT_DIGEST,
        "relationship_matrix_digest": EXPECTED_RELATIONSHIP_DIGEST,
        "event_summary_digest": EXPECTED_EVENT_DIGEST,
        "analysis_summary_digest": EXPECTED_SUMMARY_DIGEST,
        "canonical_start": summary["canonical_start"],
        "canonical_end": summary["canonical_end"],
        "q05_historical_threshold": float(q05),
        "q95_historical_threshold": float(q95),
        "relationship_rows": relationship_view,
        "event_rows": events,
    }
