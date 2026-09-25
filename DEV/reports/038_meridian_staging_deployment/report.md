# Task 038: Meridian Staging Deployment

## Starting Remote HEAD

Starting remote and local `main` were both
`c84516f7cc11958cc63a50531f416496d1a2c932`, with a clean worktree and no
newer remote commits.

## Staging Infrastructure Discovered

The VPS serves the requested domains through the existing Caddy Windows
service (`Caddy`, managed by NSSM). The Caddy service uses
`C:\Caddy\Caddyfile`; its existing `otgostest.run.place` host block proxied
to the staging OpenSea application on port 8504. The production host has a
separate `otgos.run.place` block and upstream on port 8502. The host's
`system_management` registry is the canonical inventory for NSSM services.

The existing Caddy TLS binding was active for the staging host. Initial and
post-deployment HTTPS requests completed with certificate verification
enabled. Caddy configuration was validated and hot-reloaded; Caddy and
unrelated application services were not restarted.

## Deployment Architecture

The existing Caddy HTTPS endpoint now proxies the `otgostest.run.place` host
to `127.0.0.1:8765`. The demo runs as the automatic Windows service
`OTG_staging_meridian_demo`, installed through NSSM and registered in the
existing OTG service-management registry as a non-production experimental
service. It runs as `LocalSystem`, starts automatically, and is reported
`RUNNING` / `HEALTHY` by the manager. Port 8765 listens only on loopback.

The process-local response cache remains at least 60 seconds. The page has no
automatic polling; source inspection confirms that only the explicit refresh
button calls `/api/live-gun`. The Caddy build has no rate-limit module, so the
existing serialized in-process cache is the request-burst safeguard used here.

## Key Configuration

The existing parser `.env` was the only configured server-side Nansen key
source. Its contents were not printed or copied. Its NTFS ACL was restricted
to `NT AUTHORITY\SYSTEM` and `BUILTIN\Administrators`; the environment file
remains untracked. The service runner reads the key in memory at startup and
does not pass it in NSSM arguments, write it to another file, or log it. The
service log directory is also restricted to SYSTEM and Administrators.

## Files Changed

Repository changes:

- `scripts/run_meridian_demo_service.ps1` loads the protected existing
  environment and launches the loopback app with the shared OTG Python runtime.
- `tests/test_demo_service_wrapper.py` checks the wrapper's secret handling,
  binding, launch command, and absence of network/database/write commands.
- `docs/deployment.md` records the isolated staging architecture and key
  handling.
- This deployment report.

Host changes outside Git:

- Changed only the `otgostest.run.place` fallback upstream in
  `C:\Caddy\Caddyfile`, from port 8504 to 8765; preserved the production
  host block and upstream.
- Installed and started automatic NSSM service
  `OTG_staging_meridian_demo`.
- Added its non-production entry to
  `C:\VAMBAM\Projects\OTG\system_management\service_registry.json`.
- Created the restricted service log directory under the existing OTG log
  tree.
- Tightened access to the already-existing untracked parser `.env` file.

## Public HTTPS Validation

- `https://otgostest.run.place/`: HTTP 200; TLS verification passed.
- `/demo.js` and `/demo.css`: HTTP 200 with JavaScript and CSS content types.
- `/api/health`: HTTP 200 with `status=ok`,
  `historical_artifacts=ready`, `live_data=requested_on_demand`, and
  `database_required=false`.
- `/api/history`: HTTP 200, `status=success`, 12 primary relationship rows,
  24 event-summary rows, and the accepted Task 034 snapshot digest
  `9ac2109500aea84160555928d297b7efdcd551e23f3259bee5482a1ae5ed19f8`.
- The served page contains the project title, LIVE NANSEN DATA card, `$GUN`
  Smart Money label, explicit refresh button, live-to-historical context,
  relationship and event panels, weak/time-inconsistent finding, descriptive
  limitation, and GitHub identity.
- `https://otgos.run.place/` remained HTTP 200 with TLS verification after
  Caddy's hot reload. Its Caddy site block/upstream was not changed.

## Live Validation

Exactly one deliberate public staging refresh was made through
`/api/live-gun`; the committed adapter is limited to one request and zero
retries. The result was successful and returned `fetch_mode=LIVE`, 11 response
records, and 11 complete hourly buckets. The latest complete bucket was
`2026-09-25T08:00:00Z` through `2026-09-25T09:00:00Z`. The price return was
available; flow-imbalance share was unavailable for that bucket. The live
return selected `MIDDLE_90_PERCENT`, and the neutral historical-context logic
passed. The browser-facing field allowlist and sensitive-field scan passed.
No volatile price or flow values are included here.

The page and health/history routes were checked before the live request. Source
inspection confirms page loading and browser refresh do not automatically call
Nansen. The public refresh was the only live Nansen attempt in this task; no
second refresh was made.

## Database and Production Safety

The demo requires no PostgreSQL connection. No production database connection,
DDL, or DML occurred. The production `otgos.run.place` site was not changed or
restarted. No staging database was accessed.

## Tests and Scans

- Offline suite: **315 passed, 6 skipped**.
- `python -m compileall src`: passed.
- `SECRET_SCAN=PASS`.
- `CYRILLIC_SCAN=PASS`.
- `ENV_TRACKED=NO`.

## Request Attempt Count

`NANSEN_API_CALLS_TASK038=1`. This is the single explicit staging refresh;
there were no retries or startup requests.

## Final Commit

The reusable wrapper, tests, deployment documentation, and report are
committed and pushed. The remote readback SHA is recorded in the final status.

## Remaining Blockers

None for staging deployment. The operator can open
`https://otgostest.run.place/` directly. Recording and submission remain
separate operator tasks.

## Architecture Correction: Native OTG Analytics Mode

On 2026-09-25 the deployment requirement was clarified: the staging domain
must remain the existing OTG Analytics application, with Nansen available as
one native analytics mode. The Task 038 Caddy change had routed the entire
staging host to the standalone service on port 8765. The original staging
Streamlit application on port 8504 was verified healthy, and the staging
upstream was restored to `127.0.0.1:8504`; Caddy validation and hot reload
passed. The production host configuration was not changed.

The standalone service remains a loopback-only internal backend. The Nansen
mode was implemented in the separate `Blackpoint133/otg-analytics` repository,
using its existing `mode` query parameter and Analytics dropdown. The public
route is `https://otgostest.run.place/?mode=nansen`; the site reads the
digest-validated historical aggregates and calls the internal live endpoint
only on explicit user refresh. No page-load live request was observed.

One deliberate browser refresh returned a fresh completed-bucket observation
and the `MIDDLE_90_PERCENT` classification; no volatile price or flow values
are recorded here. Production `https://otgos.run.place/` remained reachable
and its configuration/service were left untouched. Detailed implementation
and validation evidence is in the native-mode integration report in the
`otg-analytics` repository.
