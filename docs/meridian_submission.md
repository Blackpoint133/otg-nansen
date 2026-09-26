# Meridian Submission Readiness

Current status: the Nansen experience is live in production OTG Analytics. This document retains the historical Task 035 call audit and records current submission preparation. It does not claim that an entry has been submitted, accepted, or is award-eligible.

## Official Requirement Conflict

Reviewed official materials differ. The [Nansen Meridian campaign page](https://nansen.ai/campaigns/meridian-buildathon) states a 1,000 API-call threshold. The [Meridian FAQ](https://release.nansen.ai/help/articles/3540155-nansen-meridian-buildathon-sep-14-27) states 100+ calls logged between September 14 and September 27 and excludes earlier calls. Both list September 27, 2026 at 23:59 UTC as the deadline. This project does not infer which source supersedes the other.

## Task 035 Historical Call Audit

The eligible interval audited in Task 035 was `[2026-09-14T00:00:00Z, 2026-09-28T00:00:00Z)`. Read-only staging evidence identified `nansen.ingestion_runs.api_calls` as the persisted request-attempt measure. It records the delta in `requests_attempted`; `pages_requested` is not a substitute.

The Task 035 audit found 85 persisted attempts across 81 runs (78 successful, 3 failed); successful runs accounted for 82 attempts and failed runs for 3. All audited rows were `flows` / `smart_money`. It also reconciled 32 explicitly documented direct attempts not represented by those rows. Its minimum confirmed total was 117. These figures are the historical Task 035 snapshot and have not been rewritten.

## Current Documented Call Minimum

Task 036 separately documented one live demo validation request on September 25, 2026. The conservative project-documented minimum is **118 in-window attempts**: the Task 035 minimum of 117 plus that request. This does not claim that Nansen independently confirmed the count in its quota system. Later scheduled production requests are not added without durable audit evidence.

| Threshold interpretation | Project-documented minimum | Status | Remaining |
|---|---:|---|---:|
| FAQ threshold: 100+ | 118 | Met on documented minimum | 0 |
| Campaign-page threshold: 1,000 | 118 | Not met on documented minimum | 882 |

No synthetic or quota-padding traffic was generated.

## Current Submission Checklist

- [x] Public GitHub repository: [Blackpoint133/otg-nansen](https://github.com/Blackpoint133/otg-nansen).
- [x] Production Nansen mode integrated into OTG Analytics: [open the live product](https://otgos.run.place/?mode=nansen).
- [x] Live Nansen integration with shared automatic hourly refresh.
- [x] Historical relationship and price-shock response visualizations.
- [x] Production README and user Guide.
- [x] Visible “Data provided by Nansen” attribution in the product.
- [ ] Record the final demo video, if not already completed.
- [ ] Publish the X post tagging `@nansen_ai` with the GitHub link, if not already completed.
- [ ] Submit the final entry form, if not already completed.
- [ ] Optionally ask Nansen to clarify the 100+ versus 1,000 threshold discrepancy.

The documented minimum meets the FAQ's 100+ interpretation and does not meet the campaign page's 1,000 interpretation. This is not a guarantee of Nansen's internal quota accounting or a statement of award eligibility.

## Current Judging-Criteria Mapping

| Criterion | Current project evidence | Remaining submission work |
|---|---|---|
| Data Integration | Avalanche `$GUN` Smart Money data drives live market context and the historical comparison with OTG marketplace activity. | Show the live product clearly in the recording. |
| Functionality & Workability | The public [production Nansen mode](https://otgos.run.place/?mode=nansen) provides shared live context, historical visualizations, and a user Guide. | Record and submit the working product. |
| Creativity & Originality | OTG marketplace reactions are contextualized against Nansen `$GUN` market and Smart Money observations, with the weak result retained as observed. | Explain the use case without suggesting a trading signal. |
| Documentation & Submission | README, methodology, production deployment documentation, demo storyboard, recording checklist, X draft, and submission copy bank are available. | Complete any outstanding recording, X post, and form steps. |

## Current Project Evidence

- The accepted historical foundation contains 12,336 aligned hourly observations.
- The preregistered analysis retains all 48 relationship cells and 24 event-summary cells.
- Historical hourly price-return associations were weak and time-inconsistent. Flow-imbalance-share history was too sparse under the fixed analysis rules. Results are descriptive and do not establish prediction or causation.
- The production Nansen mode displays current $GUN context, Smart Money flow context, historical OTG comparisons, and the concise Market Takeaway. Live observations are refreshed through a shared server-side schedule; visitors do not manually refresh or trigger per-visit Nansen calls.
- The product displays the last successful data-update time and visible Nansen attribution.

## Remaining Submission Items

1. Complete and review the final recording if it has not already been recorded.
2. Review and publish the X post, then submit the final entry form if those steps remain outstanding.
3. Optionally request clarification of the official API-call threshold discrepancy.

See the [production demo storyboard](meridian_demo_script.md), [recording checklist](meridian_recording_checklist.md), [X post draft](meridian_x_post_draft.md), and [submission copy bank](meridian_submission_copy.md).
