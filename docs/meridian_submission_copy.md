# Meridian Submission Copy Bank

Prepared text to adapt to the official entry form. This is a copy bank, not a reproduction of the form or a claim about mandatory fields.

## PROJECT_NAME

OTG - Nansen Market Intelligence

## ONE_LINE_DESCRIPTION

A Nansen-powered market-intelligence layer combining live Avalanche `$GUN` context with 12,336 hours of historical Off The Grid marketplace activity.

## SHORT_DESCRIPTION

OTG - Nansen Market Intelligence is integrated into the production OTG Analytics application. It combines live Avalanche `$GUN` price and Smart Money flow context with 12,336 aligned hours of Off The Grid marketplace trades, native GUN volume, and buyer activity. Users can compare historical marketplace responses across fixed 0h, 1h, 6h, and 24h horizons and view historical reactions around unusually large price moves. The observed hourly price-return relationships were weak and time-inconsistent. The page presents descriptive context, not prediction, causation, or a standalone trading signal.

## HOW_NANSEN_IS_USED

Nansen Avalanche `$GUN` observations drive the current market-context classification and contribute price and Smart Money flow measures to the fixed historical analysis. A private server-side service refreshes a shared sanitized live observation approximately once per hour. Page visits, chart changes, and Guide interactions read the available observation and do not directly make Nansen requests. The browser never receives the Nansen API key. Historical price and flow observations are compared with OTG marketplace activity; the resulting relationships are presented descriptively and were weak and time-inconsistent.

## WHAT_WAS_BUILT

The production OTG Analytics application includes a native Nansen mode with automatically updated live `$GUN` context, a historical OTG reaction visualization, a concise Market Takeaway, and a user Guide. A private backend refreshes and serves the shared live observation. Committed historical artifacts contain the 12,336-hour aligned dataset and preregistered relationship and price-shock summaries. The interface includes visible “Data provided by Nansen” attribution. The historical results remain descriptive and are not presented as causal or predictive.

## KEY_TECHNICAL_FACTS

- 12,336 canonical aligned hourly observations.
- Nansen Avalanche `$GUN` price and Smart Money flow context.
- OTG marketplace hourly trades, native GUN volume, and buyer aggregation.
- Native production Nansen mode in OTG Analytics.
- Shared automatic live observation refresh, approximately hourly.
- Historical relationship and price-shock response views at 0h, 1h, 6h, and 24h.
- Guide, Market Takeaway, and visible Nansen attribution.
- Descriptive, noncausal, nonpredictive positioning; historical associations were weak and time-inconsistent.

## GITHUB_URL

https://github.com/Blackpoint133/otg-nansen

## X_POST_URL

[TO_FILL_AFTER_POSTING]

## DEMO_VIDEO_URL

[TO_FILL_AFTER_UPLOAD_IF_REQUIRED]
