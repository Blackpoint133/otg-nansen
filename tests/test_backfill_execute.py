import pytest

from otg_nansen.backfill import (
    BackfillExecutionError,
    PlanProgress,
    execute_pending_units,
)
from otg_nansen.backfill_execute import (
    ABSOLUTE_MAX_LIVE_CALLS_PER_INVOCATION,
    ABSOLUTE_MAX_UNITS_PER_INVOCATION,
    expected_progress_after,
    execution_enabled,
    first_pending_index,
    select_authorized_units,
    should_stop_for_resource_pressure,
    validate_invocation_limits,
    validate_task028_bounds,
)
from otg_nansen.backfill_plan import build_canonical_plan


def test_backfill_runner_requires_both_explicit_opt_ins():
    assert not execution_enabled(False, {"NANSEN_RUN_LIVE_BACKFILL": "1"})
    assert not execution_enabled(True, {})
    assert not execution_enabled(True, {"NANSEN_RUN_LIVE_BACKFILL": "true"})
    assert execution_enabled(True, {"NANSEN_RUN_LIVE_BACKFILL": "1"})


def _progress(plan, complete=0, pending=None, ambiguous=0):
    statuses = {}
    for unit in plan.units:
        statuses[unit.unit_id] = "COMPLETE" if unit.index <= complete else "PENDING"
    return PlanProgress(statuses, complete, len(plan.units) - complete - ambiguous if pending is None else pending, ambiguous)


def test_absolute_invocation_caps_reject_batches_over_twenty():
    assert ABSOLUTE_MAX_UNITS_PER_INVOCATION == 20
    assert ABSOLUTE_MAX_LIVE_CALLS_PER_INVOCATION == 20
    with pytest.raises(BackfillExecutionError):
        validate_invocation_limits(21, 21)
    with pytest.raises(BackfillExecutionError):
        validate_invocation_limits(10, 21)
    with pytest.raises(BackfillExecutionError):
        validate_invocation_limits(10, 9)


def test_expected_complete_and_first_pending_mismatches_refuse_selection():
    plan = build_canonical_plan()
    progress = _progress(plan, complete=3)
    with pytest.raises(BackfillExecutionError):
        select_authorized_units(plan, progress, max_units=10, max_live_calls=10,
                                expected_complete_before=2, expected_first_pending_index=4)
    with pytest.raises(BackfillExecutionError):
        select_authorized_units(plan, progress, max_units=10, max_live_calls=10,
                                expected_complete_before=3, expected_first_pending_index=3)


def test_resumed_state_selects_ten_dynamic_pending_units_four_through_thirteen():
    plan = build_canonical_plan()
    progress = _progress(plan, complete=3)
    selected = select_authorized_units(plan, progress, max_units=10, max_live_calls=10,
                                       expected_complete_before=3, expected_first_pending_index=4)
    assert tuple(unit.index for unit in selected) == tuple(range(4, 14))
    assert all(unit.desired_bucket_count == 167 for unit in selected)
    validate_task028_bounds(selected)


def test_task028_independent_bounds_reject_an_altered_unit():
    plan = build_canonical_plan()
    progress = _progress(plan, complete=3)
    selected = select_authorized_units(plan, progress, max_units=10, max_live_calls=10,
                                       expected_complete_before=3, expected_first_pending_index=4)
    changed = (selected[0].__class__(**{**selected[0].__dict__, "request_end": selected[0].request_end}), *selected[1:])
    validate_task028_bounds(changed)
    altered_first = selected[0].__class__(**{**selected[0].__dict__, "coverage_end": selected[0].coverage_end.replace(minute=1)})
    with pytest.raises(BackfillExecutionError):
        validate_task028_bounds((altered_first, *selected[1:]))


def test_progress_math_is_relative_to_persisted_completion():
    plan = build_canonical_plan()
    before = _progress(plan, complete=3)
    assert expected_progress_after(before, 1) == (4, 70, 0)
    assert expected_progress_after(before, 10) == (13, 61, 0)


def test_resource_stop_is_relative_to_this_invocation_not_unit_index():
    pressure = (50.0, 1, 100, 1)
    assert should_stop_for_resource_pressure(pressure, successful_units=1, selected_units=10)
    assert not should_stop_for_resource_pressure(pressure, successful_units=10, selected_units=10)


def test_generic_restart_selects_next_pending_after_contiguous_batch():
    plan = build_canonical_plan()
    statuses = {unit.unit_id: ("COMPLETE" if unit.index <= 13 else "PENDING") for unit in plan.units}
    assert first_pending_index(plan, statuses) == 14


@pytest.mark.parametrize("calls", [0, 2])
def test_executor_rejects_callback_not_reporting_exactly_one_call(calls):
    plan = build_canonical_plan()
    with pytest.raises(BackfillExecutionError):
        execute_pending_units(plan, {}, max_units=1, max_live_calls=1,
                              max_calls_per_unit=1, execute_unit=lambda unit, ceiling: calls)


def test_executor_refuses_ambiguous_and_skips_completed_without_call_budget():
    plan = build_canonical_plan()
    states = {unit.unit_id: ("COMPLETE" if unit.index <= 3 else "PENDING") for unit in plan.units}
    called = []
    result = execute_pending_units(plan, states, max_units=1, max_live_calls=1,
                                   execute_unit=lambda unit, ceiling: called.append(unit.index) or 1)
    assert called == [4]
    assert result.skipped_complete_unit_ids == tuple(unit.unit_id for unit in plan.units[:3])
    ambiguous = dict(states)
    ambiguous[plan.units[3].unit_id] = "AMBIGUOUS"
    with pytest.raises(BackfillExecutionError):
        execute_pending_units(plan, ambiguous, max_units=1, max_live_calls=1,
                              execute_unit=lambda unit, ceiling: 1)


def test_executor_stops_after_first_failure_in_resumed_plan():
    plan = build_canonical_plan()
    states = {unit.unit_id: ("COMPLETE" if unit.index <= 3 else "PENDING") for unit in plan.units}
    attempted = []

    def callback(unit, ceiling):
        attempted.append(unit.index)
        if unit.index == 5:
            raise RuntimeError("synthetic stop")
        return 1

    with pytest.raises(RuntimeError, match="synthetic stop"):
        execute_pending_units(plan, states, max_units=10, max_live_calls=10, execute_unit=callback)
    assert attempted == [4, 5]
