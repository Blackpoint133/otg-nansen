# Meridian Silent Demo Storyboard

The local demo is implemented. This storyboard describes a silent recording
of approximately 45 seconds, within the 30-60 second range listed in the
Meridian FAQ. The operator steps are in
[`meridian_recording_checklist.md`](meridian_recording_checklist.md).

| Time | Screen and readable on-screen point |
|---|---|
| 0-5 sec | Show OTG - Nansen Market Intelligence and the question: does Avalanche `$GUN` Smart Money activity relate to Off The Grid marketplace activity? |
| 5-14 sec | Click **Refresh Live Data** once. Show the latest completed bucket, price, 1-hour move, and LIVE badge. |
| 14-23 sec | Show the live-to-historical regime card and the Task 034 thresholds that classify the observation. |
| 23-32 sec | Show the fixed-lag historical relationship panel: three market outcomes across 0h, 1h, 6h, and 24h. |
| 32-40 sec | Show the historical price-shock response panel for trades, native GUN volume, and unique buyers. |
| 40-47 sec | Finish on the weak/time-inconsistent result, descriptive limitations, cross-chain separation, and GitHub identity. |

## Capture Rules

- Keep the live observation timestamp and source labels visible.
- If live data cannot load, retain the honest error state; never substitute a
  canned value and label it live.
- Keep Avalanche `$GUN` observations separate from native marketplace GUN
  amounts.
- Treat 0h as same-hour association; within-hour causal ordering is unknown.
- Do not describe the results as causal, predictive, or a trading signal.
- Keep the GitHub URL legible in the closing frame.
