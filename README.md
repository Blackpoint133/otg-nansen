# OTG - Nansen Market Intelligence

Live $GUN context and historical OTG marketplace reaction, built with Nansen data.

**Try the live product:** [OTG - Nansen Market Intelligence](https://otgos.run.place/?mode=nansen)

## What It Is

OTG — Nansen Market Intelligence is an experimental market-intelligence layer for the Off The Grid NFT marketplace. It combines current Avalanche $GUN market context from Nansen with historical OTG marketplace activity.

The page helps users see whether current $GUN conditions are within the usual historical range or unusually strong, then compare them with how OTG activity behaved around similar past moves. It provides context, not a prediction or causal explanation.

## Live Product

The Nansen mode is integrated into the production version of OTG Analytics:

**[Open OTG Analytics - Nansen mode](https://otgos.run.place/?mode=nansen)**

OTG Analytics covers the Off The Grid NFT marketplace. Its Nansen mode adds live $GUN context and a historical cross-market comparison. A shared observation updates automatically on an approximately hourly schedule, so users see the latest successful data without triggering a request from each page visit.

## What You Can Analyze

The production page shows:

- Current Avalanche $GUN price and its one-hour move.
- Nansen Smart Money flow context.
- Whether the current move is inside or outside its normal historical range.
- Historical OTG transaction, native GUN marketplace volume, and active-buyer responses.
- Fixed 0h, 1h, 6h, and 24h comparison horizons.
- A concise Market Takeaway.

## Why Nansen Matters

Nansen data drives the product logic. Avalanche $GUN price observations determine the current market context and define the historical price-move groups. Nansen Smart Money flow data adds live flow context. Those observations are compared with OTG marketplace activity, so Nansen is part of the analysis rather than a decorative data feed.

## Historical Result

Historical hourly $GUN price-return relationships with OTG marketplace activity were weak and time-inconsistent. Responses around unusually large $GUN moves remain useful as descriptive market context, but the observed relationship was not strong enough to justify a standalone predictive trading signal.

Historical flow-imbalance observations were too sparse to estimate a reliable relationship under the preregistered rules. This result is preserved as observed; the analysis was not tuned to produce a stronger conclusion.

## How the Product Works

**Live context:** A private production service retrieves Nansen data on a shared hourly schedule and serves a sanitized latest successful observation to OTG Analytics.

**Historical context:** A fixed, complete hourly dataset aligns Avalanche $GUN observations with OTG marketplace activity. Preregistered aggregate results provide the historical relationship and price-move comparisons shown in the page.

Conceptually:

`Nansen API -> normalized $GUN observations -> canonical hourly history -> OTG hourly marketplace activity -> aligned historical analysis -> shared live context -> OTG Analytics Nansen mode`

The live observation describes current conditions. The historical analysis describes what was observed in the fixed sample; it does not forecast what happens next.

## Meridian Buildathon

Built for the Nansen Meridian Buildathon, this project uses Nansen data as a core analytical input and is available in the production OTG Analytics application. Official Buildathon materials have differed on the API-call threshold; the project's documented audit and source notes are available in the [submission readiness record](docs/meridian_submission.md). The project does not generate calls merely to inflate a quota.

## Historical Dataset and Method

The historical comparison contains 12,336 aligned hourly observations spanning 2025-04-25 through 2026-09-20. The fixed comparisons use 0h, 1h, 6h, and 24h offsets. The price-move view compares OTG marketplace responses around unusually positive and negative hourly $GUN returns.

The analysis plan, transformations, event rules, and limitations are documented in the [market reaction methodology](docs/market_reaction_methodology.md). The full relationship matrix, event summaries, and aggregate digests are committed under `DEV/analysis/`; the readable findings are in the [analysis report](DEV/reports/034_otg_gun_relationship_analysis/report.md).

## Limitations and Interpretation

The findings are descriptive. Correlation does not establish causation, and a lagged association is not a prediction. The historical relationship was weak and time-inconsistent.

Avalanche Nansen metrics and OTG marketplace-native GUN amounts are kept separate. Marketplace USD volume is not fabricated. Smart Money flow imbalance is shown as context; its historical coverage is too sparse for a reliable predictive relationship.

## Reproducibility

### Offline installation and tests

From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[test]"
pytest -q
```

The default suite uses offline fixtures and does not require PostgreSQL, Nansen, or on-chain RPC access.

### Inspect committed results

The aggregate result files are:

- `DEV/analysis/034_relationship_matrix.csv`
- `DEV/analysis/034_price_shock_event_summary.csv`
- `DEV/analysis/034_analysis_summary.json`

Their source snapshot and content digests are recorded in the summary and analysis report.

### Repeat the read-only analysis

With local read-only staging database settings configured, the preregistered analysis can be rerun from the repository root:

```powershell
$env:PYTHONPATH = "src"
python -m otg_nansen.relationship_analysis --execute-readonly
```

This reads the staging analytical snapshot and writes aggregate result files locally. It does not call Nansen or modify database data. Never commit database credentials or `.env` files.

### Run a separate local live service

A local live service is optional; judges can use the production link above. To run the service locally, install the project and provide `NANSEN_API_KEY` in the server process environment:

```powershell
python -m pip install -e ".[test]"
.\scripts\run_meridian_demo.ps1
```

The script starts a local service at <http://127.0.0.1:8765/>. It performs a shared initial refresh when needed and then follows the hourly schedule; page reads do not request fresh Nansen data. Its persisted sanitized state is local to the configured service environment. No PostgreSQL connection is needed for the live page.

## Data Safety

Nansen credentials remain server-side. The public page receives only sanitized current aggregate fields and committed historical summaries. The application does not require a PostgreSQL connection for demo runtime.

## Project Records

- [Market reaction methodology](docs/market_reaction_methodology.md)
- [Submission requirements and documented call audit](docs/meridian_submission.md)
- [Analysis findings](DEV/reports/034_otg_gun_relationship_analysis/report.md)
