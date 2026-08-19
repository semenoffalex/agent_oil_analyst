from __future__ import annotations

import math

import pandas as pd

from oil_gas_analyst.forecast import detect_horizon, forecast_plot_payload

CHART_UNCERTAINTY_COPY = (
    "История Brent или Forecast недоступны. Не выдумываем цены — "
    "попробуйте обновить график позже."
)

_DEFAULT_HORIZON = 21


def chart_refresh_horizon(user_prompt: str) -> int | None:
    """Return a Forecast horizon to reload the pinned chart, or None."""
    q = user_prompt.casefold()
    if any(tok in q for tok in ("обнов", "refresh", "пересчитай график", "update chart")):
        return _DEFAULT_HORIZON
    if any(tok in q for tok in ("прогноз", "forecast", "спрогноз", "predict")):
        return detect_horizon(user_prompt)
    return None


def load_brent_chart_payload(*, horizon_days: int = _DEFAULT_HORIZON, load_history=None) -> dict:
    return forecast_plot_payload(
        symbol="BZ=F",
        horizon_days=horizon_days,
        load_history=load_history,
    )


def kpi_from_chart_payload(payload: dict) -> dict[str, float | None]:
    methods = {m["name"]: m for m in payload.get("methods") or []}
    return {
        "close": payload.get("live_quote"),
        "sarima": (methods.get("sarima") or {}).get("point"),
        "holt_winters": (methods.get("holt_winters") or {}).get("point"),
    }


def chart_dataframe_from_payload(payload: dict) -> pd.DataFrame | None:
    """Brent actuals plus two Forecast paths; never averaged."""
    if payload.get("unavailable_reason"):
        return None
    closes = payload.get("history_closes") or []
    dates = payload.get("history_dates") or []
    if not closes or not dates:
        return None
    methods = {m["name"]: m for m in payload.get("methods") or []}
    sarima = methods.get("sarima")
    holt = methods.get("holt_winters")
    if not sarima or not holt:
        return None

    hist_idx = pd.to_datetime(dates)
    horizon = int(payload.get("horizon_days") or _DEFAULT_HORIZON)
    fc_idx = pd.bdate_range(hist_idx[-1], periods=horizon + 1)[1:]
    last_close = float(closes[-1])

    actual_col = [float(v) for v in closes] + [math.nan] * len(fc_idx)
    sarima_col = [math.nan] * (len(closes) - 1) + [last_close] + [float(v) for v in sarima["path"]]
    holt_col = [math.nan] * (len(closes) - 1) + [last_close] + [float(v) for v in holt["path"]]
    index = pd.DatetimeIndex(list(hist_idx) + list(fc_idx))

    return pd.DataFrame(
        {
            "Brent actual": actual_col,
            "SARIMA": sarima_col,
            "Holt-Winters": holt_col,
        },
        index=index,
    )
