# Task 036: Meridian Live Demo MVP

## OBJECTIVE

Build a local judge-facing demo that combines a current Nansen Avalanche `$GUN`
Smart Money observation with the committed Task 034 historical OTG analysis.
The live one-hour return drives the selected historical context.

## STARTING_STATE

- Starting main: `3949b0857bad01fd44d7ca82f177fb0de17e2a02`.
- Source-first demo commit: `4a39e0674e4d36b8879280e9377c7cb81e14e61a`.
- The source commit was pushed and verified on `origin/main` before the live
  Nansen validation.
- Task 034 files and methods were not changed.

## BASELINE_TESTS

The offline baseline completed with **281 passed, 6 skipped**. After
implementation, the source-first suite completed with **308 passed, 6
skipped**. The same **308 passed, 6 skipped** completed after live validation.
The default tests make no PostgreSQL, Nansen, or GUNZ RPC connections.

## DEMO_ARCHITECTURE

The local standard-library HTTP server serves a static HTML/CSS/JavaScript UI
and JSON endpoints. It loads committed Task 034 aggregate artifacts from disk.
It requires no PostgreSQL connection. Server startup does not contact Nansen;
only an explicit `/api/live-gun` request reaches the live adapter.

## HISTORICAL_ARTIFACT_CONTRACT

The loader validates the Task 034 summary, relationship matrix, event summary,
row counts, and logical digests before returning any historical values:

- Snapshot: 12,336 rows; digest
  `9ac2109500aea84160555928d297b7efdcd551e23f3259bee5482a1ae5ed19f8`.
- Relationship matrix: 48 rows; digest
  `81004c088b886eee4289151803a18c27d8ee4a75132f178ce6a8be584b1831ef`.
- Event summary: 24 rows; digest
  `5f3e89ed359275c65977acaf02ad45d14b2a8329fcc4902c8e3b590396bff772`.
- Summary digest:
  `e7a16b3b2a84c15d20b5ce019e7463357b06513b60ed7e48754113df2e844e74`.

Any mismatch raises a historical-artifact error and the UI keeps the live
request unavailable rather than proceeding with altered results.

## LIVE_NANSEN_ADAPTER

The adapter reuses the repository `NansenClient`, configuration, flow
normalizer, warning classifier, and structural warning validator. It requests
Avalanche `$GUN` `smart_money` Flows for a dynamic recent UTC window, limited to
one page, one call, zero retries, and at most 120 seconds. It validates
identities, aware hourly bucket boundaries, completion state, uniqueness, and
consecutive latest complete hours, then uses the latest two complete buckets.
The API key remains server-side. Raw response and warning content are never
returned by the demo API.

## LIVE_DECISION_LOGIC

The latest two completed hourly prices produce the live 1-hour return when the
previous price is nonzero. The latest bucket's flow imbalance share is computed
only when the sum of in/out flow counts is positive. The positive and negative
shock thresholds are read from the validated Task 034 summary, not duplicated
in live business logic. The live return selects positive historical events,
negative historical events, the neutral middle-90% message, or an unavailable
state. No event group is fabricated for an unavailable return.

## CACHE_AND_CREDIT_SAFETY

There is no automatic browser polling. The refresh button is the only browser
trigger. A process-local lock prevents concurrent duplicate refreshes and the
sanitized response, including a sanitized failure, is cached for at least 60
seconds. The one real Task 036 validation used **1 Nansen HTTP attempt** and no
retry.

## HTTP_ROUTES

- `GET /` serves the local judge-facing page.
- `GET /api/history` serves validated aggregate Task 034 context.
- `GET /api/live-gun` triggers or returns the cached sanitized live observation.
- `GET /api/health` reports local artifact/service state without contacting
  Nansen.
- `/demo.js` and `/demo.css` serve local static assets from an allowlist.

The server binds to loopback by default (`127.0.0.1:8765`). Traversal requests
are rejected. The page has no external CDN dependency.

## UI_CONTENT

The page displays current live price/return/flow context and LIVE/CACHED state,
the live-selected historical regime, a three-outcome by four-lag Spearman panel,
historical event responses for trades/native GUN/unique buyers at 0/1/6/24
hours, the weak/time-inconsistent finding, and descriptive-only limitations.
It retains historical results on live failure and never substitutes fixture
values for live data. The footer identifies `Blackpoint133/otg-nansen`.

## OFFLINE_TESTS

The 22 new tests cover digest and artifact failure handling, bounded request
shape, complete-hour selection, regime and flow calculations, warning
validation, sanitized failures, cache behavior/expiry, endpoint shape, local
assets, path traversal, no automatic live call, and API-key non-disclosure.
The final complete suite was **308 passed, 6 skipped**. `compileall src` passed.

## SOURCE_FIRST_COMMIT

Commit `4a39e0674e4d36b8879280e9377c7cb81e14e61a` (`feat: add meridian live
demo mvp`) was pushed and read back before the real Nansen request. No source,
test, or UI edit was made after that request.

## LIVE_VALIDATION

One request completed successfully through the committed adapter:

- Request attempts: 1.
- Response records normalized: 11.
- Complete hourly buckets: 11.
- Latest complete bucket: `2026-09-25T07:00:00Z` to
  `2026-09-25T08:00:00Z`.
- Price return available: yes.
- Flow imbalance share available: no (the latest bucket had no positive
  in-plus-out denominator).
- Current regime: `MIDDLE_90_PERCENT`.
- Warning policy: pass.

Volatile price and flow values are intentionally omitted from this durable
report.

## LOCAL_SERVER_SMOKE_TEST

The committed server handler was started on an ephemeral loopback port with an
offline fake live provider. `/`, `/demo.js`, `/demo.css`, `/api/health`,
`/api/history`, and `/api/live-gun` returned 200; a traversal route returned
404. The HTML referenced only local application assets (the explicit GitHub
project link is not a CDN). Historical relationship/event aggregates and live
regime handling were present. The fake provider was called once and the server
shut down cleanly. **Smoke test: PASS.**

## JUDGE_DEMO_CONTENT_CONTRACT

**PASS.** The source and served responses contain the live Nansen card, the
current-regime decision path, 12 primary relationship cells, 24 event summary
cells, weak/time-inconsistent finding, noncausal/nonpredictive language, and
GitHub project identity.

## BUILDATHON_CALL_COUNT_UPDATE

Task 035 documented a project minimum of 117 eligible attempts. Task 036 added
one separately documented live demo validation attempt, producing a current
documented minimum of **118**. The 100+ interpretation is met; 1,000 is not.
This project-side total is not a guarantee of Nansen's internal quota counter.
The Task 035 audit remains unchanged; a dated addendum was added to
`docs/meridian_submission.md`.

## RESOURCE_OBSERVATION

Windows resource samples (CPU is a one-second system sample; memory is in MB):

| Phase | CPU % | Available RAM | Committed | Commit limit | Free commit |
|---|---:|---:|---:|---:|---:|
| Before live request | 99.2 | 4,064 | 20,765 | 31,731 | 10,966 |
| After live request | 50.1 | 3,999 | 20,755 | 31,731 | 10,976 |
| During local smoke server | 7.1 | 4,289 | 20,528 | 31,731 | 11,202 |
| After shutdown and final tests | 38.6 | 3,507 | 21,582 | 31,731 | 10,149 |

Memory and commit headroom remained available throughout; the brief high CPU
sample before the HTTP request subsided. **RESOURCE_STABILITY=PASS.**

## NANSEN_API_CALL_PROOF

`NANSEN_API_CALLS_TASK036=1`: exactly one HTTP request attempt reached the
committed Nansen client. A preceding local configuration check failed before
request construction and had zero attempts. No retry or later live route call
occurred.

## DATABASE_SAFETY

No production or staging database connection was opened. Production and
staging DDL/DML were zero. The demo depends only on committed local artifacts
and the live Nansen API request.

## SECURITY_CHECK

The browser receives only sanitized aggregate/current fields. No key, request
headers, raw response, raw warning, identity, or credential was committed or
printed. `SECRET_SCAN=PASS`; `.env` is untracked (`ENV_TRACKED=NO`).

## CYRILLIC_CHECK

`CYRILLIC_SCAN=PASS`.

## FILES_CHANGED

Source-first commit:

- `README.md`
- `src/otg_nansen/demo_data.py`
- `src/otg_nansen/demo_live.py`
- `src/otg_nansen/demo_app.py`
- `tests/test_demo_data.py`
- `tests/test_demo_live.py`
- `tests/test_demo_app.py`
- `web/demo.html`
- `web/demo.js`
- `web/demo.css`

Evidence commit:

- `docs/meridian_submission.md` (Task 036 addendum only)
- `DEV/reports/036_meridian_live_demo_mvp/report.md`

Task 034 analysis and result files were not modified.

## KNOWN_LIMITATIONS

The demo is local-only and requires a valid `NANSEN_API_KEY` in the server
environment when live data is requested. The latest live flow imbalance share
was unavailable in this observation. A screen recording, public deployment,
X post, and entry form submission remain outside this task. The official 100
versus 1,000 call threshold conflict remains unresolved.

## NEXT_RECOMMENDED_TASK

Record the specified silent 45-second local demo with a fresh operator-run live
refresh, keeping the observation time and descriptive limitations visible.
Then review submission requirements before any public post or entry submission.
