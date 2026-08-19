# What Forecast already returns for a Dashboard chart

Ticket: [06-what-forecast-already-plots](../issues/06-what-forecast-already-plots.md).  
Sources: `oil_gas_analyst/forecast.py`, `oil_gas_analyst/types.py`, `oil_gas_analyst/turn.py` (`forecast_citations`), `skills/oil_gas_forecast/`, `tests/test_forecast.py`, [ADR 0009](../../../docs/adr/0009-yfinance-sarima-ets.md).

Glossary: **Forecast** = module output (methods + intervals), not a price strip from Web. **Live quote** = latest traded/reported price from Web or a market API. Daily close history used to fit models is neither a Live quote nor part of the Forecast tool payload today.

## Verdict

Without new series or methods, a Dashboard can draw **two horizon-end scalars per crude** (SARIMA and Holt–Winters), each with a **point + low–high interval**, plus symbol / horizon / citation labels. It **cannot** draw the fitted history path or either method’s day-by-day trajectory from `forecast_for_tool` / `[Forecast …]` alone — those stay local to `run_forecast` / the fit helpers.

ADR 0009 says the module returns a “point path”; the **implemented** contract is last-horizon-day point + interval only.

---

## `ForecastResult` and `MethodForecast`

From `oil_gas_analyst/types.py`:

| Type | Fields |
|------|--------|
| `MethodForecast` | `name`, `point`, `low`, `high`, `interpretation` |
| `ForecastResult` | `symbol`, `methods: list[MethodForecast]`, `unavailable_reason` (optional), `horizon_days` (optional) |

No history series, no date index, no per-day forecast arrays, no average of the two methods.

Success path (`run_forecast`): `methods` has two entries (`sarima`, `holt_winters`), `unavailable_reason` is unset, `horizon_days` is set from the closed phrase list (default 90).

Failure / Urals path: `methods == []`, `unavailable_reason` set, `horizon_days` usually unset (Urals early-return never sets it).

---

## `forecast_for_tool` JSON (what the skill / Dashboard host sees)

Built in `forecast_for_tool` from `ForecastResult` + `forecast_citations`:

| Key | Content |
|-----|---------|
| `symbol` | e.g. `BZ=F`, `CL=F`, or `Urals` |
| `horizon_days` | int or `None` |
| `methods` | list of `{name, point, low, high, interpretation}` — same scalars as `MethodForecast` |
| `unavailable_reason` | string or `None` |
| `citations` | list of `[Forecast …]` **label strings** (not structured series) |
| `note` | LLM instruction: show both methods / do not average; or uncertainty / no invent / no Urals→Brent proxy |

The Ouroboros extension (`skills/oil_gas_forecast/plugin.py`) returns exactly this dict from `forecast_for_tool(query)`.

### `[Forecast …]` tags (`forecast_citations`)

- Success (one tag per method):  
  `[Forecast {name} {symbol} {Nd }{point} ({low}–{high})]`  
  Example shape: `[Forecast sarima BZ=F 90d 74.1 (70–78)]`.
- Unavailable: single tag  
  `[Forecast {symbol}: no series — {unavailable_reason}]`.

Tags encode the same **last-day scalars** as the JSON methods list. Nothing more.

---

## Daily history: returned to the tool?

**No.**

`run_forecast` loads a `pd.Series` of daily closes via `load_history` / `default_load_history` → `load_live_history` (Yahoo → Stooq → on-disk cache under `data/forecast_cache` / `FORECAST_CACHE_PATH`). That series is used only as endog for the two fits, then discarded. It is **not** a field on `ForecastResult` and **not** serialized in `forecast_for_tool`.

So: history is **not** a Live quote, and it is **not** Forecast output either — it is an internal fit input.

Tests assert tool payload shape (two methods, citations, Urals/uncertainty) and never assert history in the JSON (`tests/test_forecast.py`).

---

## SARIMA / Holt–Winters: full horizon path or last point + interval?

**Last-horizon-day point + interval only** reach the public types / tool / tags.

Inside the fit helpers (`_fit_sarima`, `_fit_holt`):

- SARIMA: `get_forecast(horizon)` yields a full `predicted_mean` and CI frame; code takes **`mean[-1]`** and the **last row** of the CI.
- Holt–Winters: `fitted.forecast(horizon)` yields a length-`horizon` array; `_interval` uses **`pred[-1]`** only, with a residual-based ±1.96 band scaled by `√horizon`.
- Fallbacks (fit failure) also build a length-`horizon` array, then again keep only the last point + band.

The intermediate arrays never attach to `MethodForecast`. Interpretation text states that the last point is day `{horizon}` — consistent with scalar-only export.

---

## Urals and Yahoo-fail / history-fail paths

### Urals

`detect_symbol` → `"urals"`. `run_forecast` returns immediately:

- `symbol="Urals"`, `methods=[]`, `unavailable_reason="no Yahoo series in v1"`
- no `load_history` call, no proxy with Brent

`forecast_for_tool` then adds uncertainty-style `note`, and one `[Forecast Urals: no series — …]` citation. Chart has **nothing numeric** to plot for Urals from Forecast.

### Live history failure (Yahoo / Stooq / thin series)

`load_live_history` order: Yahoo, then Stooq (if configured), then **cached CSV** from a prior successful fetch. If none yield ≥30 usable closes → `ForecastError`.

- `run_forecast`: re-raises `ForecastError` (does not return a soft `ForecastResult`).
- `forecast_for_tool`: catches `ForecastError` → soft `ForecastResult` with `methods=[]`, `unavailable_reason=str(exc)`, uncertainty `note` (“Do not invent prices or a CSV…”).

So the **tool/tag surface** for history failure looks like Urals: empty methods + reason + citations. The host never sees a partial path.

Note vs ADR 0009: ADR says no silent CSV fallback when Yahoo is down and the tool should error / show uncertainty. Implementation **does** retry Stooq and a **local cache of earlier live pulls**; only total absence of usable history becomes the uncertainty payload. That cache is still not exposed as Forecast or Live quote data to the chart.

---

## What a Dashboard chart can draw today vs what it must add

### Drawable from existing Forecast / tool payload (no new return fields)

- Two markers (or error bars) at the chosen horizon: SARIMA and Holt–Winters `point` / `low` / `high`.
- Labels from `symbol`, `horizon_days`, `interpretation`, and `[Forecast …]` strings.
- Empty / message state for Urals and history-unavailable.

Not a time-series Forecast ribbon — only horizon-end dots with bands.

### Stays inside `run_forecast` / loaders and never reaches tool or tags

- Full daily close **history** `pd.Series` (Yahoo / Stooq / cache).
- Full **method trajectories** (length-`horizon` means; SARIMA CI path except last row).

### What a chart would still have to add (without inventing new methods/series)

| Need | Option A — new return fields | Option B — host-side, current APIs |
|------|------------------------------|-------------------------------------|
| History line behind the Forecast | Extend `ForecastResult` / tool JSON with serialized history (dates + closes) | Call `load_live_history(symbol)` (or inject the same loader) on the host; do **not** treat that as a Live quote |
| Day-by-day Forecast paths | Return per-method arrays (mean ± optional band per step) from the fits | Re-fit or re-run forecast logic outside the tool (duplicates work; not on the skill payload today) |
| Interval ribbon over the horizon | Same as paths (CI only last day today for SARIMA export; Holt uses scalar band on last point) | Recompute |

Minimal chart without code changes to Forecast: **two error-bar points**. Anything that looks like “price history + two Forecast curves” requires either **new Forecast return fields** or the **host calling `load_live_history` itself** (and separately obtaining full trajectories, which are not available from the current public return at all).

---

## Skill / product constraints that affect plotting

- Always show **both** methods; **never average** (`SKILL.md`, tool `note`, tests).
- Default crude Brent (`BZ=F`); WTI if named (`CL=F`); Urals has no series.
- Oil-price figures in prose must come from these methods, Reports, or Web — history used for fitting is not licensed as a Live quote channel through this tool.
