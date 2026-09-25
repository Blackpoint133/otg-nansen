# OTG - Nansen Market Intelligence

## What It Does

This project ingests Nansen Avalanche `$GUN` Smart Money flow history, aligns
OTG marketplace activity to UTC hours, and builds a complete 12,336-hour joined
dataset. A preregistered descriptive analysis compares fixed-lag Nansen price
and flow measures with OTG activity and summarizes marketplace behavior
around large price moves. The analysis preserves weak, null, and
time-inconsistent results instead of tuning methods for a preferred result.

## Why Nansen Matters

Nansen data drives the analysis. Hourly `price_usd` supplies the preregistered
one-hour `$GUN` price return and price-shock event thresholds. The hourly
`total_inflows_count` and `total_outflows_count` fields define
`flow_imbalance_share`; its sparse observations are retained and reported as
not reliably estimable where the preregistered rules require. Other source
fields are retained in the aligned data contract but were not promoted to
additional Task 034 drivers.

## Current Result

In the analyzed sample, hourly `$GUN` price-return relationships with OTG
marketplace activity were weak and time-inconsistent. Descriptive responses
around extreme price moves are available in the committed event summary.
Flow-imbalance-share relationships were too sparse to estimate reliably under
the preregistered rules. These results do not establish predictive alpha.

## Architecture

`Nansen API -> normalized staging -> canonical hourly history -> OTG hourly
market aggregation -> aligned analytical snapshot -> preregistered analysis
-> presentation layer`

The project has implemented ingestion, canonical hourly history, the OTG hourly
market foundation, the preregistered Task 034 descriptive analysis, and a
tested local live-Nansen demo. Recording, posting, and entry submission remain
operator steps.

## Reproducible Analysis

From the repository root, install and run the offline suite:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[test]"
pytest -q
```

Committed Task 034 aggregate results are in `DEV/analysis/034_*.csv` and
`DEV/analysis/034_analysis_summary.json`; the interpretation and integrity
details are in
[`DEV/reports/034_otg_gun_relationship_analysis/report.md`](DEV/reports/034_otg_gun_relationship_analysis/report.md).

To rerun the frozen analysis against an already configured staging snapshot
(read-only; writes aggregate result files locally):

```powershell
$env:PYTHONPATH = "src"
python -m otg_nansen.relationship_analysis --execute-readonly
```

This command reads `server_otg_staging` only. It does not call Nansen, modify
the database, or access production. Staging PostgreSQL connection settings
must be configured locally; never commit `.env` or credentials.

## Live Demo

From the repository root, install the project and make `NANSEN_API_KEY`
available to the local PowerShell process. Then start the demo:

```powershell
python -m pip install -e ".[test]"
.\scripts\run_meridian_demo.ps1
```

The app runs at <http://127.0.0.1:8765/>. Select **Refresh Live Data** to make
one bounded Avalanche `$GUN` Smart Money Flows request. The app does not poll
automatically; its sanitized response is cached in memory for at least 60
seconds. The key stays in the server process and is never sent to browser code.
Historical relationship and price-shock views come from the committed,
digest-validated Task 034 aggregate artifacts. No PostgreSQL connection is
required. This is a local demo and is not publicly deployed.

Manual alternate launch, if the helper script is unavailable:

```powershell
$env:PYTHONPATH = "src"
python -m otg_nansen.demo_app --serve
```

## Safety / Interpretation

Correlation is not causation. Lagged association is not prediction. The market
amount is parser-recorded integer-truncated native GUN; it is kept separate
from Avalanche Nansen values. No marketplace USD volume is fabricated.

## Meridian Buildathon

Built with the Nansen API and maintained in a public GitHub repository. The
local demo and submission materials are prepared. Recording, the X post, and
entry submission remain operator steps. The official call threshold conflict
and project-side documented count are recorded in
[`docs/meridian_submission.md`](docs/meridian_submission.md); Nansen's internal
quota total has not been independently confirmed.
