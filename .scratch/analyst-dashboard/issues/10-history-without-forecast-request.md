# May the Dashboard load price history without a Forecast request

Type: grilling
Status: resolved
Blocked by: 01

## Question

[What Forecast already plots](06-what-forecast-already-plots.md): the tool JSON is two last-horizon **points**, not a history series and not two full paths. A visible price chart therefore needs either new Forecast return fields or a **host** call to `load_live_history` (Yahoo/Stooq/cache).

If [What frames the chat for a bank executive](01-what-frames-the-chat.md) wants a chart:

- May the Dashboard load Brent/WTI history at session start **without** the model calling `run_forecast`?
- If yes: is that a Live quote strip, a Forecast illustration, or a third thing — and how is it labelled so it is not an averaged “the price”?
- If the model later Forecasts, do we then overlay the two method **end points** only, or do we extend the module to return paths?

If ticket 01 rejects a chart, close this as out of scope for the Dashboard (history stays inside the module).

## Answer

**Yes.** At **session start** the host draws **one chart**: **actual prices** (history / last close) **plus** a **21 trading-day Forecast**, for **Brent and Urals**. No Forecast verb required.

- Two methods per crude (SARIMA and Holt–Winters), **never** averaged, never labelled as “the bank’s price.”
- Actuals on that chart **are** the Live quote for those crudes (last history point), not a second mystery tape. A separate Live-quote tile is optional in layout.
- The pin stays until the user **asks to update**; then the host recomputes and **replaces** the chart. No polling. Chat may change horizon or emphasise one crude.
- Implementers must expose history and per-step paths (today’s `forecast_for_tool` is last-point only — [What Forecast already plots](06-what-forecast-already-plots.md)). History failure: uncertainty, no fake CSV ([0009](../../../docs/adr/0009-yfinance-sarima-ets.md)).
- **Urals is in.** That **reopens** “no Urals series.” Source is [Where the Urals series comes from](11-where-urals-series-comes-from.md). Until that ticket, do **not** proxy Urals with Brent.

## Comments

- Customer (2026-08-19): chart on open = actuals + 21d forecast, Brent **and** Urals; refresh on request. Supersedes the earlier “Brent only / Urals no series on the Dashboard” line in this Answer.
