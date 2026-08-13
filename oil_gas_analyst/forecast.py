from __future__ import annotations

import re
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd
import yaml
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.statespace.sarimax import SARIMAX

from oil_gas_analyst.types import ForecastResult, MethodForecast

_CONFIG = Path(__file__).resolve().parent.parent / "config" / "forecast.yaml"

HistoryLoader = Callable[[str], pd.Series]


class ForecastError(RuntimeError):
    pass


def load_forecast_config(path: Path | None = None) -> dict:
    return yaml.safe_load((path or _CONFIG).read_text(encoding="utf-8"))


def detect_symbol(question: str, config: dict | None = None) -> str:
    cfg = config or load_forecast_config()
    q = question.casefold()
    if re.search(r"\burals\b", q) or "юралс" in q or "urals" in q:
        return "urals"
    if re.search(r"\bwti\b", q):
        return str(cfg["symbols"]["wti"])
    return str(cfg["symbols"].get("brent", cfg.get("default_symbol", "BZ=F")))


def _interval(pred: np.ndarray, resid_std: float) -> tuple[float, float, float]:
    point = float(pred[-1])
    band = 1.96 * float(max(resid_std, 1e-6))
    return point, point - band, point + band


def _fit_sarima(y: pd.Series, horizon: int) -> MethodForecast:
    endog = y.astype(float)
    try:
        fitted = SARIMAX(
            endog,
            order=(1, 1, 1),
            seasonal_order=(1, 0, 0, 5),
            enforce_stationarity=False,
            enforce_invertibility=False,
        ).fit(disp=False)
        fc = fitted.get_forecast(horizon)
        mean = np.asarray(fc.predicted_mean)
        ci = fc.conf_int()
        low = float(np.asarray(ci.iloc[:, 0])[-1])
        high = float(np.asarray(ci.iloc[:, 1])[-1])
        point = float(mean[-1])
        if low > high:
            low, high = high, low
        return MethodForecast(
            name="sarima",
            point=point,
            low=low,
            high=high,
            interpretation="SARIMA on daily closes; last point is the horizon.",
        )
    except Exception:
        resid_std = float(endog.diff().std() or 1.0)
        drift = float(endog.diff().mean() or 0.0)
        pred = endog.iloc[-1] + drift * np.arange(1, horizon + 1)
        point, low, high = _interval(pred, resid_std * np.sqrt(horizon))
        return MethodForecast(
            name="sarima",
            point=point,
            low=low,
            high=high,
            interpretation="SARIMA fallback (random-walk with drift) after fit failure.",
        )


def _fit_holt(y: pd.Series, horizon: int) -> MethodForecast:
    endog = y.astype(float)
    periods = 5 if len(endog) >= 20 else None
    try:
        model = ExponentialSmoothing(
            endog,
            trend="add",
            seasonal="add" if periods else None,
            seasonal_periods=periods,
        )
        fitted = model.fit(optimized=True)
        fc = np.asarray(fitted.forecast(horizon))
        resid_std = float(np.std(fitted.resid)) if getattr(fitted, "resid", None) is not None else float(endog.diff().std() or 1)
        point, low, high = _interval(fc, resid_std * np.sqrt(horizon))
        return MethodForecast(
            name="holt_winters",
            point=point,
            low=low,
            high=high,
            interpretation="Holt–Winters additive; last point is the horizon.",
        )
    except Exception:
        resid_std = float(endog.diff().std() or 1.0)
        pred = np.full(horizon, float(endog.iloc[-1]))
        point, low, high = _interval(pred, resid_std * np.sqrt(horizon))
        return MethodForecast(
            name="holt_winters",
            point=point,
            low=low,
            high=high,
            interpretation="Holt–Winters fallback to last close after fit failure.",
        )


def default_load_history(symbol: str) -> pd.Series:
    import yfinance as yf

    cfg = load_forecast_config()
    period = cfg.get("history_period", "5y")
    interval = cfg.get("interval", "1d")
    data = yf.download(symbol, period=period, interval=interval, progress=False, auto_adjust=True)
    if data is None or data.empty:
        raise ForecastError(f"yfinance returned no rows for {symbol}")
    close = data["Close"]
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]
    close = close.dropna()
    if close.empty:
        raise ForecastError(f"yfinance Close empty for {symbol}")
    return close


def run_forecast(question: str, load_history: HistoryLoader | None = None) -> ForecastResult:
    cfg = load_forecast_config()
    symbol = detect_symbol(question, cfg)
    if symbol == "urals":
        return ForecastResult(
            symbol="Urals",
            methods=[],
            unavailable_reason="no Yahoo series in v1",
        )
    loader = load_history or default_load_history
    try:
        history = loader(symbol)
    except ForecastError:
        raise
    except Exception as exc:
        raise ForecastError(str(exc)) from exc
    if history is None or len(history) < 30:
        raise ForecastError("not enough price history")
    horizon = int(cfg.get("horizon_default_days", 90))
    methods = [_fit_sarima(history, horizon), _fit_holt(history, horizon)]
    return ForecastResult(symbol=symbol, methods=methods)
