from __future__ import annotations

import json
import math
import os
import statistics
from pathlib import Path

import pandas as pd

from oil_gas_analyst.forecast import FORECAST_METHOD_ORDER, detect_horizon, forecast_plot_payload

CHART_HISTORY_START = "2026-05-01"
CHART_DISPLAY_HISTORY_BDAYS = 22
CHART_Y_AXIS_MIN = 60.0

CHART_METHOD_LABELS = {
    "auto_arima": "AutoARIMA",
    "unobserved_components": "UnobservedComponents",
    "autoreg": "AutoReg",
}

CHART_METHOD_SHORT_LABELS = {
    "auto_arima": "AutoARIMA",
    "unobserved_components": "UCM",
    "autoreg": "AutoReg",
}

CHART_UNCERTAINTY_COPY = (
    "История Brent или Forecast недоступны. Не выдумываем цены — "
    "попробуйте обновить график позже."
)

_DEFAULT_HORIZON = 21


def _chart_payload_cache_path() -> Path:
    root = Path(os.environ.get("FORECAST_CACHE_PATH") or "data/forecast_cache")
    return root / "brent_chart_payload.json"


def load_cached_brent_chart_payload(*, horizon_days: int = _DEFAULT_HORIZON) -> dict | None:
    path = _chart_payload_cache_path()
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if int(payload.get("horizon_days") or 0) != horizon_days:
        return None
    if payload.get("unavailable_reason"):
        return None
    return payload


def save_brent_chart_payload_cache(payload: dict) -> None:
    if payload.get("unavailable_reason"):
        return
    path = _chart_payload_cache_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def chart_refresh_horizon(user_prompt: str) -> int | None:
    """Return a Forecast horizon to reload the pinned chart, or None."""
    q = user_prompt.casefold()
    if any(tok in q for tok in ("обнов", "refresh", "пересчитай график", "update chart")):
        return _DEFAULT_HORIZON
    if any(tok in q for tok in ("прогноз", "forecast", "спрогноз", "predict")):
        return detect_horizon(user_prompt)
    return None


def load_brent_chart_payload(
    *,
    horizon_days: int = _DEFAULT_HORIZON,
    load_history=None,
    history_start: str = CHART_HISTORY_START,
) -> dict:
    payload = forecast_plot_payload(
        symbol="BZ=F",
        horizon_days=horizon_days,
        load_history=load_history,
        history_start=history_start,
    )
    if load_history is None:
        save_brent_chart_payload_cache(payload)
    return payload


def forecast_model_consensus(payload: dict | None) -> dict[str, float | None | dict[str, float]]:
    """Average horizon-end point across the three forecast models."""
    if not payload or payload.get("unavailable_reason"):
        return {"average": None, "models": {}}
    methods = {m["name"]: m for m in payload.get("methods") or []}
    models: dict[str, float] = {}
    for name in FORECAST_METHOD_ORDER:
        point = (methods.get(name) or {}).get("point")
        if point is not None:
            models[name] = float(point)
    average = statistics.fmean(models.values()) if models else None
    return {"average": average, "models": models}


def _forecast_path_column(closes: list[float], path: list[float]) -> list[float]:
    last_close = float(closes[-1])
    return [math.nan] * (len(closes) - 1) + [last_close] + [float(v) for v in path]


def chart_dataframe_from_payload(payload: dict) -> pd.DataFrame | None:
    """Brent actuals plus Forecast paths for each method; never averaged."""
    if payload.get("unavailable_reason"):
        return None
    closes = payload.get("history_closes") or []
    dates = payload.get("history_dates") or []
    if not closes or not dates:
        return None
    methods = {m["name"]: m for m in payload.get("methods") or []}
    if not all(name in methods for name in FORECAST_METHOD_ORDER):
        return None

    hist_idx = pd.to_datetime(dates)
    horizon = int(payload.get("horizon_days") or _DEFAULT_HORIZON)
    fc_idx = pd.bdate_range(hist_idx[-1], periods=horizon + 1)[1:]
    actual_col = [float(v) for v in closes] + [math.nan] * len(fc_idx)
    index = pd.DatetimeIndex(list(hist_idx) + list(fc_idx))

    columns: dict[str, list[float]] = {"Факт": actual_col}
    for name in FORECAST_METHOD_ORDER:
        columns[CHART_METHOD_LABELS[name]] = _forecast_path_column(closes, methods[name]["path"])

    return pd.DataFrame(columns, index=index)


def chart_display_dataframe(
    frame: pd.DataFrame,
    *,
    history_bdays: int = CHART_DISPLAY_HISTORY_BDAYS,
) -> pd.DataFrame:
    """Last month of actuals plus the forecast window (for the dashboard chart)."""
    actual_idx = frame.index[frame["Факт"].notna()]
    if len(actual_idx) == 0:
        return frame
    start = actual_idx[-history_bdays] if len(actual_idx) > history_bdays else actual_idx[0]
    return frame.loc[frame.index >= start]


def brent_chart_altair(frame: pd.DataFrame, *, height: int = 280, y_min: float = CHART_Y_AXIS_MIN):
    """Multi-series Brent chart with a fixed lower Y bound."""
    import altair as alt

    plot = frame.reset_index(names="Дата")
    melted = plot.melt(id_vars=["Дата"], var_name="Серия", value_name="Цена").dropna(subset=["Цена"])
    return (
        alt.Chart(melted)
        .mark_line()
        .encode(
            x=alt.X("Дата:T", title=None),
            y=alt.Y("Цена:Q", title=None, scale=alt.Scale(domainMin=y_min, nice=True)),
            color=alt.Color("Серия:N", title=None),
        )
        .properties(height=height)
    )
