# Where the Urals series comes from

Type: grilling
Status: resolved
Blocked by: 10

## Question

The Dashboard chart must show **actuals + 21-day Forecast for Brent and Urals** ([May the Dashboard load price history without a Forecast request](10-history-without-forecast-request.md)). Today the Forecast module has **no Urals series** and must not proxy Brent ([0009](../../../docs/adr/0009-yfinance-sarima-ets.md), [Forecast module in the loop](../../ouroboros-analyst/issues/12-forecast-module-in-the-loop.md)).

What daily (or trading-day) Urals history may the host use?

- A named vendor / official series (who, licence, Docker-reachable URL)?
- CBR or another Report as levels, not a Yahoo strip?
- Show Urals as “no series” on the chart until a feed exists (contradicts “Brent + Urals” on open)?
- Anything **except** copying Brent and relabelling it.

Without this, implementers cannot draw Urals without inventing prices.

## Answer

**Deferred.** The Dashboard chart for this Demo cut is **Brent only** (actuals + 21-day Forecast, two methods, refresh on request). Urals stays **out of this map** until a real series exists — no Brent proxy. Chat still says “no series” if asked for Urals Forecast ([0009](../../../docs/adr/0009-yfinance-sarima-ets.md)).
