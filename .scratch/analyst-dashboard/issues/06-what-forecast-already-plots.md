# What Forecast already plots

Type: research
Status: resolved
Blocked by:

## Question

Without adding series or methods: what does the Forecast module **already** return that a Dashboard chart could draw, and what stays **inside** `run_forecast` (history path, two method trajectories) and never reaches `forecast_for_tool` / `[Forecast …]` tags?

Need: fields of `ForecastResult` / tool JSON; whether daily history is serializable today; Urals / Yahoo-fail paths; what a chart would still have to invent (full horizon path vs last-point-only).

Findings file: [research/forecast-plot-payload.md](../research/forecast-plot-payload.md).

## Answer

`forecast_for_tool` exposes two **horizon-end** scalars per method (point + interval), symbol, horizon, `[Forecast …]` labels, and an uncertainty note. Daily history and full SARIMA/Holt paths are computed inside `run_forecast` / fit helpers and **never serialized**. ADR 0009’s “point path” is not the implemented JSON. A history+curves chart needs new return fields or a host call to `load_live_history`; even then today’s public API does not give per-day method trajectories. Urals / Yahoo-fail: empty `methods` + `unavailable_reason`, no invented CSV.
