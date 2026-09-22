"""Offline checks for PostgreSQL adapter safety and migration guards."""

from pathlib import Path

from otg_nansen.postgres import ALLOWED_STAGING_DATABASE, staging_connection_kwargs


def test_staging_connection_is_pinned_to_allowed_database():
    assert ALLOWED_STAGING_DATABASE == "server_otg_staging"
    assert staging_connection_kwargs()["dbname"] == ALLOWED_STAGING_DATABASE


def test_migration_has_no_drop_and_has_target_scope_guards():
    text = (Path(__file__).parents[1] / "sql" / "001_create_nansen_schema.sql").read_text(encoding="utf-8")
    assert "DROP " not in text.upper()
    for key in ("chain", "endpoint", "token_address", "flow_label"):
        assert f"request_scope ? '{key}'" in text or f"request_scope->>'{key}'" in text
    assert "jsonb_typeof(request_scope) = 'object'" in text
    assert "jsonb_typeof(request_scope->'chain') = 'string'" in text
    assert ") IS TRUE" in text
    assert "request_scope->>'chain' = chain" in text
    assert "request_scope->>'flow_label' = flow_label" in text
    assert "UNIQUE (run_id, chain, endpoint, token_address, flow_label)" in text
    assert "FOREIGN KEY (last_success_run_id, chain, endpoint, token_address, flow_label)" in text
