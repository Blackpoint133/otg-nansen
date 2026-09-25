import json
from pathlib import Path

import pytest

from otg_nansen.demo_data import HistoricalArtifactError, load_historical_artifacts


ROOT = Path(__file__).resolve().parents[1]


def test_committed_task034_artifacts_validate_and_expose_aggregate_views():
    data = load_historical_artifacts(ROOT)
    assert data["snapshot_row_count"] == 12336
    assert data["snapshot_digest"] == "9ac2109500aea84160555928d297b7efdcd551e23f3259bee5482a1ae5ed19f8"
    assert len(data["relationship_rows"]) == 12
    assert len(data["event_rows"]) == 24
    assert data["q05_historical_threshold"] == pytest.approx(-0.016533971141552434)
    assert data["q95_historical_threshold"] == pytest.approx(0.016966713439596874)


@pytest.mark.parametrize("filename", [
    "034_analysis_summary.json",
    "034_relationship_matrix.csv",
    "034_price_shock_event_summary.csv",
])
def test_tampered_historical_artifact_fails_closed(tmp_path, filename):
    source = ROOT / "DEV" / "analysis"
    target = tmp_path / "DEV" / "analysis"
    target.mkdir(parents=True)
    for name in ("034_analysis_summary.json", "034_relationship_matrix.csv", "034_price_shock_event_summary.csv"):
        (target / name).write_bytes((source / name).read_bytes())
    path = target / filename
    if filename.endswith(".json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["snapshot_row_count"] += 1
        path.write_text(json.dumps(payload), encoding="utf-8")
    else:
        lines = path.read_text(encoding="utf-8").splitlines()
        cells = lines[1].split(",")
        if filename == "034_relationship_matrix.csv":
            cells[3] = "999"
        else:
            cells[3] = "999"
        lines[1] = ",".join(cells)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    with pytest.raises(HistoricalArtifactError):
        load_historical_artifacts(tmp_path)
