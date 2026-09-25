from pathlib import Path
import re


LAUNCHER = Path(__file__).resolve().parents[1] / "scripts" / "run_meridian_demo.ps1"


def test_launcher_fails_closed_without_key_and_never_prints_it():
    source = LAUNCHER.read_text(encoding="utf-8")
    assert "IsNullOrWhiteSpace($env:NANSEN_API_KEY)" in source
    assert "Write-Output $env:NANSEN_API_KEY" not in source
    assert "Write-Host $env:NANSEN_API_KEY" not in source
    assert "Write-Output 'http://127.0.0.1:8765/'" in source


def test_launcher_sets_project_pythonpath_and_runs_committed_module():
    source = LAUNCHER.read_text(encoding="utf-8")
    assert "Join-Path $repositoryRoot 'src'" in source
    assert "-m otg_nansen.demo_app --serve" in source
    assert "1>$null" in source


def test_launcher_has_no_network_or_database_operations():
    source = LAUNCHER.read_text(encoding="utf-8")
    assert not re.search(r"(?i)curl|invoke-webrequest|invoke-restmethod|psql|postgres|nansen\.ai", source)


def test_launcher_does_not_write_credentials_or_open_browser():
    source = LAUNCHER.read_text(encoding="utf-8")
    assert not re.search(r"(?i)set-content|out-file|new-item|start-process|start\s+http", source)
    assert "127.0.0.1" in source
