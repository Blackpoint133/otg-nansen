# Analytics methodology

The intended analytical principle is to compare historical `$GUN` events with
subsequent Off The Grid market reactions. Sample size and uncertainty must be
reported; correlation does not establish causation. Thresholds must be
data-driven and are not defined yet.

The normalization boundary does not define event thresholds or causal claims.
It preserves source flow and trade semantics, rejects malformed required
records, represents empty flow datasets as empty lists, and normalizes all
accepted timestamps to UTC. Monetary, token, supply, and price values use
Decimal rather than binary floating-point arithmetic.

Nansen's current TGM Flows documentation states that ranges of seven days or
less return hourly snapshots, while longer ranges return daily snapshots.
`date` is the inclusive bucket start and `bucket_end` the exclusive end; the
request's `date.to` is an inclusive cutoff. `is_complete` describes request
window coverage, not whether the underlying observation is final. See the
[official Flows contract](https://docs.nansen.ai/api/token-god-mode/flows).

Task 021 live evidence demonstrated this range-dependent resolution for
Avalanche `$GUN` `smart_money`: the retained 30-day query produced daily
midnight buckets, while one-day direct queries produced hourly buckets for
the tested days. The wide query omitted one calendar date that returned
records under a direct one-day query. For the represented day, the narrow
response did not include the same midnight timestamp as the persisted daily
bucket, so a same-date/different-`bucket_end` collision was not observed;
identity collision risk was inconclusive from the probe itself. The Task 022
design therefore uses both bucket start and exclusive bucket end in persisted
identity, allowing distinct resolutions to coexist. Migration 003 and the
bucket-aware re-key were applied and verified on staging only; broader
backfill remains unauthorized. Any future finite backfill must choose request window
widths according to desired resolution, and analytics must retain and interpret
the bucket interval rather than assume uniform hourly history.

Chain, timezone, missing-date, bucket-resolution, and sample-size diagnostics
must be retained with every future analysis. Align only observations whose
bucket intervals are understood. No causal or predictive claim is permitted
from a simple before/after comparison.

Task 023's warning boundary prevents analyzing or retaining flow pages with
unrecognized source warnings. The verified benign category concerns only the
documented null CEX/DEX breakdown for non-exchange labels. Warning summaries
contain no source text or response fields. Since the authorized live warning
revalidation classified as `UNKNOWN`, broader historical ingestion remains
blocked pending clarification.

Task 023F later adopts the exact recorded warning fingerprint, limited to Flows `smart_money` and guarded by null CEX/DEX breakdown fields on every normalized result row. The warning text is not retained, and changed wording remains unknown. This source-specific boundary does not establish other labels or broader historical coverage.

Task 024 validated the documented hourly resolution for one seven-day Avalanche `smart_money` request: 167 hourly buckets were retained across all seven UTC calendar dates, alongside six unchanged daily buckets. One hourly timestamp was absent; this does not imply no token activity for that interval. The warning policy and sanitized audit worked for this run, and the later high-water checkpoint stayed unchanged. This single pilot does not establish full coverage or authorize systematic backfill.

Task 025 compared the retained hourly set for 2025-04-25 through 2025-05-01 UTC with one read-only Flows request shifted one hour earlier at both bounds. The shifted response returned the previously missing 2025-04-25T00:00Z bucket but not a bucket at its own 2025-04-24T23:00Z lower bound; overlap was 166 identities with one identity exchanged at each edge. This supports a lower-bound omission classification for this tested range, while differing from the current official documentation's statement that non-Hyperliquid requests return the full first bucket. Naive non-overlapping weekly windows are unsafe for complete hourly coverage under this observed behavior. Further boundary review is needed before systematic ingestion, and no cause beyond the observed request-boundary relation is inferred.

Task 026 introduces a deterministic 74-unit plan for the desired 12,336 hourly bucket starts from 2025-04-25T00:00:00Z through 2026-09-20T23:00:00Z. Each unit covers at most 167 desired starts and requests one hour before its coverage start. Desired coverage is contiguous and non-overlapping; request windows share the prior unit's final hourly bucket. The response validator distinguishes absent source buckets from a missing request-boundary bucket and reports structure without treating a missing observation as a planning failure. Historical completion and resumption use exact-window successful warning-audited runs, not the existing high-water checkpoint. No live backfill was executed.

Task 027 completed the first three planned units through 2025-05-15T20:00:00Z coverage. Each unit returned 167 records and all 167 desired hourly bucket identities were retained. The combined set contains 501 unique desired hourly starts; 167 pre-existing identities were reused and 334 added. Daily buckets remained unchanged alongside hourly buckets. Each audit retained only the approved sanitized warning category. This is a bounded three-unit validation; it does not establish full historical coverage or imply that a missing source bucket means inactivity. Exact-window audits, not the later high-water checkpoint, establish resumability. Unit 4 is next; the remaining 71 units were not executed.

Task 028 resumed at unit 4 using exact-window successful warning-audited runs and completed units 4–13. All 1,670 desired hourly natural bucket identities for those units are present; none were present before the batch. The requests each returned and normalized 167 records, and every per-unit audit used the approved sanitized warning category. The pre-existing daily identity digest and later checkpoint remained unchanged. Progress is 13 complete / 61 pending, with unit 14 next. This ten-unit batch remains bounded evidence and does not establish full historical coverage or infer activity from source omissions.

Task 029's generic runner completed desired coverage for units 14–28, but stopped at unit 28 on a false-positive local-time comparison around the daylight-saving fold. A read-only UTC-normalized check confirms all 167 desired starts for unit 28 and 2,505 starts across attempted units 14–28. The UTC comparison fix has a regression test. The runner did not request units 29–33; exact-window audit progress is not evidence that the authorized 20-unit batch ran to completion.

Task 029R completed the five units left pending by that stopped invocation. Units 14–33 now contain all 3,340 desired hourly identities, verified using UTC-canonical bucket keys. This is bounded retained coverage only; it does not establish coverage outside these canonical windows or infer activity from absent source observations. Unit 34 is next.

Task 030R found that only units 34–45 of the authorized 34–53 range have complete desired coverage: 2,004 of 3,340 desired hourly identities. Unit 46 remains pending after two failed one-attempt requests; units 47–53 were not attempted. This is partial historical coverage, not a completed batch. The high-water checkpoint remains unchanged.

Task 030D diagnosed the two unit 46 failures as HTTP 403 `NansenHTTPError` responses. Their safe summaries indicate an insufficient-credit condition. Current official Nansen guidance marks the credit condition and forbidden access non-retryable; 403 is also excluded from the committed client's retryable status set. No third call was authorized or made. Unit 46 remains blocked pending account/credit resolution; units 47–53 remain pending.

Task 030K validated the operator-replaced local key with one authorized unit 46 request. The exact-window run succeeded and all 167 desired hourly identities are present. Progress is 46 complete / 28 pending / 0 ambiguous; unit 47 is next and was not executed. Production remains untouched.

Task 030F completed units 47–53 after Task 030K's successful unit 46 recovery. The replacement key resolved the unit 46 access/credit blocker for that request. The full original Task 030 range, units 34–53, now has 3,340/3,340 desired hourly identities and 20 successful exact-window unit runs; earlier failed unit 46 audits remain in history. Progress is 53 complete / 21 pending / 0 ambiguous, unit 54 is next, and the checkpoint remains unchanged. Production was untouched.
