# Meridian Submission Readiness

Updated 2026-09-25. This document separates the Task 035 point-in-time audit
from the current Task 036/037 readiness state. It does not claim that an entry
has been submitted, accepted, or is award-eligible.

## Official Requirement Conflict

The [Nansen Meridian campaign page](https://nansen.ai/campaigns/meridian-buildathon)
states a 1,000 API-call threshold. The [Meridian FAQ](https://release.nansen.ai/help/articles/3540155-nansen-meridian-buildathon-sep-14-27)
states 100+ calls logged between September 14 and September 27 and excludes
earlier calls. Both sources list September 27, 2026 at 23:59 UTC as the
deadline. This project does not infer which source supersedes the other; both
thresholds remain visible below.

## Task 035 Historical Call Audit

The eligible interval audited in Task 035 was
`[2026-09-14T00:00:00Z, 2026-09-28T00:00:00Z)`. Read-only staging evidence
identified `nansen.ingestion_runs.api_calls` as the persisted request-attempt
measure. It records the delta in `requests_attempted`; `pages_requested` is
not a substitute.

The Task 035 audit found 85 persisted attempts across 81 runs (78 successful,
3 failed); successful runs accounted for 82 attempts and failed runs for 3.
All audited rows were `flows` / `smart_money`. It also reconciled 32 explicitly
documented direct attempts not represented by those rows. Its minimum
confirmed total was 117. These figures are retained as the historical Task
035 snapshot and have not been rewritten.

## Current Documented Call Minimum

Task 036 separately documented one live demo validation request on September
25, 2026. The current project-side minimum is therefore **118 in-window
attempts**: the Task 035 minimum of 117 plus that one request. This is not a
claim that Nansen independently confirmed the count in its quota system.

| Threshold interpretation | Project-documented minimum | Status | Remaining |
|---|---:|---|---:|
| FAQ threshold: 100+ | 118 | Met | 0 |
| Campaign-page threshold: 1,000 | 118 | Not met | 882 |

No synthetic or quota-padding traffic was generated.

## Current Submission Checklist

- [ ] Ensure the demo operator has an active Nansen API key configured locally.
      The key must not be committed or shown in the recording.
- [x] Public GitHub repository:
      [Blackpoint133/otg-nansen](https://github.com/Blackpoint133/otg-nansen).
- [x] Working local judge-facing demo; live Nansen integration was validated
      with one bounded request.
- [x] Historical relationship visualization implemented from committed Task
      034 aggregate results.
- [x] Historical price-shock event-response visualization implemented.
- [x] README and local startup instructions present.
- [ ] Record the silent 30-60 second demo.
- [ ] Publish an X post tagging `@nansen_ai` with the repository link.
- [ ] Submit the entry form with the required contact and link fields.
- [ ] Clarify whether the operative threshold is 100+ or 1,000 if Nansen
      provides authoritative clarification.

The 100+ interpretation is met by the documented project minimum. The 1,000
interpretation is not met. Neither status is a guarantee of Nansen's internal
quota accounting or a statement of award eligibility.

## Current Judging-Criteria Mapping

| Criterion | Current repository evidence | Remaining work |
|---|---|---|
| Data Integration | Real Avalanche `$GUN` Smart Money data drives the live observation and the committed historical price/flow analysis; OTG marketplace activity is a separate native-GUN series. | Record the demo so judges can review the integrated experience. |
| Functionality & Workability | Local UI, explicit live refresh, bounded request, in-memory cache, and committed digest-validated historical artifacts. No PostgreSQL is required to run the demo. | Operator should rehearse the startup and capture sequence. |
| Creativity & Originality | OTG marketplace behavior is contextualized against Nansen `$GUN` Smart Money observations and the historical price-shock response summary. | Present the use case clearly in the recording without suggesting a trading signal. |
| Documentation & Submission | README, methodology, task reports, demo storyboard, recording checklist, X draft, and submission copy bank are present. | Recording, X post, and final entry-form submission remain pending. |

## Current Project Evidence

- Task 033 ratified the 12,336-hour staging-only hourly foundation.
- Task 034 preregistered its methods and retained all 48 relationship cells
  and 24 event-summary cells.
- Task 034 found weak, time-inconsistent hourly price-return associations.
  Flow-imbalance-share analysis was too sparse under its fixed rules. These
  findings are descriptive and do not establish prediction or causation.
- Task 036 added a local live-data demo. Its explicit refresh makes a bounded
  Nansen request; current live return selects the matching historical shock
  context using thresholds loaded from digest-validated Task 034 artifacts.
- Task 036 validated the adapter with one live request. Its local route smoke
  test used an offline fake provider.
- Task 037 adds a Windows launch helper and operator-facing recording and
  submission materials; it makes no live API request.

## Remaining Gaps

1. Operator must launch and record the local demo using the checklist.
2. Operator must review and publish the X post, then submit the entry form.
3. Official sources still conflict between 100+ and 1,000 calls; clarify with
   Nansen if possible.
4. The demo is local only and has not been publicly deployed.

For the exact local steps, see
[`meridian_recording_checklist.md`](meridian_recording_checklist.md). Draft
materials are in [`meridian_x_post_draft.md`](meridian_x_post_draft.md) and
[`meridian_submission_copy.md`](meridian_submission_copy.md).
