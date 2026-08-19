# 01 — Forecast plot payload

**What to build:** The Forecast module exposes Brent daily history and two 21 trading-day method paths (SARIMA and Holt–Winters, never averaged) so a Dashboard can draw actuals plus Forecast without inventing a series. Chat `[Forecast …]` tags stay last-horizon scalars. Urals still has no series and must not proxy Brent. History/Yahoo failure is uncertainty, not a fake CSV.

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

- [ ] Payload includes Brent history dates/closes plus per-step SARIMA and Holt–Winters paths for a 21 trading-day horizon (two series, no average).
- [ ] Chat-facing `[Forecast …]` labels remain last-horizon point + interval per method.
- [ ] Urals still returns no series; no Brent numbers labelled as Urals.
- [ ] Loader failure yields uncertainty / empty methods, not invented prices.
- [ ] Frozen tests lock the payload and the Urals / failure paths without a UI.
