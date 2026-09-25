# Task 037: Submission Lock and Rehearsal Package

## OBJECTIVE

Reconcile current submission documentation with the accepted Task 036 demo,
add a safe Windows launch helper, and prepare the operator's recording and
submission materials. No analytics, ingestion, or Task 034 result was changed.

## STARTING_STATE

- Starting main: `e7d6dae13dfadba72295de0c432ae62cc453fa67`.
- Working tree was clean and local main matched `origin/main`.
- Task 036 demo and its one-request live validation were accepted inputs.

## BASELINE_TESTS

Before edits: **308 passed, 6 skipped**. No Nansen API or PostgreSQL call was
made by the test suite.

## DOCUMENTATION_RECONCILIATION

Removed current-state contradictions while preserving Task 035's historical
audit figures as a dated snapshot. The current readiness section now reflects
the local demo, live validation, implemented historical panels, and remaining
operator steps. The official 100+ versus 1,000 threshold conflict remains
explicit and unresolved.

## README_STATUS

README now says ingestion, canonical hourly history, Task 033 foundation,
Task 034 analysis, and the local live demo are implemented. It links the
one-command Windows launcher, gives the local URL, explains explicit refresh
and in-memory caching, and states that recording and submission remain
operator tasks. It makes no public-deployment, eligibility, prediction, or
causality claim.

## SUBMISSION_CHECKLIST_STATUS

The current checklist marks the public repository, working local demo, live
integration validation, historical relationship/event panels, and README
instructions complete. Recording, X post, final form submission, and possible
threshold clarification remain open. The current project-documented minimum
is 118; the 100+ reading is met and the 1,000 reading is not. The document
does not claim Nansen independently confirmed the count.

## JUDGING_CRITERIA_STATUS

The current judging map ties Data Integration to real Avalanche `$GUN` Smart
Money data driving both live and historical panels; Functionality to the
working local UI, explicit refresh, and committed artifacts; Creativity to
OTG marketplace context and historical price-shock responses; and
Documentation to the README, methodology, reports, storyboard, and submission
materials. Recording and final submission remain pending. Weak and
time-inconsistent results are described without promotion into predictive
claims.

## WINDOWS_LAUNCHER

Added `scripts/run_meridian_demo.ps1`. It fails clearly if Python or a
non-empty `NANSEN_API_KEY` is unavailable, never prints the key, sets this
process's `PYTHONPATH`, and launches `python -m otg_nansen.demo_app --serve`.
The launcher prints only the local URL during normal startup and suppresses
the server's stdout banner; errors remain visible on stderr. It does not open
a browser, call Nansen, access PostgreSQL, or write credentials. Static tests
check these properties; a no-key guard invocation also exited before starting
the app.

Launch command: `.\scripts\run_meridian_demo.ps1`

Local URL: `http://127.0.0.1:8765/`

## OFFLINE_DEMO_SMOKE

Started the committed handler on loopback with an injected offline live
provider. `/`, `/demo.js`, `/demo.css`, `/api/health`, and `/api/history` all
returned 200. The smoke made zero live-provider calls. The served page contains
the live `$GUN` Smart Money card, historical relationship and event panels,
descriptive limitation, and GitHub identity. The server shut down cleanly.
Result: **PASS**.

## RECORDING_CHECKLIST

Added `docs/meridian_recording_checklist.md` with operator steps, one deliberate
refresh, a 45-second screen sequence, privacy rules, and post-capture review.
The supported recording duration is 30-60 seconds.

## X_POST_DRAFT

Added one primary and one alternate English post in
`docs/meridian_x_post_draft.md`. Both tag `@nansen_ai`, use placeholders for
the GitHub and video URLs, and describe results without causal or predictive
claims. The drafts are within the intended X length range with ordinary
project/video URLs substituted. No post was published.

## SUBMISSION_COPY_BANK

Added `docs/meridian_submission_copy.md` with project name, one-line and
approximately 70-120 word descriptions, key technical facts, and URL
placeholders. It is labeled a copy bank rather than a form reproduction. No
entry form was submitted.

## FINAL_TESTS

Final offline suite: **312 passed, 6 skipped**. `python -m compileall src`
passed. Tests do not connect to PostgreSQL or call Nansen. The offline demo
smoke used the fake provider only.

## NANSEN_API_PROOF

`NANSEN_API_CALLS_TASK037=0`. No live Nansen request was made.

## DATABASE_PROOF

`POSTGRES_CONNECTIONS_TASK037=0`. No production or staging database
connection, DDL, or DML occurred.

## SECURITY_CHECK

Changed files were scanned for credential-like values. No API key, database
password, GitHub token, raw Nansen response/warning, wallet address, or
transaction hash was added. `.env` is not tracked. `SECRET_SCAN=PASS`;
`ENV_TRACKED=NO`.

## CYRILLIC_CHECK

Changed documentation and code are English-only. `CYRILLIC_SCAN=PASS`.

## FILES_CHANGED

- `README.md`
- `docs/meridian_submission.md`
- `docs/meridian_demo_script.md`
- `docs/meridian_recording_checklist.md`
- `docs/meridian_x_post_draft.md`
- `docs/meridian_submission_copy.md`
- `scripts/run_meridian_demo.ps1`
- `tests/test_demo_launcher.py`
- `DEV/reports/037_submission_lock/report.md`

No analytics source, Nansen ingestion, or Task 034 result artifacts changed.

## REMAINING_OPERATOR_ACTIONS

1. Run the demo.
2. Record a 30-60 second video.
3. Review and publish the X post.
4. Submit the entry form.
5. Optionally clarify the official 100-versus-1,000 threshold with Nansen.
