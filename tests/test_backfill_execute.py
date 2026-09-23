from otg_nansen.backfill_execute import execution_enabled


def test_backfill_runner_requires_both_explicit_opt_ins():
    assert not execution_enabled(False, {"NANSEN_RUN_LIVE_BACKFILL": "1"})
    assert not execution_enabled(True, {})
    assert not execution_enabled(True, {"NANSEN_RUN_LIVE_BACKFILL": "true"})
    assert execution_enabled(True, {"NANSEN_RUN_LIVE_BACKFILL": "1"})
