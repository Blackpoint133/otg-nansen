# Meridian Demo Recording Checklist

Use this checklist for a silent 30-60 second screen recording. Aim for about
45 seconds.

## Before Recording

1. Open PowerShell.
2. Change to the repository root:

   ```powershell
   cd C:\VAMBAM\Projects\OTG\parsers\parser_nansen
   ```

3. Make sure `NANSEN_API_KEY` is available in this PowerShell process. Do not
   type the key into a command that will appear in the recording.
4. Start the demo:

   ```powershell
   .\scripts\run_meridian_demo.ps1
   ```

5. Open <http://127.0.0.1:8765/> in the browser.
6. Confirm the historical relationship and event panels are visible.
7. Do not click **Refresh Live Data** yet while preparing the capture.
8. Adjust browser zoom and window size so the live card, historical panels,
   finding, and GitHub identity are readable together.
9. Prepare the screen recorder. Keep the browser in the foreground and avoid
   exposing desktop notifications.

## Recording Sequence

| Time | Screen action |
|---|---|
| 0-5 sec | Show the title, project name, and question about Nansen `$GUN` Smart Money and OTG marketplace activity. |
| 5-14 sec | Click **Refresh Live Data** once. Wait for the LIVE state. Keep the completed-hour time, price, 1-hour move, and regime visible. |
| 14-23 sec | Show the **Live -> Historical Context** decision and its historical thresholds. |
| 23-32 sec | Show the Historical relationship panel and its fixed 0h/1h/6h/24h comparisons. |
| 32-40 sec | Show the Historical event response panel for trades, native GUN volume, and unique buyers. |
| 40-47 sec | Finish on the finding, limitations, and GitHub project identity. |

## Recording Rules

- Make exactly one deliberate live refresh during the recording.
- Do not expose the terminal API key or open `.env`.
- Do not show browser developer tools containing request headers.
- Keep the observation timestamp visible.
- Do not describe the results as prediction or causality.
- If the live request fails, show the honest error state. Do not substitute
  fixture data; restart and record again later if needed.

## After Recording

- Confirm the final video is between 30 and 60 seconds.
- Check that text is readable, the GitHub identity is visible, and the live
  state appears in the recording.
- Save the final video and review it once before sharing.
- Do not publish until the X post copy has been reviewed.
