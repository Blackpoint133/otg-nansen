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
identity, allowing distinct resolutions to coexist. Staging migration is
pending; broader backfill remains unauthorized until that migration and its
verification complete. Any future finite backfill must choose request window
widths according to desired resolution, and analytics must retain and interpret
the bucket interval rather than assume uniform hourly history.

Chain, timezone, missing-date, bucket-resolution, and sample-size diagnostics
must be retained with every future analysis. Align only observations whose
bucket intervals are understood. No causal or predictive claim is permitted
from a simple before/after comparison.
