import pytest
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from otg_nansen.backfill import (
    BackfillExecutionError,
    PlanProgress,
    execute_pending_units,
)
from otg_nansen.backfill_execute import (
    ABSOLUTE_MAX_LIVE_CALLS_PER_INVOCATION,
    ABSOLUTE_MAX_UNITS_PER_INVOCATION,
    expected_next_pending_index,
    format_batch_status,
    expected_progress_after,
    execution_enabled,
    first_pending_index,
    _utc_identity,
    select_authorized_units,
    should_stop_for_resource_pressure,
    validate_checkpoint_transition,
    validate_recent_identity_transition,
    _utc_wire,
    validate_invocation_limits,
)
from otg_nansen.backfill_plan import build_canonical_plan


def test_backfill_runner_requires_both_explicit_opt_ins():
    assert not execution_enabled(False, {"NANSEN_RUN_LIVE_BACKFILL": "1"})
    assert not execution_enabled(True, {})
    assert not execution_enabled(True, {"NANSEN_RUN_LIVE_BACKFILL": "true"})
    assert execution_enabled(True, {"NANSEN_RUN_LIVE_BACKFILL": "1"})


def test_batch_status_output_is_task_agnostic():
    assert format_batch_status("SUCCESS") == "BACKFILL_BATCH_STATUS=SUCCESS"
    assert format_batch_status("SOURCE_COVERAGE_GAP") == "BACKFILL_BATCH_STATUS=SOURCE_COVERAGE_GAP"
    assert format_batch_status("LIVE_BATCH_FAILURE") == "BACKFILL_BATCH_STATUS=LIVE_BATCH_FAILURE"
    with pytest.raises(ValueError):
        format_batch_status("UNSUPPORTED_STATUS")


def test_checkpoint_timestamp_gate_compares_utc_instants():
    local = datetime(2026, 9, 20, 16, 59, 59, tzinfo=timezone(timedelta(hours=-7)))
    assert _utc_wire(local) == "2026-09-20T23:59:59Z"


def test_bucket_identity_comparison_canonicalizes_daylight_saving_fold_to_utc():
    los_angeles = ZoneInfo("America/Los_Angeles")
    database_bucket = (
        datetime(2025, 11, 2, 1, 0, tzinfo=los_angeles, fold=0),
        datetime(2025, 11, 2, 1, 0, tzinfo=los_angeles, fold=1),
    )
    canonical_bucket = (
        datetime(2025, 11, 2, 8, 0, tzinfo=timezone.utc),
        datetime(2025, 11, 2, 9, 0, tzinfo=timezone.utc),
    )
    assert _utc_identity(*database_bucket) == canonical_bucket


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
        validate_invocation_limits(10, 11)
    with pytest.raises(BackfillExecutionError):
        validate_invocation_limits(10, 9)
    with pytest.raises(BackfillExecutionError):
        validate_invocation_limits(21, 21)
    validate_invocation_limits(20, 20)


def test_expected_complete_and_first_pending_mismatches_refuse_selection():
    plan = build_canonical_plan()
    progress = _progress(plan, complete=3)
    with pytest.raises(BackfillExecutionError):
        select_authorized_units(plan, progress, max_units=10, max_live_calls=10,
                                expected_complete_before=2, expected_first_pending_index=4)
    with pytest.raises(BackfillExecutionError):
        select_authorized_units(plan, progress, max_units=10, max_live_calls=10,
                                expected_complete_before=3, expected_first_pending_index=3)


def test_resumed_state_selects_twenty_dynamic_pending_units_fourteen_through_thirty_three():
    plan = build_canonical_plan()
    progress = _progress(plan, complete=13)
    selected = select_authorized_units(plan, progress, max_units=20, max_live_calls=20,
                                       expected_complete_before=13, expected_first_pending_index=14)
    assert tuple(unit.index for unit in selected) == tuple(range(14, 34))
    assert all(unit.desired_bucket_count == 167 for unit in selected)
    assert selected[0].index == 14
    assert selected[-1].index == 33
    assert [right.index - left.index for left, right in zip(selected, selected[1:])] == [1] * 19
    assert first_pending_index(plan, progress.statuses) == 14


def test_progress_math_is_relative_to_persisted_completion():
    plan = build_canonical_plan()
    before = _progress(plan, complete=13)
    assert expected_progress_after(before, 1) == (14, 60, 0)
    assert expected_progress_after(before, 20) == (33, 41, 0)
    statuses = {unit.unit_id: ("COMPLETE" if unit.index <= 33 else "PENDING") for unit in plan.units}
    assert first_pending_index(plan, statuses) == 34


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


def _checkpoint_owner(*, status="success", chain="avalanche", endpoint="flows",
                      token_address=None, flow_label="smart_money", window_end=None):
    plan = build_canonical_plan()
    return {
        "status": status,
        "chain": chain,
        "endpoint": endpoint,
        "token_address": token_address or plan.token_address,
        "flow_label": flow_label,
        "window_end": window_end or datetime(2026, 9, 20, 23, 59, 59, tzinfo=timezone.utc),
    }


def test_checkpoint_unchanged_timestamp_and_owner_passes():
    timestamp = datetime(2026, 9, 20, 23, 59, 59, tzinfo=timezone.utc)
    assert validate_checkpoint_transition(
        (timestamp, "same-run"), (timestamp, "same-run"), None,
        chain="avalanche", token_address=build_canonical_plan().token_address,
        flow_label="smart_money",
    )


def test_checkpoint_advanced_timestamp_requires_matching_success_owner():
    before = datetime(2026, 9, 20, 22, 59, 59, tzinfo=timezone.utc)
    after = datetime(2026, 9, 20, 23, 59, 59, tzinfo=timezone.utc)
    assert validate_checkpoint_transition(
        (before, "old"), (after, "new"), _checkpoint_owner(window_end=after),
        chain="avalanche", token_address=build_canonical_plan().token_address,
        flow_label="smart_money",
    )


def test_checkpoint_equal_timestamp_accepts_valid_owner_replacement():
    timestamp = datetime(2026, 9, 20, 23, 59, 59, tzinfo=timezone.utc)
    assert validate_checkpoint_transition(
        (timestamp, "old"), (timestamp, "new"), _checkpoint_owner(window_end=timestamp),
        chain="avalanche", token_address=build_canonical_plan().token_address,
        flow_label="smart_money",
    )


def test_checkpoint_timestamp_regression_fails_even_if_owner_changes():
    before = datetime(2026, 9, 20, 23, 59, 59, tzinfo=timezone.utc)
    after = before - timedelta(seconds=1)
    with pytest.raises(BackfillExecutionError, match="regressed"):
        validate_checkpoint_transition(
            (before, "old"), (after, "new"), _checkpoint_owner(window_end=after),
            chain="avalanche", token_address=build_canonical_plan().token_address,
            flow_label="smart_money",
        )


@pytest.mark.parametrize("owner", [
    _checkpoint_owner(status="failed"),
    _checkpoint_owner(chain="solana"),
    _checkpoint_owner(window_end=datetime(2026, 9, 20, 22, 59, 59, tzinfo=timezone.utc)),
])
def test_checkpoint_owner_replacement_rejects_failed_wrong_stream_or_window(owner):
    timestamp = datetime(2026, 9, 20, 23, 59, 59, tzinfo=timezone.utc)
    with pytest.raises(BackfillExecutionError, match="owner"):
        validate_checkpoint_transition(
            (timestamp, "old"), (timestamp, "new"), owner,
            chain="avalanche", token_address=build_canonical_plan().token_address,
            flow_label="smart_money",
        )


def test_recent_identity_transition_accepts_unchanged_and_authorized_sets():
    old = ("old-a", "old-b")
    added = "selected-desired-recent-id"
    unchanged = validate_recent_identity_transition(old, old, ())
    assert unchanged.preexisting_preserved and unchanged.new_identity_count == 0
    result = validate_recent_identity_transition(old, (*old, added), (added,))
    assert result.preexisting_preserved
    assert result.new_identity_count == 1
    assert result.new_identities_authorized
    assert result.duplicate_count == 0


def test_recent_identity_transition_rejects_removed_preexisting_identity():
    with pytest.raises(BackfillExecutionError, match="removed"):
        validate_recent_identity_transition(("old-a", "old-b"), ("old-a",), ())


def test_recent_identity_transition_rejects_unselected_new_identity():
    with pytest.raises(BackfillExecutionError, match="unexpected"):
        validate_recent_identity_transition(("old",), ("old", "new"), ())


def test_recent_identity_transition_rejects_duplicate_natural_identity():
    with pytest.raises(BackfillExecutionError, match="duplicate"):
        validate_recent_identity_transition(("old",), ("old", "old"), ())


def test_terminal_resume_expectation_accepts_none_after_final_plan_unit():
    plan = build_canonical_plan()
    assert expected_next_pending_index(plan.units[4:5], plan) == 6
    assert expected_next_pending_index(plan.units[-1:], plan) is None
    completed = _progress(plan, complete=len(plan.units))
    assert first_pending_index(plan, completed.statuses) is None
