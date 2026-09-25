from pathlib import Path
import re


WRAPPER = Path(__file__).resolve().parents[1] / "scripts" / "run_meridian_demo_service.ps1"


def test_service_wrapper_reads_existing_server_environment_without_echoing_key():
    source = WRAPPER.read_text(encoding="utf-8")
    assert "ReadAllLines($environmentFile)" in source
    assert "NANSEN_API_KEY" in source
    assert "Write-Output $apiKey" not in source
    assert "Write-Host $apiKey" not in source
    assert "Write-Output $env:NANSEN_API_KEY" not in source


def test_service_wrapper_starts_loopback_demo_with_pinned_runtime():
    source = WRAPPER.read_text(encoding="utf-8")
    assert r"C:\VAMBAM\Projects\OTG\.venv\Scripts\python.exe" in source
    assert "-m otg_nansen.demo_app --serve --host 127.0.0.1 --port 8765" in source
    assert "Join-Path $repositoryRoot 'src'" in source


def test_service_wrapper_never_calls_external_services_or_writes_credentials():
    source = WRAPPER.read_text(encoding="utf-8")
    assert not re.search(r"(?i)curl|invoke-webrequest|invoke-restmethod|psql|psycopg|set-content|out-file|new-item", source)
