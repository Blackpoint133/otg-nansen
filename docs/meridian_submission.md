# Meridian Submission Readiness

Readiness audit date: 2026-09-25. This document records the repository and
read-only staging evidence available on that date. It does not claim that an
entry has been submitted or accepted.

## OFFICIAL_REQUIREMENT_CONFLICT

The [Nansen Meridian campaign page](https://nansen.ai/campaigns/meridian-buildathon)
currently says to make **1,000 API calls**. The later-updated [Nansen Meridian
FAQ](https://release.nansen.ai/help/articles/3540155-nansen-meridian-buildathon-sep-14-27),
updated two days before this audit, says to log **100+ API calls between Sep
14 and Sep 27**, and explicitly excludes calls made before Sep 14. Both pages
give the closing time as Sep 27 at 23:59 UTC. This project does not infer
which source supersedes the other; both thresholds are tracked below.

## DEADLINE

**2026-09-27 23:59 UTC** (exclusive end of the call-count window:
`2026-09-28T00:00:00Z`).

## CALL-COUNT AUDIT

The eligible interval used was `[2026-09-14T00:00:00Z,
2026-09-28T00:00:00Z)`. The actual staging schema is
`nansen.ingestion_runs`. `api_calls` is the most faithful persisted measure of
HTTP request attempts: the ingestion code records the delta in
`requests_attempted`, including failed attempts and retries. `pages_requested`
counts response pages and is not a substitute for request attempts.

Read-only staging evidence: **85 audited attempts** across 81 runs (78 success,
3 failed); successful runs account for 82 attempts and failed runs for 3.
All were `flows` / `smart_money`. Separately, reports explicitly document 32
direct request attempts that predate or bypassed ingestion auditing. These
are counted once only where a report gives an explicit count and execution is
bounded to the eligibility period. This yields a **minimum confirmed total
of 117**. No additional ambiguous request is included. See the Task 035 report
for the reconciliation by task.

| Threshold interpretation | Confirmed calls | Status | Remaining |
|---|---:|---|---:|
| FAQ threshold: 100+ | 117 | Met | 0 |
| Campaign-page threshold: 1,000 | 117 | Not met | 883 |

The status describes documented project calls, not a guarantee of Nansen's
independent quota accounting. No calls were made for this audit or to inflate
a threshold.

## SUBMISSION CHECKLIST

- [ ] Confirm an active Nansen API key is available to the demo operator. Key
  values were not inspected in this audit.
- [x] Call evidence reconciled: at least 100 confirmed in-window attempts.
- [ ] Confirm whether Nansen requires 1,000 attempts; the audited minimum is
  117, so that threshold is not met.
- [x] Public GitHub repository:
  [Blackpoint133/otg-nansen](https://github.com/Blackpoint133/otg-nansen).
- [ ] Working judge-facing demo with live Nansen data visibly driving a
  meaningful part of the experience.
- [ ] Silent 30–60 second screen recording (the FAQ calls for 30–60 seconds).
- [ ] X post tagging `@nansen_ai` and linking the public GitHub repository.
- [ ] Submit the entry form with email, X post URL, and GitHub URL.

## JUDGING CHECKLIST

The campaign gives equal weight to Data Integration, Functionality &
Workability, Creativity & Originality, and Documentation & Submission.

| Criterion | Current repository evidence | Remaining gap |
|---|---|---|
| Data Integration | Real Avalanche `$GUN` Smart Money ingestion and a 12,336-hour aligned historical dataset; Nansen price and flow-count fields drive fixed, preregistered analysis. | No judge-facing current/live Nansen view exists yet. |
| Functionality & Workability | Tested ingestion/backfill tools, read-only analysis runner, committed aggregate results. | No integrated visual demo to run end to end. |
| Creativity & Originality | OTG marketplace activity is compared with Avalanche `$GUN` Smart Money observations using explicit cross-chain separation and a price-shock summary. | The specific use case is implemented as research artifacts, not yet presented as a usable product surface. |
| Documentation & Submission | Updated README, analysis report, this checklist, public repository. | Demo, recording, X post, and entry form remain pending. |

## CURRENT PROJECT EVIDENCE

- Task 033 ratified the staging-only joined hourly foundation.
- Task 034 preregistered its analysis before reading the source snapshot and
  retained all 48 relationship cells and 24 event-summary cells.
- The committed result reports weak, time-inconsistent price-return
  associations. Flow-imbalance-share estimates were too sparse under the
  frozen rules. This is not a predictive or causal result.
- The Task 034 report, methodology, CSV summaries, and summary JSON are
  committed under `DEV/` and `docs/`.
- The GitHub repository is public. This audit found no live-demo UI, charting
  surface, public web integration, or integrated one-command presentation
  flow in this repository.

## GAPS

1. Build a small read-only presentation surface with one live Nansen-backed
   component and the committed historical analysis.
2. Exercise the demo using a valid local API key and document startup in the
   README; do not expose the key in the browser or logs.
3. Record the required silent 30–60 second walkthrough.
4. Publish the X post and submit the entry form.
5. Resolve the 100 versus 1,000 threshold with Nansen or retain both
   interpretations when making any eligibility statement.

The next code milestone is specified in
[`meridian_demo_script.md`](meridian_demo_script.md). No API call was made to
complete this audit.

## TASK 036 STATUS ADDENDUM

Task 035 remains the historical audit snapshot above. After it, Task 036 added
one separately documented live demo validation request on 2026-09-25 UTC. The
documented project minimum is therefore **118 in-window attempts** (117 from
the Task 035 minimum plus this one request). This is project-side evidence and
does not guarantee that Nansen's internal quota counter records the same
total. The 100+ interpretation is met by this documented minimum; the 1,000
interpretation remains unmet. The local demo now has a working read-only
presentation surface and passed a one-request live validation; the recording,
X post, and entry form remain pending.
