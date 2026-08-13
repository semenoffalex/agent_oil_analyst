# 0009. Forecast from yfinance with ARIMA and exponential smoothing

## Status

Accepted

## Context

The spec requires a Forecast module with at least two methods and a history source. Alternatives were Prophet+ARIMA on Yahoo, ARIMA+smoothing on a frozen CSV, or a factor regression that needs extra series. LSTM was left out.

Yahoo in Docker is not reliable. A CSV would have been replayable; the owner chose live history instead.

## Decision

v1 Forecast loads history with `yfinance` and fits two `statsmodels` methods: SARIMA and exponential smoothing (Holt–Winters). The module returns a point path, an interval, and a short interpretation. The Analyst calls it only on a Forecast request ([0004](0004-forecast-only-on-explicit-verbs.md)).

Default series is Brent. WTI if the user names it. Urals has no trustworthy Yahoo series in v1: the tool says so and does not invent a proxy.

No silent CSV fallback if Yahoo is down — the tool errors and the Analyst reports uncertainty.

## Consequences

- Docker needs outbound access to Yahoo. Reviews can fail on a blocked `yfinance`.
- Image stays slimmer than Prophet. No `cmdstanpy` build.
- Demos that must show a Forecast have to hit Yahoo or they show an error path, which is still a valid “uncertainty” dialogue.
- Adding Prophet later is a dependency change, not a flag.
