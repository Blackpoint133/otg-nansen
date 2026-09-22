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

Phase 0B recommends using hourly Nansen flow observations and event-level DEX
trades where available, then aligning them to the existing OTG sales and token
price timestamps. Chain, timezone, missing-data, and sample-size diagnostics
must be retained with every future analysis. No causal or predictive claim is
permitted from a simple before/after comparison.
