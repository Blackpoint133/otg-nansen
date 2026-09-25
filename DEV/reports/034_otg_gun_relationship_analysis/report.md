# Task 034: OTG and GUN Relationship Analysis

## OBJECTIVE

Report the preregistered descriptive relationship analysis of Avalanche Nansen `$GUN` observations and OTG marketplace aggregates. No causal, predictive, or deployment claim is made.

## PREREGISTERED_ANALYSIS_SHA

`01d77700c0768d0f972f2877f504a8c567c81fae` was pushed and verified before the staging snapshot was read. The frozen source, tests, and methodology were not changed after that point.

## OFFLINE_TESTS

Baseline before implementation: 265 passed, 6 skipped. Preregistration suite: 281 passed, 6 skipped. Final suite after analysis: 281 passed, 6 skipped. The test suite used no PostgreSQL, live RPC, or Nansen connection.

## SOURCE_SNAPSHOT

- Source: `server_otg_staging.nansen.otg_nansen_hourly`, read with the committed read-only connection and full aligned-column read path.
- Connection verification: `current_database=server_otg_staging`; `transaction_read_only=on`.
- Rows: 12,336. UTC minimum: `2025-04-25T00:00:00Z`. UTC maximum: `2026-09-20T23:00:00Z`.
- Missing, duplicate, unexpected, or out-of-order canonical identities: 0.
- Analysis source digest: `9ac2109500aea84160555928d297b7efdcd551e23f3259bee5482a1ae5ed19f8` (PASS).
- Nansen source identity baseline: `73291cb74398292cc1ed38f728e8c686973920fe7c18701c12bea154eb7335a7` (the analysis read did not access `nansen.flows` separately).

## METHODOLOGY_FREEZE

Methodology version: `034-preregistered-v1`. The implementation, synthetic tests, and Task 034 preregistration document were committed before any real result was observed. No methodology, source, or test edit followed the preregistration commit.

## DRIVERS

- `gun_price_return_1h`.
- `flow_imbalance_share = flow_count_imbalance / flow_count_total` when total is positive; otherwise NULL.

## MARKET_OUTCOMES

Exactly three outcomes were used: `market_trade_tx_count`, `market_native_gun_amount_truncated`, and `market_unique_buyers`. Native GUN marketplace values and Avalanche Nansen values remain separate series.

## OUTCOME_TRANSFORMS

Primary: `log1p(value)` minus the full-sample median for the same UTC hour-of-week. All 168 groups were represented for each outcome. Sensitivity: one-hour `delta_log1p_1h`; the first canonical outcome is NULL. No winsorization or observation deletion was performed.

## FIXED_LAGS

Exactly 0, 1, 6, and 24 hours; driver at `t-k` is paired with outcome at `t`. Positive lag means the Nansen-side observation precedes the market outcome.

## RELATIONSHIP_MATRIX_COMPLETENESS

All 48 fixed cells are present. Spearman rho is primary; Pearson r is secondary. No p-values are calculated. Undefined coefficients remain NULL. CSV values retain full deterministic precision; the table below rounds only for display to six decimal places.

| Driver | Outcome | Outcome form | Lag h | n | Spearman rho | Pearson r | Defined blocks | Block rho median [min, max] | Block + / - / 0 |
|---|---|---|---:|---:|---:|---:|---:|---|---:|
| flow_imbalance_share | market_native_gun_amount_truncated | delta_log1p_1h | 0 | 11 | NULL | NULL | 0 | NULL [NULL, NULL] | 0 / 0 / 0 |
| flow_imbalance_share | market_native_gun_amount_truncated | delta_log1p_1h | 1 | 11 | NULL | NULL | 0 | NULL [NULL, NULL] | 0 / 0 / 0 |
| flow_imbalance_share | market_native_gun_amount_truncated | delta_log1p_1h | 6 | 11 | NULL | NULL | 0 | NULL [NULL, NULL] | 0 / 0 / 0 |
| flow_imbalance_share | market_native_gun_amount_truncated | delta_log1p_1h | 24 | 9 | NULL | NULL | 0 | NULL [NULL, NULL] | 0 / 0 / 0 |
| flow_imbalance_share | market_native_gun_amount_truncated | hour_of_week_seasonal_residual | 0 | 11 | NULL | NULL | 0 | NULL [NULL, NULL] | 0 / 0 / 0 |
| flow_imbalance_share | market_native_gun_amount_truncated | hour_of_week_seasonal_residual | 1 | 11 | NULL | NULL | 0 | NULL [NULL, NULL] | 0 / 0 / 0 |
| flow_imbalance_share | market_native_gun_amount_truncated | hour_of_week_seasonal_residual | 6 | 11 | NULL | NULL | 0 | NULL [NULL, NULL] | 0 / 0 / 0 |
| flow_imbalance_share | market_native_gun_amount_truncated | hour_of_week_seasonal_residual | 24 | 9 | NULL | NULL | 0 | NULL [NULL, NULL] | 0 / 0 / 0 |
| flow_imbalance_share | market_trade_tx_count | delta_log1p_1h | 0 | 11 | NULL | NULL | 0 | NULL [NULL, NULL] | 0 / 0 / 0 |
| flow_imbalance_share | market_trade_tx_count | delta_log1p_1h | 1 | 11 | NULL | NULL | 0 | NULL [NULL, NULL] | 0 / 0 / 0 |
| flow_imbalance_share | market_trade_tx_count | delta_log1p_1h | 6 | 11 | NULL | NULL | 0 | NULL [NULL, NULL] | 0 / 0 / 0 |
| flow_imbalance_share | market_trade_tx_count | delta_log1p_1h | 24 | 9 | NULL | NULL | 0 | NULL [NULL, NULL] | 0 / 0 / 0 |
| flow_imbalance_share | market_trade_tx_count | hour_of_week_seasonal_residual | 0 | 11 | NULL | NULL | 0 | NULL [NULL, NULL] | 0 / 0 / 0 |
| flow_imbalance_share | market_trade_tx_count | hour_of_week_seasonal_residual | 1 | 11 | NULL | NULL | 0 | NULL [NULL, NULL] | 0 / 0 / 0 |
| flow_imbalance_share | market_trade_tx_count | hour_of_week_seasonal_residual | 6 | 11 | NULL | NULL | 0 | NULL [NULL, NULL] | 0 / 0 / 0 |
| flow_imbalance_share | market_trade_tx_count | hour_of_week_seasonal_residual | 24 | 9 | NULL | NULL | 0 | NULL [NULL, NULL] | 0 / 0 / 0 |
| flow_imbalance_share | market_unique_buyers | delta_log1p_1h | 0 | 11 | NULL | NULL | 0 | NULL [NULL, NULL] | 0 / 0 / 0 |
| flow_imbalance_share | market_unique_buyers | delta_log1p_1h | 1 | 11 | NULL | NULL | 0 | NULL [NULL, NULL] | 0 / 0 / 0 |
| flow_imbalance_share | market_unique_buyers | delta_log1p_1h | 6 | 11 | NULL | NULL | 0 | NULL [NULL, NULL] | 0 / 0 / 0 |
| flow_imbalance_share | market_unique_buyers | delta_log1p_1h | 24 | 9 | NULL | NULL | 0 | NULL [NULL, NULL] | 0 / 0 / 0 |
| flow_imbalance_share | market_unique_buyers | hour_of_week_seasonal_residual | 0 | 11 | NULL | NULL | 0 | NULL [NULL, NULL] | 0 / 0 / 0 |
| flow_imbalance_share | market_unique_buyers | hour_of_week_seasonal_residual | 1 | 11 | NULL | NULL | 0 | NULL [NULL, NULL] | 0 / 0 / 0 |
| flow_imbalance_share | market_unique_buyers | hour_of_week_seasonal_residual | 6 | 11 | NULL | NULL | 0 | NULL [NULL, NULL] | 0 / 0 / 0 |
| flow_imbalance_share | market_unique_buyers | hour_of_week_seasonal_residual | 24 | 9 | NULL | NULL | 0 | NULL [NULL, NULL] | 0 / 0 / 0 |
| gun_price_return_1h | market_native_gun_amount_truncated | delta_log1p_1h | 0 | 12335 | -0.004843 | -0.021089 | 8 | -0.003716 [-0.047916, 0.037447] | 4 / 4 / 0 |
| gun_price_return_1h | market_native_gun_amount_truncated | delta_log1p_1h | 1 | 12334 | 0.010959 | -0.002587 | 8 | 0.021907 [-0.024008, 0.043620] | 5 / 3 / 0 |
| gun_price_return_1h | market_native_gun_amount_truncated | delta_log1p_1h | 6 | 12329 | -0.009928 | 0.001892 | 8 | -0.006517 [-0.041548, 0.006341] | 2 / 6 / 0 |
| gun_price_return_1h | market_native_gun_amount_truncated | delta_log1p_1h | 24 | 12311 | 0.017044 | -0.004886 | 8 | 0.019731 [-0.009732, 0.040058] | 6 / 2 / 0 |
| gun_price_return_1h | market_native_gun_amount_truncated | hour_of_week_seasonal_residual | 0 | 12335 | -0.004783 | -0.004062 | 8 | -0.001821 [-0.027234, 0.039272] | 4 / 4 / 0 |
| gun_price_return_1h | market_native_gun_amount_truncated | hour_of_week_seasonal_residual | 1 | 12334 | -0.006825 | -0.006464 | 8 | -0.003481 [-0.026600, 0.041168] | 3 / 5 / 0 |
| gun_price_return_1h | market_native_gun_amount_truncated | hour_of_week_seasonal_residual | 6 | 12329 | 0.001915 | -0.000726 | 8 | 0.001902 [-0.039659, 0.038800] | 4 / 4 / 0 |
| gun_price_return_1h | market_native_gun_amount_truncated | hour_of_week_seasonal_residual | 24 | 12311 | 0.006587 | 0.000806 | 8 | 0.010991 [-0.014354, 0.057056] | 5 / 3 / 0 |
| gun_price_return_1h | market_trade_tx_count | delta_log1p_1h | 0 | 12335 | -0.002276 | -0.010184 | 8 | -0.004457 [-0.053000, 0.036216] | 4 / 4 / 0 |
| gun_price_return_1h | market_trade_tx_count | delta_log1p_1h | 1 | 12334 | 0.004888 | -0.018539 | 8 | 0.007114 [-0.053020, 0.044442] | 4 / 4 / 0 |
| gun_price_return_1h | market_trade_tx_count | delta_log1p_1h | 6 | 12329 | -0.006573 | 0.004619 | 8 | -0.010037 [-0.030535, 0.018362] | 2 / 6 / 0 |
| gun_price_return_1h | market_trade_tx_count | delta_log1p_1h | 24 | 12311 | 0.017260 | 0.004046 | 8 | 0.017360 [-0.017284, 0.041529] | 6 / 2 / 0 |
| gun_price_return_1h | market_trade_tx_count | hour_of_week_seasonal_residual | 0 | 12335 | 0.001533 | 0.000803 | 8 | 0.006856 [-0.014634, 0.044057] | 6 / 2 / 0 |
| gun_price_return_1h | market_trade_tx_count | hour_of_week_seasonal_residual | 1 | 12334 | -0.009189 | -0.010860 | 8 | -0.005544 [-0.031314, 0.029242] | 2 / 6 / 0 |
| gun_price_return_1h | market_trade_tx_count | hour_of_week_seasonal_residual | 6 | 12329 | -0.007271 | -0.001512 | 8 | -0.006711 [-0.046132, 0.016844] | 3 / 5 / 0 |
| gun_price_return_1h | market_trade_tx_count | hour_of_week_seasonal_residual | 24 | 12311 | 0.000712 | -0.001188 | 8 | 0.010127 [-0.035838, 0.056330] | 5 / 3 / 0 |
| gun_price_return_1h | market_unique_buyers | delta_log1p_1h | 0 | 12335 | 0.000650 | -0.006225 | 8 | -0.011581 [-0.035772, 0.044197] | 3 / 5 / 0 |
| gun_price_return_1h | market_unique_buyers | delta_log1p_1h | 1 | 12334 | 0.003119 | -0.021928 | 8 | 0.004622 [-0.067325, 0.041808] | 4 / 4 / 0 |
| gun_price_return_1h | market_unique_buyers | delta_log1p_1h | 6 | 12329 | -0.009783 | 0.000591 | 8 | -0.016986 [-0.025424, 0.010314] | 2 / 6 / 0 |
| gun_price_return_1h | market_unique_buyers | delta_log1p_1h | 24 | 12311 | 0.013142 | 0.002631 | 8 | 0.006024 [-0.038905, 0.039944] | 7 / 1 / 0 |
| gun_price_return_1h | market_unique_buyers | hour_of_week_seasonal_residual | 0 | 12335 | 0.004922 | 0.001905 | 8 | 0.015252 [-0.013705, 0.043236] | 6 / 2 / 0 |
| gun_price_return_1h | market_unique_buyers | hour_of_week_seasonal_residual | 1 | 12334 | -0.006529 | -0.011051 | 8 | -0.003905 [-0.031463, 0.042366] | 3 / 5 / 0 |
| gun_price_return_1h | market_unique_buyers | hour_of_week_seasonal_residual | 6 | 12329 | -0.012941 | -0.003461 | 8 | -0.013339 [-0.044233, 0.015036] | 2 / 6 / 0 |
| gun_price_return_1h | market_unique_buyers | hour_of_week_seasonal_residual | 24 | 12311 | 0.004098 | 0.000817 | 8 | 0.019048 [-0.036747, 0.060780] | 5 / 3 / 0 |

## TIME_STABILITY_DIAGNOSTIC

The sample was divided into exactly 8 chronological blocks of 1,542 outcome hours. All 24 `gun_price_return_1h` relationship rows had both positive and negative block Spearman coefficients (8 defined blocks per row). Their full-sample Spearman coefficients ranged from -0.012941 to +0.017260. All `flow_imbalance_share` block estimates were NULL because each fixed-lag cell had fewer than 20 valid pairs. Full-sample flow-share cells had 9 or 11 finite pairs, but coefficients were NULL under the preregistered zero-denominator rule; no flow-share coefficient was estimated.

## PRICE_SHOCK_THRESHOLDS

Using all non-NULL 1-hour price returns, q05 = `-0.016533971142` and q95 = `0.016966713440`. These thresholds were not adjusted after event counts were observed.

## EVENT_COUNTS

- Positive candidates: 617; selected after 24-hour declustering: 146; retained after requiring t-1 and t+24: 145.
- Negative candidates: 617; selected after 24-hour declustering: 146; retained after the same boundary rule: 145.
Each retained sign population contains the same events across all outcomes and horizons. Candidate signs were declustered separately.

## EVENT_DECLUSTERING

Consecutive candidates within 24 hours were clustered separately by sign. Each cluster retained its largest absolute return, with earliest time resolving ties. Boundary events without both t-1 and t+24 were removed.

## EVENT_SUMMARY_COMPLETENESS

All 24 direction/outcome/horizon cells are present. Response is `log1p(value[t+h]) - log1p(value[t-1])`. Horizon 0 is same-hour association only; within-hour ordering is unknown. Each cell uses 2,000 bootstrap median replicates with the fixed local RNG seed formula. Low event count rows: 0 of 24. Intervals are descriptive and are not significance decisions.

| Direction | Outcome | Horizon h | Events | Mean | Median | q25 | q75 | Bootstrap median interval 95% | Low n |
|---|---|---:|---:|---:|---:|---:|---:|---|---|
| negative | market_native_gun_amount_truncated | 0 | 145 | 0.206618 | 0.125463 | -0.128186 | 0.506665 | [0.056442, 0.204448] | NO |
| negative | market_native_gun_amount_truncated | 1 | 145 | 0.249493 | 0.218891 | -0.353121 | 0.770279 | [0.074515, 0.410488] | NO |
| negative | market_native_gun_amount_truncated | 6 | 145 | -0.136943 | 0.016659 | -1.061089 | 1.214190 | [-0.445757, 0.390056] | NO |
| negative | market_native_gun_amount_truncated | 24 | 145 | 0.232300 | 0.113195 | -0.348167 | 0.623703 | [-0.052532, 0.243005] | NO |
| negative | market_trade_tx_count | 0 | 145 | 0.018540 | 0.051736 | -0.271934 | 0.297402 | [0.000000, 0.149440] | NO |
| negative | market_trade_tx_count | 1 | 145 | 0.151240 | 0.134712 | -0.287369 | 0.662593 | [-0.032365, 0.332408] | NO |
| negative | market_trade_tx_count | 6 | 145 | -0.189666 | -0.068993 | -1.035243 | 0.748410 | [-0.365869, 0.211295] | NO |
| negative | market_trade_tx_count | 24 | 145 | 0.065385 | 0.032267 | -0.356910 | 0.554385 | [-0.089199, 0.197750] | NO |
| negative | market_unique_buyers | 0 | 145 | 0.011946 | 0.079792 | -0.189242 | 0.300721 | [0.000000, 0.146005] | NO |
| negative | market_unique_buyers | 1 | 145 | 0.124097 | 0.159683 | -0.196710 | 0.632523 | [0.038173, 0.287682] | NO |
| negative | market_unique_buyers | 6 | 145 | -0.211719 | -0.113329 | -1.047533 | 0.742521 | [-0.361370, 0.131093] | NO |
| negative | market_unique_buyers | 24 | 145 | 0.051425 | 0.068286 | -0.290191 | 0.485508 | [-0.068414, 0.159568] | NO |
| positive | market_native_gun_amount_truncated | 0 | 145 | -0.186385 | 0.021815 | -0.557376 | 0.312274 | [-0.046717, 0.111324] | NO |
| positive | market_native_gun_amount_truncated | 1 | 145 | -0.197193 | 0.062589 | -0.625275 | 0.775474 | [-0.074425, 0.206523] | NO |
| positive | market_native_gun_amount_truncated | 6 | 145 | -0.196240 | -0.084534 | -1.041062 | 0.980587 | [-0.450017, 0.298293] | NO |
| positive | market_native_gun_amount_truncated | 24 | 145 | 0.179117 | 0.062253 | -0.483303 | 0.670316 | [-0.067537, 0.283447] | NO |
| positive | market_trade_tx_count | 0 | 145 | 0.022616 | 0.024585 | -0.263197 | 0.376511 | [-0.017427, 0.083881] | NO |
| positive | market_trade_tx_count | 1 | 145 | -0.030180 | 0.100540 | -0.405465 | 0.654926 | [0.009434, 0.314569] | NO |
| positive | market_trade_tx_count | 6 | 145 | -0.098843 | -0.192803 | -1.026540 | 0.998322 | [-0.424019, 0.078781] | NO |
| positive | market_trade_tx_count | 24 | 145 | 0.181960 | 0.111809 | -0.242752 | 0.574760 | [0.000000, 0.276177] | NO |
| positive | market_unique_buyers | 0 | 145 | 0.070620 | 0.031322 | -0.188401 | 0.307701 | [-0.022197, 0.116864] | NO |
| positive | market_unique_buyers | 1 | 145 | -0.017719 | 0.106684 | -0.317981 | 0.641475 | [0.000000, 0.295418] | NO |
| positive | market_unique_buyers | 6 | 145 | -0.046013 | -0.060625 | -0.850095 | 0.938270 | [-0.353139, 0.159065] | NO |
| positive | market_unique_buyers | 24 | 145 | 0.192174 | 0.097118 | -0.218800 | 0.545386 | [0.000000, 0.221393] | NO |

## BOOTSTRAP_CONFIGURATION

Replicates=2000; base seed=3401; direction/outcome/horizon category indices follow the frozen methodology. Quantiles use linear interpolation. No binary significance label is attached to an interval.

## RESULT_ARTIFACTS

- [`DEV/analysis/034_relationship_matrix.csv`](../../analysis/034_relationship_matrix.csv): 48 aggregate cells.
- [`DEV/analysis/034_price_shock_event_summary.csv`](../../analysis/034_price_shock_event_summary.csv): 24 aggregate cells.
- [`DEV/analysis/034_analysis_summary.json`](../../analysis/034_analysis_summary.json): frozen configuration, source metadata, event counts, and digests.

## RESULT_DIGESTS

- Relationship matrix: `81004c088b886eee4289151803a18c27d8ee4a75132f178ce6a8be584b1831ef` (independently recomputed from normalized logical rows).
- Event summary: `5f3e89ed359275c65977acaf02ad45d14b2a8329fcc4902c8e3b590396bff772` (independently recomputed from normalized logical rows).
- Analysis summary: `e7a16b3b2a84c15d20b5ce019e7463357b06513b60ed7e48754113df2e844e74` (canonical JSON digest independently verified).

## RESOURCE_OBSERVATION

| Stage | CPU % | Available RAM bytes | Committed bytes | Commit limit bytes | Free commit bytes |
|---|---:|---:|---:|---:|---:|
| before staging read | 54.8 | 3600568320 | 4869922816 | 16092729344 | 11222806528 |
| after snapshot read | 69.4 | 3580018688 | 4869922816 | 16092729344 | 11222806528 |
| after relationship matrix | 51.2 | 3553619968 | 4869914624 | 16092729344 | 11222814720 |
| after event analysis | 50.0 | 3553046528 | 4869914624 | 16092729344 | 11222814720 |
| after artifact serialization | 54.1 | 3552231424 | 4869914624 | 16092729344 | 11222814720 |

Resource observations remained stable during the bounded read and computation. `RESOURCE_STABILITY=PASS`.

## NANSEN_API_PROOF

`NANSEN_API_CALLS_TASK034=0`. The source was read from staging; no Nansen API request occurred.

## RPC_PROOF

`ONCHAIN_RPC_CALLS_TASK034=0`. No overlap resolver or chain RPC was called.

## DATABASE_SAFETY

`PRODUCTION_CONNECTIONS_TASK034=0`; production DDL=0; production DML=0. Staging connection mode was READ ONLY; staging DDL=0 and DML=0. No sales table was accessed.

## SECURITY_CHECK

Outputs contain aggregate coefficients and event summaries only. No hourly rows, event timestamp list, wallet/token/transaction identity, or credentials were emitted. `SECRET_SCAN=PASS`; `ENV_TRACKED=NO`.

## CYRILLIC_CHECK

PASS.

## FILES_CHANGED

The preregistration commit contains the frozen analysis module, synthetic test suite, and methodology section. The result commit contains the three aggregate artifacts in `DEV/analysis/` and this report. No source, test, or methodology file changed after preregistration.

## LIMITATIONS

The flow-imbalance-share relationships were not estimable from the small number of valid pairs. Price-return associations were close to zero across the full sample, with mixed block signs. Event response distributions were broad and several medians changed sign across horizons; bootstrap intervals are descriptive, not p-value substitutes. The event design does not establish within-hour order, economic mechanism, causality, or predictive use. The market amount is parser-recorded integer-truncated native GUN and is not an Avalanche token-flow amount.

## DESCRIPTIVE_FINDINGS

Across the 24 predefined price-return cells, the Spearman range was approximately -0.012941 to +0.017260 and every cell showed both positive and negative block coefficients. This is weak and time-inconsistent descriptive association in this sample. The 24 flow-share cells remain present but have NULL coefficients under the zero-denominator rule; finite pair counts were 9 or 11 and block estimates were undefined.

For positive price-shock events, median responses for the three market outcomes were positive at 0h and 1h, negative at 6h, and positive at 24h. For negative-shock events, medians were positive at 0h and 1h, negative at 6h, and positive at 24h. The sign pattern is not evidence of an effect; event distributions and bootstrap intervals in the complete table show substantial dispersion. These are historical descriptive responses only.

## NEXT_RECOMMENDED_TASK

Review these descriptive results and their limitations. Any further model, visualization, causal design, or prediction work requires a separately preregistered task.
