# Meridian Silent Demo Storyboard

Specification for the next demo implementation. Target runtime: **45 seconds**
(within the FAQ's 30–60 second range). No narration; use large on-screen labels
and readable captions. The current repository has no presentation UI, so every
proposed visual or live surface below is marked `PENDING_IMPLEMENTATION`.

| Time | Silent screen and on-screen text | Implementation state |
|---|---|---|
| 0–5 s | Title card: “Does Avalanche `$GUN` Smart Money activity line up with Off The Grid marketplace activity?” Subtitle: “Historical descriptive research — not a trading signal.” | `PENDING_IMPLEMENTATION` title/demo shell |
| 5–13 s | A clearly timestamped “Latest Nansen `$GUN`” card showing one current price/flow snapshot and its source time. A compact label explains that the live Nansen observation drives this panel. Show loading/error state if unavailable; never substitute canned values. | `PENDING_IMPLEMENTATION` live Nansen view and data endpoint |
| 13–22 s | Historical comparison panel: hourly Nansen `$GUN` price return beside OTG trade-transaction count and native-GUN amount across the analyzed period. Label both sources and their units; retain separate axes/series. | `PENDING_IMPLEMENTATION` historical visualization backed by committed Task 034 artifacts |
| 22–31 s | Price-shock panel: positive/negative 5th/95th percentile event groups and the committed event-response medians at 0, 1, 6, and 24 hours. Add “0h = same-hour association; ordering unknown.” | `PENDING_IMPLEMENTATION` event-summary visualization |
| 31–38 s | Result card: “Price-return associations were weak and time-inconsistent. Flow-share estimates were too sparse under the preregistered rule.” Add “Descriptive only · no causality or prediction claim.” | `PENDING_IMPLEMENTATION` results panel |
| 38–45 s | Project identity/end card: “OTG - Nansen Market Intelligence,” public GitHub URL, methodology/report links, and “Built with Nansen API.” | `PENDING_IMPLEMENTATION` branded end card |

## Capture Rules

- Capture the application running, with the live Nansen component successfully
  loaded during the recording. If it cannot load, show an honest error state
  and do not imply that a live result was retrieved.
- Keep the observation timestamp and source labels visible. Do not present
  Avalanche `$GUN` values and native marketplace GUN as numerically
  interchangeable.
- Use only the committed Task 034 relationship/event outputs for the
  historical panel. Do not rerun or tune the analysis for the demo.
- Do not add a trading signal, causal wording, or unsourced market USD value.
- Keep the GitHub URL and methodology references legible in the final frame.
