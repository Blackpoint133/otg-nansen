# Task 021: Historical flow granularity and identity probe

## OBJECTIVE

Determine whether Nansen TGM Flows resolution depends on requested range
width and assess whether current flow identity can collide across bucket
intervals.

## STARTING_STATE

Starting `main` was `54a738db58ea430b8adf02b2c41420e329dc646e`; the worktree was
clean. Default tests passed before and after the diagnostic. No application
source was changed.

## TASK020_EVIDENCE

Task 020 retained 29 rows and 29 distinct timestamps in its 30-day query. A
read-only UTC-calendar reconstruction found those timestamps are daily
midnights from 2025-04-26 through 2025-05-24, not April 25 through May 24 as
the original report's local-time conversion stated. An addendum was appended
to the Task 020 report to correct that interpretation without rewriting its
history. The one absent calendar date is 2025-04-25.

## OFFICIAL_DOCUMENTATION_RECHECK

The [current official TGM Flows documentation](https://docs.nansen.ai/api/token-god-mode/flows)
explicitly states hourly snapshots for ranges of seven days or less and daily
snapshots for longer ranges. It defines `date` as the inclusive start and
`bucket_end` as the exclusive end of an aggregation bucket; request `date.to`
is an inclusive cutoff. `is_complete=false` when the upper cutoff truncates a
bucket or the bucket is live; this flag describes request-window coverage,
not underlying data finality. For non-Hyperliquid chains, the lower cutoff is
aligned to bucket start. `warnings` is optional; the docs specifically note
that non-exchange labels have null CEX/DEX breakdowns and a warning entry.

- Documented granularity: hourly for range <=7 days; daily for range >7 days.
- Range-dependent resolution: explicitly documented.
- Bucket-end semantics: exclusive UTC bucket end; `date` is inclusive bucket
  start.
- Warning semantics: optional warnings; documented non-exchange breakdown
  warning. No range/truncation warning semantics or maximum flows range are
  explicitly documented.

## READ_ONLY_STAGING_BASELINE

All staging inspection connections targeted `server_otg_staging` with
`default_transaction_read_only=on`. The Task 020 window had 29 rows and 29
distinct timestamps. All dates were midnight UTC; no `bucket_end` was null;
all bucket durations were 24 hours. The 30-day calendar reconstruction found
one missing date: 2025-04-25. The recent September window had 23 rows. The
checkpoint remained at 2026-09-20T23:59:59Z, run
`1d535cae-c74b-49ef-bd5e-0c46f2301a3d`.

## MISSING_DATE_DISCOVERY

`MISSING_CALENDAR_DATE_COUNT=1`; missing date: `2025-04-25`. The date
reconstruction uses UTC instants, not the PostgreSQL session's Pacific display
timezone.

## PILOT_BUCKET_STRUCTURE

The retained wide-query buckets were 29 midnight UTC dates with duration
distribution `24 hours: 29`; `bucket_end` null count was 0.

## LIVE_CALL_BUDGET

One Nansen client was configured with `max_calls=2`, `max_retries=0`,
`timeout_seconds=120`, `page_size=1000`, `max_pages=1`. Exactly two direct
requests were made; no paginator or additional page was used.

## REPRESENTED_DAY_REQUEST

The accepted Task 020 report's presumed represented date, April 25, was
actually absent after correct UTC conversion. The represented probe was
therefore the earliest date actually present, `2025-04-26`; the missing-date
probe was `2025-04-25`. Both used the same one-day request shape, page 1,
`per_page=1000`, and ascending date order.

The represented response had top-level keys `data`, `pagination`, and
`warnings`; it was final on page 1. All 23 records normalized. They had 23
distinct timestamps, all non-midnight UTC, with 23 complete, zero incomplete,
zero null-completeness, zero null `bucket_end`, and duration `1 hour: 23`.
Earliest/latest structural timestamps were 2025-04-26T01:00:00Z and
2025-04-26T23:00:00Z.

## REPRESENTED_DAY_WARNINGS

Warnings were present (count 1). Sanitized keyword classification was
`other`: no truncation, aggregation, downsampling, partial/incomplete, or
unsupported-range category was detected. Raw warning text was not retained.
The official docs describe a warning for null CEX/DEX breakdowns on
non-exchange labels, but the precise live warning text was intentionally not
preserved for direct comparison.

## REPRESENTED_DAY_STRUCTURE

The persisted wide-query timestamp set for April 26 contained the daily
midnight bucket. The one-day query returned 23 additional hourly timestamps
from 01:00Z through 23:00Z. Classification:
`REPRESENTED_TIMESTAMP_SET_RELATION=NARROW_QUERY_HAS_ADDITIONAL_TIMESTAMPS`.
No one-day response row shared the persisted midnight `date`, so
`SAME_DATE_DIFFERENT_BUCKET_END=NO` for this observed date.

## WIDE_VS_NARROW_COMPARISON

The wide request's row for the represented day was one 24-hour bucket; the
narrow request returned 23 one-hour buckets. This is direct live evidence of
range-dependent granularity and different timestamp sets. The probe did not
observe a same-`date`, different-`bucket_end` pair because the narrow response
contained no midnight record.

## MISSING_DAY_REQUEST

The direct April 25 request was final on page 1 and returned 23 records; all
normalized successfully. Thus a date omitted by the wider 30-day response was
non-empty when queried alone. This establishes a response difference, not
data loss or an explanation for Nansen's aggregation behavior.

## MISSING_DAY_WARNINGS

Warnings were present (count 1); sanitized classification was `other` under
the same categories described above. Raw warning text was not retained.

## MISSING_DAY_STRUCTURE

The response had 23 distinct non-midnight timestamps, all complete with
non-null `bucket_end` and one-hour duration. The structural range was
2025-04-25T01:00:00Z through 2025-04-25T23:00:00Z. The missing calendar day
classification is `NARROW_QUERY_NONEMPTY`.

## GRANULARITY_CLASSIFICATION

`ADAPTIVE_OR_RANGE_DEPENDENT`, explicitly supported by both the current
official documentation and the observed 24-hour versus one-hour buckets.
Separately, the 30-day result omitted a calendar date that returned hourly
records when directly queried. The reason for that omission is not inferred.

## FLOW_IDENTITY_COLLISION_ANALYSIS

`SAME_DATE_DIFFERENT_BUCKET_END=NO` in the represented-day comparison.
`FLOW_IDENTITY_COLLISION_RISK=INCONCLUSIVE`: the narrow probe had no midnight
hourly row to compare against the persisted daily bucket at midnight. The
officially documented adaptive resolution establishes different bucket
widths but these two probes do not prove an identical `date` with different
ends. Since current `flow_key` excludes bucket bounds, broader backfill is
`BROADER_BACKFILL_SAFE=NO` until a separately reviewed identity decision
rules out collisions across dates/windows.

## MISSING_DATE_CLASSIFICATION

`NARROW_QUERY_NONEMPTY`. The April 25 records were observed only in the
one-day request; no data-loss cause is assigned to their absence in the
30-day result.

## PERSISTED_STATE_VERIFICATION

Read-only post-probe inspection confirmed Task 020 remained at 29 rows, the
recent September window remained at 23 rows, and the checkpoint remained at
2026-09-20T23:59:59Z referencing Task 019 run
`1d535cae-c74b-49ef-bd5e-0c46f2301a3d`. `PERSISTED_STATE_UNCHANGED=PASS`.
Database reads only; writes=0, DDL=0, migration not executed.

## RESOURCE_OBSERVATION

Before probes: CPU 45%, available RAM 5,004,424 KB, committed memory
21,061,255,168 of 33,272,041,472 bytes. After probes: CPU 35%, available RAM
5,315,040 KB, committed memory 20,775,571,456 of 33,272,041,472 bytes. No
sustained pressure was observed; stability passed.

## DEFAULT_TESTS

`pytest -q`: 140 passed, 5 skipped before and after. Default tests made zero
live Nansen calls and zero PostgreSQL connections.

## SECURITY_CHECK

No credentials, headers, raw warning text, raw records, individual flow keys,
wallet identities, transaction hashes, or metric values are included. Secret
scan: PASS. Tracked `.env`: NO.

## CYRILLIC_CHECK

PASS.

## FILES_CHANGED

- `DEV/reports/020_deep_historical_flow_pilot/report.md` (timestamp
  reconciliation addendum)
- `DEV/reports/021_historical_flow_granularity_probe/report.md`
- `docs/analytics_methodology.md`
- `docs/nansen_api.md`

No application source or schema was changed.

## RISKS

Nansen documents range-dependent resolution. The 30-day response omitted a
calendar day that returned records under a narrow request. Same-date bucket
collision was not observed, but remains inconclusive because no midnight
hourly record appeared in the represented probe. Since current identity
excludes `bucket_end`, broad backfill could risk resolution collisions or
refreshing a different aggregate under an existing identity; keep it blocked
pending key/schema review.

## NEXT_RECOMMENDED_TASK

Review flow identity semantics against adaptive bucket resolution. Decide
whether `bucket_end` or an explicit resolution dimension belongs in logical
identity before any broader historical ingestion. Do not start Task 022 or a
backfill automatically.
