# 12 — Forecast module in the loop

**What to build:** When the Analyst calls Forecast, the reply tags `[Forecast …]` and shows SARIMA and Holt–Winters with intervals and a short interpretation, never a silent average. Default crude is Brent; WTI if named; Urals has no series and is not proxied. A blocked price history is uncertainty, not a fake CSV. An explicit verb is a prompt hint, not a host detector.

**Blocked by:** 09 — Chainlit talks to Ouroboros

**Status:** ready-for-agent

- [ ] Forecast is a reviewed extension tool wrapping the calculation module (two methods, no average).
- [ ] Unspecified crude → Brent; named WTI → WTI; Urals → no series, no Brent proxy.
- [ ] Yahoo / history failure → uncertainty in the answer, not invented prices.
- [ ] Host does not refuse Forecast because the question lacked a verb; if the module ran, the answer tags it.
- [ ] No oil-price strip in prose unless it came from Reports, Web sources, or this module.
