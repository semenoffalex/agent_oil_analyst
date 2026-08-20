from __future__ import annotations

import json
import math
import os
from pathlib import Path

import pandas as pd

from oil_gas_analyst.forecast import detect_horizon, forecast_plot_payload

CHART_HISTORY_START = "2026-01-01"

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
            "Факт": actual_col,
            "SARIMA": sarima_col,
            "Хольт–Винтерс": holt_col,
        },
        index=index,
    )
