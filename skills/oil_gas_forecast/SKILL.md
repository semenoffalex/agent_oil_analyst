---
name: oil_gas_forecast
description: Oil-price Forecast calculator (AutoARIMA, UnobservedComponents, and AutoReg; never averaged).
version: 0.1.0
type: extension
runtime: python3
entry: plugin.py
permissions: [tool]
when_to_use: >
  The user wants an oil-price Forecast (Brent default, WTI if named). An explicit
  verb is a hint, not a requirement. Do not call for Urals as if a series existed.
timeout_sec: 120
---

# Forecast

Call this tool when a crude-price Forecast would help. Copy `[Forecast …]` labels verbatim.
Always show **all three** methods with intervals and the short interpretation.
Do **not** average the two paths into one number.
Unspecified crude is Brent. Named WTI is WTI. Urals has no series — say so, do not proxy with Brent.
If history is unavailable, say you are uncertain. Do not invent a CSV or a price strip.
An explicit verb (`forecast`, `predict`, `спрогнозируй`) is a hint; you may still call this without one.
