"""Deterministic, resumable hourly flow backfill planning primitives.

This module does not call Nansen or mutate a database.  Its optional staging
inspector requires an explicitly read-only connection.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from typing import Any, Callable, Iterable, Mapping, Sequence

from .errors import IngestionWindowError
from .identity import canonical_chain_address, canonical_flow_scope
from .models import NormalizedFlowRecord
from .source_warnings import NON_EXCHANGE_BREAKDOWN_UNAVAILABLE

HOUR = timedelta(hours=1)
MAX_HOURLY_REQUEST_SPAN = timedelta(days=7) - timedelta(seconds=1)
DEFAULT_MAX_DESIRED_BUCKETS_PER_REQUEST = 167
_SUCCESS_WARNING_CATEGORIES = frozenset({NON_EXCHANGE_BREAKDOWN_UNAVAILABLE})


class BackfillPlanningError(IngestionWindowError):
    """Raised when a requested historical plan cannot satisfy its invariants."""


class BackfillExecutionError(BackfillPlanningError):
    """Raised when progress is ambiguous or an executor budget is invalid."""


class LiveCallBudgetExceeded(BackfillExecutionError):
    """Raised before the executor starts a unit that exceeds its call budget."""


@dataclass(frozen=True)
class HourlyFlowBackfillUnit:
    index: int
    unit_id: str
    chain: str
    token_address: str
    flow_label: str
    coverage_start: datetime
    coverage_end: datetime
    request_start: datetime
    request_end: datetime
    desired_bucket_count: int

    @property
    def request_duration(self) -> timedelta:
        return self.request_end - self.request_start


@dataclass(frozen=True)
class HourlyFlowBackfillPlan:
    chain: str
    token_address: str
    flow_label: str
    target_start: datetime
    target_end: datetime
    units: tuple[HourlyFlowBackfillUnit, ...]
    desired_bucket_count: int
    max_live_calls: int
    max_desired_buckets_per_request: int


@dataclass(frozen=True)
class UnitCoverageValidation:
    unit_id: str
    expected_bucket_starts: tuple[datetime, ...]
    observed_desired_bucket_starts: tuple[datetime, ...]
    missing_desired_bucket_starts: tuple[datetime, ...]
    source_absent_bucket_starts: tuple[datetime, ...]
    source_absence_classification: str | None
    unexpected_bucket_starts_inside_responsibility: tuple[datetime, ...]
    unexpected_bucket_starts_outside_responsibility: tuple[datetime, ...]
    hourly_bucket_count: int
    non_hourly_duration_count: int
    request_boundary_bucket_observed: bool
    request_boundary_gap: bool
    request_boundary_classification: str | None
    first_desired_bucket_internal: bool


@dataclass(frozen=True)
class IngestionAuditEvidence:
    run_id: str
    status: str
    chain: str
    endpoint: str
    token_address: str
    flow_label: str
    window_start: datetime | None
    window_end: datetime | None
    source_warnings: Any


@dataclass(frozen=True)
class PlanProgress:
    statuses: Mapping[str, str]
    complete: int
    pending: int
    ambiguous: int


@dataclass(frozen=True)
class BatchExecutionResult:
    attempted_unit_ids: tuple[str, ...]
    completed_unit_ids: tuple[str, ...]
    skipped_complete_unit_ids: tuple[str, ...]
    live_calls_used: int
    units_limit_reached: bool


def _as_utc(value: datetime, field: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise BackfillPlanningError(f"{field} must be timezone-aware")
    return value.astimezone(timezone.utc)


def _hour_aligned(value: datetime) -> bool:
    return value.minute == 0 and value.second == 0 and value.microsecond == 0


def _unit_fingerprint(
    chain: str,
    token_address: str,
    flow_label: str,
    coverage_start: datetime,
    coverage_end: datetime,
    request_start: datetime,
    request_end: datetime,
) -> str:
    identity = {
        "chain": chain,
        "token_address": token_address,
        "flow_label": flow_label,
        "coverage_start": coverage_start.isoformat().replace("+00:00", "Z"),
        "coverage_end": coverage_end.isoformat().replace("+00:00", "Z"),
        "request_start": request_start.isoformat().replace("+00:00", "Z"),
        "request_end": request_end.isoformat().replace("+00:00", "Z"),
    }
    encoded = json.dumps(identity, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return sha256(encoded.encode("utf-8")).hexdigest()


def plan_hourly_flow_backfill(
    target_start: datetime,
    target_end: datetime,
    *,
    chain: str,
    token_address: str,
    flow_label: str,
    max_desired_buckets_per_request: int = DEFAULT_MAX_DESIRED_BUCKETS_PER_REQUEST,
) -> HourlyFlowBackfillPlan:
    """Plan inclusive hourly bucket starts using a one-hour request pre-roll."""
    start = _as_utc(target_start, "target_start")
    end = _as_utc(target_end, "target_end")
    if not _hour_aligned(start):
        raise BackfillPlanningError("target_start must be aligned to an hour")
    if not _hour_aligned(end):
        raise BackfillPlanningError("target_end must be aligned to an hour")
    if end < start:
        raise BackfillPlanningError("target_end must not be before target_start")
    if not isinstance(max_desired_buckets_per_request, int) or isinstance(max_desired_buckets_per_request, bool) or max_desired_buckets_per_request <= 0:
        raise BackfillPlanningError("max_desired_buckets_per_request must be a positive integer")
    if not isinstance(chain, str) or not chain.strip():
        raise BackfillPlanningError("chain must be non-empty")
    try:
        canonical_token = canonical_chain_address(chain, token_address)
        canonical_label = canonical_flow_scope(flow_label)
    except ValueError as exc:
        raise BackfillPlanningError("chain, token_address, or flow_label is invalid") from exc
    if max_desired_buckets_per_request * HOUR + timedelta(seconds=3599) > MAX_HOURLY_REQUEST_SPAN:
        raise BackfillPlanningError("requested unit size can exceed the seven-day hourly request limit")

    desired_count = int((end - start) / HOUR) + 1
    units: list[HourlyFlowBackfillUnit] = []
    next_start = start
    index = 1
    while next_start <= end:
        count = min(max_desired_buckets_per_request, int((end - next_start) / HOUR) + 1)
        coverage_start = next_start
        coverage_end = coverage_start + (count - 1) * HOUR
        request_start = coverage_start - HOUR
        request_end = coverage_end + timedelta(minutes=59, seconds=59)
        duration = request_end - request_start
        if duration > MAX_HOURLY_REQUEST_SPAN:
            raise BackfillPlanningError("planned request duration exceeds the seven-day hourly limit")
        unit_id = _unit_fingerprint(
            chain.strip().lower(), canonical_token, canonical_label,
            coverage_start, coverage_end, request_start, request_end,
        )
        units.append(HourlyFlowBackfillUnit(
            index=index,
            unit_id=unit_id,
            chain=chain.strip().lower(),
            token_address=canonical_token,
            flow_label=canonical_label,
            coverage_start=coverage_start,
            coverage_end=coverage_end,
            request_start=request_start,
            request_end=request_end,
            desired_bucket_count=count,
        ))
        next_start = coverage_end + HOUR
        index += 1
    return HourlyFlowBackfillPlan(
        chain=chain.strip().lower(),
        token_address=canonical_token,
        flow_label=canonical_label,
        target_start=start,
        target_end=end,
        units=tuple(units),
        desired_bucket_count=desired_count,
        max_live_calls=len(units),
        max_desired_buckets_per_request=max_desired_buckets_per_request,
    )


def validate_unit_coverage(
    unit: HourlyFlowBackfillUnit,
    records: Iterable[NormalizedFlowRecord],
) -> UnitCoverageValidation:
    """Describe structural coverage; absent source buckets are not failures."""
    expected = tuple(unit.coverage_start + index * HOUR for index in range(unit.desired_bucket_count))
    if unit.coverage_start != unit.request_start + HOUR:
        raise BackfillPlanningError("unit first desired bucket must be internal by one hour")
    starts: set[datetime] = set()
    hourly_starts: set[datetime] = set()
    non_hourly_inside: set[datetime] = set()
    non_hourly_count = 0
    hourly_count = 0
    for record in records:
        record_start = _as_utc(record.date, "record.date")
        starts.add(record_start)
        if record.bucket_end is None:
            non_hourly_count += 1
            if unit.coverage_start <= record_start <= unit.coverage_end:
                non_hourly_inside.add(record_start)
            continue
        record_end = _as_utc(record.bucket_end, "record.bucket_end")
        if record_end - record_start == HOUR:
            hourly_count += 1
            hourly_starts.add(record_start)
        else:
            non_hourly_count += 1
            if unit.coverage_start <= record_start <= unit.coverage_end:
                non_hourly_inside.add(record_start)
    expected_set = set(expected)
    observed_desired = expected_set & hourly_starts
    missing = expected_set - observed_desired
    unexpected_inside = non_hourly_inside
    unexpected_outside = {value for value in starts if value < unit.coverage_start or value > unit.coverage_end}
    boundary_observed = unit.request_start in hourly_starts
    return UnitCoverageValidation(
        unit_id=unit.unit_id,
        expected_bucket_starts=expected,
        observed_desired_bucket_starts=tuple(sorted(observed_desired)),
        missing_desired_bucket_starts=tuple(sorted(missing)),
        source_absent_bucket_starts=tuple(sorted(missing)),
        source_absence_classification="SOURCE_ABSENT_BUCKET" if missing else None,
        unexpected_bucket_starts_inside_responsibility=tuple(sorted(unexpected_inside)),
        unexpected_bucket_starts_outside_responsibility=tuple(sorted(unexpected_outside)),
        hourly_bucket_count=hourly_count,
        non_hourly_duration_count=non_hourly_count,
        request_boundary_bucket_observed=boundary_observed,
        request_boundary_gap=not boundary_observed,
        request_boundary_classification="REQUEST_BOUNDARY_GAP" if not boundary_observed else None,
        first_desired_bucket_internal=unit.coverage_start == unit.request_start + HOUR,
    )


def _valid_success_warning_summary(value: Any) -> bool:
    if not isinstance(value, list):
        return False
    for summary in value:
        if not isinstance(summary, dict) or set(summary) != {"page", "warning_count", "categories"}:
            return False
        page = summary["page"]
        count = summary["warning_count"]
        categories = summary["categories"]
        if not isinstance(page, int) or isinstance(page, bool) or page < 1:
            return False
        if not isinstance(count, int) or isinstance(count, bool) or count < 1:
            return False
        if not isinstance(categories, list) or not categories or any(category not in _SUCCESS_WARNING_CATEGORIES for category in categories):
            return False
    return True


def _audit_value(row: IngestionAuditEvidence | Mapping[str, Any], name: str) -> Any:
    return getattr(row, name) if isinstance(row, IngestionAuditEvidence) else row.get(name)


def _same_instant(left: Any, right: datetime) -> bool:
    if not isinstance(left, datetime) or left.tzinfo is None or left.utcoffset() is None:
        return False
    return left.astimezone(timezone.utc) == right


def classify_unit_progress(
    unit: HourlyFlowBackfillUnit,
    audits: Sequence[IngestionAuditEvidence | Mapping[str, Any]],
) -> str:
    """Classify exact-window audit evidence as COMPLETE, PENDING, or AMBIGUOUS."""
    exact = []
    for audit in audits:
        try:
            token = canonical_chain_address(str(_audit_value(audit, "chain")), str(_audit_value(audit, "token_address")))
            label = canonical_flow_scope(str(_audit_value(audit, "flow_label")))
        except ValueError:
            continue
        if (
            str(_audit_value(audit, "chain")).strip().lower() == unit.chain
            and str(_audit_value(audit, "endpoint")) == "flows"
            and token == unit.token_address
            and label == unit.flow_label
            and _same_instant(_audit_value(audit, "window_start"), unit.request_start)
            and _same_instant(_audit_value(audit, "window_end"), unit.request_end)
        ):
            exact.append(audit)
    for audit in exact:
        if str(_audit_value(audit, "status")) == "success" and _valid_success_warning_summary(_audit_value(audit, "source_warnings")):
            return "COMPLETE"
    if any(str(_audit_value(audit, "status")) in {"success", "running", "partial"} for audit in exact):
        return "AMBIGUOUS"
    return "PENDING"


def classify_plan_progress(
    plan: HourlyFlowBackfillPlan,
    audits: Sequence[IngestionAuditEvidence | Mapping[str, Any]],
) -> PlanProgress:
    statuses = {unit.unit_id: classify_unit_progress(unit, audits) for unit in plan.units}
    values = tuple(statuses.values())
    return PlanProgress(
        statuses=statuses,
        complete=values.count("COMPLETE"),
        pending=values.count("PENDING"),
        ambiguous=values.count("AMBIGUOUS"),
    )


def inspect_plan_progress(connection: Any, plan: HourlyFlowBackfillPlan) -> PlanProgress:
    """Read exact-stream audit evidence from a connection forced read-only by caller."""
    read_only = connection.execute("SHOW transaction_read_only").fetchone()[0]
    if read_only != "on":
        raise BackfillPlanningError("plan progress inspection requires a read-only transaction")
    rows = connection.execute(
        """SELECT run_id::text, status, chain, endpoint, token_address, flow_label,
                  window_start, window_end, source_warnings
           FROM nansen.ingestion_runs
           WHERE chain = %s AND endpoint = 'flows' AND token_address = %s AND flow_label = %s
           ORDER BY started_at, run_id""",
        (plan.chain, plan.token_address, plan.flow_label),
    ).fetchall()
    audits = [IngestionAuditEvidence(*row) for row in rows]
    return classify_plan_progress(plan, audits)


def execute_pending_units(
    plan: HourlyFlowBackfillPlan,
    progress: Mapping[str, str],
    *,
    max_units: int,
    max_live_calls: int,
    execute_unit: Callable[[HourlyFlowBackfillUnit, int], int],
    max_calls_per_unit: int = 1,
) -> BatchExecutionResult:
    """Sequential bounded executor shell; callback receives its call ceiling."""
    for value, name in ((max_units, "max_units"), (max_live_calls, "max_live_calls"), (max_calls_per_unit, "max_calls_per_unit")):
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            raise BackfillExecutionError(f"{name} must be a positive integer")
    statuses = [progress.get(unit.unit_id, "PENDING") for unit in plan.units]
    if any(status not in {"COMPLETE", "PENDING", "AMBIGUOUS"} for status in statuses):
        raise BackfillExecutionError("progress contains an unsupported unit status")
    if "AMBIGUOUS" in statuses:
        raise BackfillExecutionError("ambiguous unit audit evidence blocks execution")
    ordered = sorted(zip(plan.units, statuses), key=lambda item: item[0].coverage_start)
    skipped = tuple(unit.unit_id for unit, status in ordered if status == "COMPLETE")
    attempted: list[str] = []
    completed: list[str] = []
    calls_used = 0
    for unit, status in ordered:
        if status == "COMPLETE":
            continue
        if len(attempted) >= max_units:
            break
        available = max_live_calls - calls_used
        if available < max_calls_per_unit:
            raise LiveCallBudgetExceeded("live-call budget would be exceeded before the next unit")
        attempted.append(unit.unit_id)
        unit_calls = execute_unit(unit, max_calls_per_unit)
        if not isinstance(unit_calls, int) or isinstance(unit_calls, bool) or unit_calls < 0 or unit_calls > max_calls_per_unit:
            raise BackfillExecutionError("unit executor exceeded its assigned live-call ceiling")
        calls_used += unit_calls
        completed.append(unit.unit_id)
    remaining_pending = any(
        status == "PENDING" and unit.unit_id not in completed
        for unit, status in ordered
    )
    return BatchExecutionResult(
        attempted_unit_ids=tuple(attempted),
        completed_unit_ids=tuple(completed),
        skipped_complete_unit_ids=skipped,
        live_calls_used=calls_used,
        units_limit_reached=len(attempted) >= max_units and remaining_pending,
    )
