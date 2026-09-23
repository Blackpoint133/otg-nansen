from datetime import datetime, timedelta, timezone

import pytest

from otg_nansen.backfill import (
    BackfillExecutionError,
    BackfillPlanningError,
    HourlyFlowBackfillUnit,
    LiveCallBudgetExceeded,
    classify_plan_progress,
    classify_unit_progress,
    execute_pending_units,
    plan_hourly_flow_backfill,
    validate_unit_coverage,
)
from otg_nansen.backfill_plan import main
from otg_nansen.models import NormalizedFlowRecord


TOKEN = "0x0000000000000000000000000000000000000001"
UTC = timezone.utc
CANONICAL_START = datetime(2025, 4, 25, 0, tzinfo=UTC)
CANONICAL_END = datetime(2026, 9, 20, 23, tzinfo=UTC)


def plan(start=CANONICAL_START, end=CANONICAL_END, **kwargs):
    return plan_hourly_flow_backfill(
        start, end, chain="avalanche", token_address=TOKEN,
        flow_label="smart_money", **kwargs,
    )


def flow(date, *, duration=timedelta(hours=1), complete=True):
    return NormalizedFlowRecord(
        chain="avalanche", token_address=TOKEN, date=date,
        price_usd=1, token_amount=1, value_usd=1, holders_count=1,
        total_inflows_count=1, total_outflows_count=1,
        flow_label="smart_money", bucket_end=date + duration, is_complete=complete,
    )


def test_canonical_full_plan_has_exact_units_and_bounds():
    result = plan()
    assert result.desired_bucket_count == 12_336
    assert len(result.units) == 74 and result.max_live_calls == 74
    assert [unit.desired_bucket_count for unit in result.units[:73]] == [167] * 73
    assert result.units[-1].desired_bucket_count == 145
    planned_starts = [unit.coverage_start + index * timedelta(hours=1) for unit in result.units for index in range(unit.desired_bucket_count)]
    expected_starts = [CANONICAL_START + index * timedelta(hours=1) for index in range(result.desired_bucket_count)]
    assert planned_starts == expected_starts
    assert len(set(planned_starts)) == 12_336
    first, second, final = result.units[0], result.units[1], result.units[-1]
    assert (first.coverage_start, first.coverage_end) == (
        datetime(2025, 4, 25, 0, tzinfo=UTC), datetime(2025, 5, 1, 22, tzinfo=UTC)
    )
    assert (first.request_start, first.request_end) == (
        datetime(2025, 4, 24, 23, tzinfo=UTC), datetime(2025, 5, 1, 22, 59, 59, tzinfo=UTC)
    )
    assert first.desired_bucket_count == 167
    assert (second.coverage_start, second.coverage_end) == (
        datetime(2025, 5, 1, 23, tzinfo=UTC), datetime(2025, 5, 8, 21, tzinfo=UTC)
    )
    assert (second.request_start, second.request_end) == (
        datetime(2025, 5, 1, 22, tzinfo=UTC), datetime(2025, 5, 8, 21, 59, 59, tzinfo=UTC)
    )
    assert second.desired_bucket_count == 167
    assert (final.coverage_start, final.coverage_end) == (
        datetime(2026, 9, 14, 23, tzinfo=UTC), datetime(2026, 9, 20, 23, tzinfo=UTC)
    )
    assert (final.request_start, final.request_end) == (
        datetime(2026, 9, 14, 22, tzinfo=UTC), datetime(2026, 9, 20, 23, 59, 59, tzinfo=UTC)
    )
    assert final.desired_bucket_count == 145


def test_plan_coverage_is_contiguous_and_requests_overlap_one_bucket():
    units = plan().units
    assert all(next_unit.coverage_start == unit.coverage_end + timedelta(hours=1) for unit, next_unit in zip(units, units[1:]))
    assert all(next_unit.request_start == unit.coverage_end for unit, next_unit in zip(units, units[1:]))
    assert all(((unit.coverage_end + timedelta(hours=1)) - next_unit.request_start).total_seconds() == 3600 for unit, next_unit in zip(units, units[1:]))
    assert all(unit.coverage_start == unit.request_start + timedelta(hours=1) for unit in units)
    assert all(unit.request_duration <= timedelta(days=6, hours=23, minutes=59, seconds=59) for unit in units)
    assert max(unit.request_duration for unit in units) == timedelta(days=6, hours=23, minutes=59, seconds=59)


def test_replanning_is_deterministic_and_boundary_changes_change_unit_id():
    first = plan()
    again = plan()
    assert [(u.unit_id, u.coverage_start, u.coverage_end, u.request_start, u.request_end) for u in first.units] == [
        (u.unit_id, u.coverage_start, u.coverage_end, u.request_start, u.request_end) for u in again.units
    ]
    shifted = plan(CANONICAL_START + timedelta(hours=1), CANONICAL_END)
    assert first.units[0].unit_id != shifted.units[0].unit_id


@pytest.mark.parametrize("start,end,kwargs", [
    (datetime(2025, 4, 25), CANONICAL_END, {}),
    (CANONICAL_START + timedelta(minutes=1), CANONICAL_END, {}),
    (CANONICAL_START, CANONICAL_END + timedelta(seconds=1), {}),
    (CANONICAL_END, CANONICAL_START, {}),
    (CANONICAL_START, CANONICAL_END, {"max_desired_buckets_per_request": 0}),
    (CANONICAL_START, CANONICAL_END, {"max_desired_buckets_per_request": 168}),
])
def test_plan_rejects_invalid_bounds_and_oversized_units(start, end, kwargs):
    with pytest.raises(BackfillPlanningError):
        plan(start, end, **kwargs)


def test_offset_aware_bounds_are_normalized_to_utc():
    offset = timezone(timedelta(hours=-7))
    result = plan(
        datetime(2025, 4, 25, 0, tzinfo=UTC).astimezone(offset),
        datetime(2025, 4, 25, 1, tzinfo=UTC).astimezone(offset),
    )
    assert result.target_start == CANONICAL_START
    assert result.target_end == CANONICAL_START + timedelta(hours=1)


def test_coverage_validator_reports_absent_source_bucket_without_failing():
    unit = plan(CANONICAL_START, CANONICAL_START + timedelta(hours=2)).units[0]
    result = validate_unit_coverage(unit, [flow(unit.request_start), flow(CANONICAL_START), flow(CANONICAL_START + timedelta(hours=2))])
    assert result.first_desired_bucket_internal
    assert result.expected_bucket_starts == tuple(CANONICAL_START + i * timedelta(hours=1) for i in range(3))
    assert result.observed_desired_bucket_starts == (CANONICAL_START, CANONICAL_START + timedelta(hours=2))
    assert result.missing_desired_bucket_starts == (CANONICAL_START + timedelta(hours=1),)
    assert result.source_absent_bucket_starts == result.missing_desired_bucket_starts
    assert result.source_absence_classification == "SOURCE_ABSENT_BUCKET"
    assert not result.request_boundary_gap
    assert result.request_boundary_classification is None


def test_coverage_validator_distinguishes_request_boundary_gap_and_unexpected_rows():
    unit = plan(CANONICAL_START, CANONICAL_START + timedelta(hours=1)).units[0]
    records = [
        flow(CANONICAL_START, duration=timedelta(hours=2)),
        flow(unit.request_start - timedelta(hours=1)),
    ]
    result = validate_unit_coverage(unit, records)
    assert result.request_boundary_gap
    assert result.request_boundary_classification == "REQUEST_BOUNDARY_GAP"
    assert not result.request_boundary_bucket_observed
    assert result.unexpected_bucket_starts_inside_responsibility == (CANONICAL_START,)
    assert result.unexpected_bucket_starts_outside_responsibility == (unit.request_start - timedelta(hours=1),)
    with pytest.raises(BackfillPlanningError):
        invalid = HourlyFlowBackfillUnit(
            **{**unit.__dict__, "coverage_start": unit.request_start}
        )
        validate_unit_coverage(invalid, [])


_UNSET = object()


def audit(unit, *, status="success", warnings=_UNSET, **changes):
    value = {
        "run_id": "synthetic-run",
        "status": status,
        "chain": unit.chain,
        "endpoint": "flows",
        "token_address": unit.token_address,
        "flow_label": unit.flow_label,
        "window_start": unit.request_start,
        "window_end": unit.request_end,
        "source_warnings": [] if warnings is _UNSET else warnings,
    }
    value.update(changes)
    return value


def test_audit_completion_requires_exact_warning_audited_success():
    unit = plan(CANONICAL_START, CANONICAL_START).units[0]
    benign = [{"page": 1, "warning_count": 1, "categories": ["NON_EXCHANGE_BREAKDOWN_UNAVAILABLE"]}]
    assert classify_unit_progress(unit, [audit(unit, status="failed", warnings=benign)]) == "PENDING"
    assert classify_unit_progress(unit, [audit(unit, status="success", warnings=None)]) == "AMBIGUOUS"
    assert classify_unit_progress(unit, [audit(unit, status="success", warnings=[])]) == "COMPLETE"
    assert classify_unit_progress(unit, [audit(unit, status="success", warnings=benign)]) == "COMPLETE"
    assert classify_unit_progress(unit, [audit(unit, status="success", warnings=[], window_end=unit.request_end + timedelta(hours=1))]) == "PENDING"


def test_pre_warning_success_is_ambiguous_but_later_safe_success_completes():
    unit = plan(CANONICAL_START, CANONICAL_START).units[0]
    legacy_success = audit(unit, status="success", source_warnings=None)
    assert classify_unit_progress(unit, [legacy_success]) == "AMBIGUOUS"
    safe_success = audit(unit, status="success", source_warnings=[])
    assert classify_unit_progress(unit, [legacy_success, safe_success, audit(unit, status="failed")]) == "COMPLETE"


def test_successful_audit_with_unknown_warning_summary_is_ambiguous():
    unit = plan(CANONICAL_START, CANONICAL_START).units[0]
    unknown = [{"page": 1, "warning_count": 1, "categories": ["UNKNOWN"]}]
    assert classify_unit_progress(unit, [audit(unit, status="success", warnings=unknown)]) == "AMBIGUOUS"


def test_plan_progress_counts_complete_pending_and_ambiguous():
    units = plan(CANONICAL_START, CANONICAL_START + timedelta(hours=2), max_desired_buckets_per_request=1).units
    evidence = [audit(units[0], status="success", source_warnings=[]), audit(units[1], status="failed")]
    result = classify_plan_progress(plan(CANONICAL_START, CANONICAL_START + timedelta(hours=2), max_desired_buckets_per_request=1), evidence)
    assert (result.complete, result.pending, result.ambiguous) == (1, 2, 0)


def test_executor_stops_after_first_failure():
    units = plan(CANONICAL_START, CANONICAL_START + timedelta(hours=2), max_desired_buckets_per_request=1).units
    called = []

    def execute(unit, call_limit):
        called.append(unit.unit_id)
        assert call_limit == 1
        if unit.index == 2:
            raise RuntimeError("synthetic unit failure")
        return 1

    with pytest.raises(RuntimeError, match="synthetic unit failure"):
        execute_pending_units(
            plan(CANONICAL_START, CANONICAL_START + timedelta(hours=2), max_desired_buckets_per_request=1), {},
            max_units=3, max_live_calls=3, execute_unit=execute,
        )
    assert called == [unit.unit_id for unit in units[:2]]


def test_executor_resumes_after_completed_units_and_honors_max_units():
    result_plan = plan(CANONICAL_START, CANONICAL_START + timedelta(hours=3), max_desired_buckets_per_request=1)
    states = {unit.unit_id: status for unit, status in zip(result_plan.units, ["COMPLETE", "COMPLETE", "PENDING", "PENDING"])}
    called = []
    result = execute_pending_units(
        result_plan, states, max_units=1, max_live_calls=4,
        execute_unit=lambda unit, ceiling: called.append(unit.index) or 1,
    )
    assert called == [3]
    assert result.skipped_complete_unit_ids == tuple(unit.unit_id for unit in result_plan.units[:2])
    assert result.attempted_unit_ids == (result_plan.units[2].unit_id,)
    assert result.live_calls_used == 1 and result.units_limit_reached


def test_executor_fails_before_starting_a_unit_beyond_live_call_budget():
    result_plan = plan(CANONICAL_START, CANONICAL_START + timedelta(hours=2), max_desired_buckets_per_request=1)
    called = []
    with pytest.raises(LiveCallBudgetExceeded):
        execute_pending_units(
            result_plan, {}, max_units=3, max_live_calls=1,
            execute_unit=lambda unit, ceiling: called.append(unit.index) or 1,
        )
    assert called == [1]


def test_executor_rejects_ambiguous_progress_before_starting_any_unit():
    result_plan = plan(CANONICAL_START, CANONICAL_START + timedelta(hours=1), max_desired_buckets_per_request=1)
    states = {result_plan.units[0].unit_id: "AMBIGUOUS"}
    called = []
    with pytest.raises(BackfillExecutionError):
        execute_pending_units(result_plan, states, max_units=1, max_live_calls=1, execute_unit=lambda unit, limit: called.append(unit))
    assert called == []


def test_default_cli_is_a_plan_only_dry_run(capsys):
    assert main([]) == 0
    output = capsys.readouterr().out
    assert "DESIRED_BUCKET_COUNT=12336" in output
    assert "TOTAL_PLAN_UNITS=74" in output
    assert "LIVE_API_CALLS=0" in output
    assert "DATABASE_WRITES=0" in output
    assert TOKEN not in output
