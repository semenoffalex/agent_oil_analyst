from __future__ import annotations

import io
import os
import re
import urllib.request
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd
import yaml
from statsmodels.tsa.ar_model import AutoReg, ar_select_order
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.statespace.structural import UnobservedComponents

from oil_gas_analyst.settings import maybe_traceable
from oil_gas_analyst.types import ForecastPlotPayload, ForecastResult, MethodForecast, MethodPathForecast

_CONFIG = Path(__file__).resolve().parent.parent / "config" / "forecast.yaml"

FORECAST_METHOD_ORDER = ("auto_arima", "unobserved_components", "autoreg")

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


def detect_horizon(question: str, config: dict | None = None) -> int:
    cfg = config or load_forecast_config()
    default = int(cfg.get("horizon_default_days", 90))
    q = question.casefold()
    ranked: list[tuple[int, int]] = []
    for rule in cfg.get("horizon_phrases") or []:
        days = int(rule["days"])
        for phrase in rule.get("phrases") or []:
            p = str(phrase).casefold().strip()
            if p and p in q:
                ranked.append((len(p), days))
    if not ranked:
        return default
    ranked.sort(reverse=True)
    return ranked[0][1]


def _interval(pred: np.ndarray, resid_std: float) -> tuple[float, float, float]:
    point = float(pred[-1])
    band = 1.96 * float(max(resid_std, 1e-6))
    return point, point - band, point + band


def _endog_for_fit(y: pd.Series) -> pd.Series:
    """RangeIndex so get_forecast works when Yahoo/Stooq dates have no freq."""
    values = pd.to_numeric(y, errors="coerce").dropna().astype(float)
    return pd.Series(values.to_numpy(), index=pd.RangeIndex(len(values)), name="close")


def _path_from_pred(pred: np.ndarray) -> tuple[float, ...]:
    return tuple(float(x) for x in np.asarray(pred, dtype=float).ravel())


def _random_walk_fallback(
    endog: pd.Series,
    horizon: int,
    *,
    name: str,
    label: str,
) -> tuple[MethodForecast, tuple[float, ...]]:
    resid_std = float(endog.diff().std() or 1.0)
    drift = float(endog.diff().mean() or 0.0)
    pred = endog.iloc[-1] + drift * np.arange(1, horizon + 1)
    point, low, high = _interval(pred, resid_std * np.sqrt(horizon))
    return (
        MethodForecast(
            name=name,
            point=point,
            low=low,
            high=high,
            interpretation=f"{label} fallback (random-walk with drift) after fit failure; day {horizon}.",
        ),
        _path_from_pred(pred),
    )


def _method_from_forecast(
    *,
    name: str,
    interpretation: str,
    fitted,
    horizon: int,
) -> tuple[MethodForecast, tuple[float, ...]]:
    if hasattr(fitted, "get_forecast"):
        fc = fitted.get_forecast(horizon)
        mean = np.asarray(fc.predicted_mean)
        ci = np.asarray(fc.conf_int())
    else:
        n = len(np.asarray(fitted.model.endog).ravel())
        pred = fitted.get_prediction(start=n, end=n + horizon - 1)
        mean = np.asarray(pred.predicted_mean)
        ci = np.asarray(pred.conf_int())
    low = float(ci[-1, 0])
    high = float(ci[-1, 1])
    point = float(mean[-1])
    if low > high:
        low, high = high, low
    return (
        MethodForecast(
            name=name,
            point=point,
            low=low,
            high=high,
            interpretation=interpretation,
        ),
        _path_from_pred(mean),
    )


def _fit_auto_arima(y: pd.Series, horizon: int) -> MethodForecast:
    forecast, _ = _fit_auto_arima_with_path(y, horizon)
    return forecast


def _fit_auto_arima_with_path(y: pd.Series, horizon: int) -> tuple[MethodForecast, tuple[float, ...]]:
    endog = _endog_for_fit(y)
    cfg = load_forecast_config()
    max_p = int(cfg.get("auto_arima_max_p", 2))
    max_d = int(cfg.get("auto_arima_max_d", 1))
    max_q = int(cfg.get("auto_arima_max_q", 2))
    best_aic = float("inf")
    best_order = (1, 1, 1)
    for p in range(max_p + 1):
        for d in range(max_d + 1):
            for q in range(max_q + 1):
                if p == d == q == 0:
                    continue
                try:
                    res = ARIMA(endog, order=(p, d, q)).fit()
                    if res.aic < best_aic:
                        best_aic = res.aic
                        best_order = (p, d, q)
                except Exception:
                    continue
    try:
        fitted = ARIMA(endog, order=best_order).fit()
        return _method_from_forecast(
            name="auto_arima",
            interpretation=f"AutoARIMA order={best_order}; last point is day {horizon}.",
            fitted=fitted,
            horizon=horizon,
        )
    except Exception:
        return _random_walk_fallback(endog, horizon, name="auto_arima", label="AutoARIMA")


def _fit_unobserved_components(y: pd.Series, horizon: int) -> MethodForecast:
    forecast, _ = _fit_unobserved_components_with_path(y, horizon)
    return forecast


def _fit_unobserved_components_with_path(
    y: pd.Series, horizon: int
) -> tuple[MethodForecast, tuple[float, ...]]:
    endog = _endog_for_fit(y)
    try:
        fitted = UnobservedComponents(endog, level="local linear trend").fit(disp=False)
        return _method_from_forecast(
            name="unobserved_components",
            interpretation=f"UnobservedComponents local linear trend; last point is day {horizon}.",
            fitted=fitted,
            horizon=horizon,
        )
    except Exception:
        return _random_walk_fallback(
            endog,
            horizon,
            name="unobserved_components",
            label="UnobservedComponents",
        )


def _fit_autoreg(y: pd.Series, horizon: int) -> MethodForecast:
    forecast, _ = _fit_autoreg_with_path(y, horizon)
    return forecast


def _fit_autoreg_with_path(y: pd.Series, horizon: int) -> tuple[MethodForecast, tuple[float, ...]]:
    endog = _endog_for_fit(y)
    try:
        maxlag = min(int(load_forecast_config().get("autoreg_max_lag", 21)), max(1, len(endog) // 3))
        sel = ar_select_order(endog, maxlag=maxlag, ic="aic")
        lags = sel.ar_lags or [1]
        fitted = AutoReg(endog, lags=lags).fit()
        return _method_from_forecast(
            name="autoreg",
            interpretation=f"AutoReg lags={list(lags)}; last point is day {horizon}.",
            fitted=fitted,
            horizon=horizon,
        )
    except Exception:
        return _random_walk_fallback(endog, horizon, name="autoreg", label="AutoReg")


def _fit_all_methods(history: pd.Series, horizon: int) -> list[MethodForecast]:
    return [
        _fit_auto_arima(history, horizon),
        _fit_unobserved_components(history, horizon),
        _fit_autoreg(history, horizon),
    ]


def _fit_all_methods_with_paths(history: pd.Series, horizon: int) -> list[tuple[MethodForecast, tuple[float, ...]]]:
    return [
        _fit_auto_arima_with_path(history, horizon),
        _fit_unobserved_components_with_path(history, horizon),
        _fit_autoreg_with_path(history, horizon),
    ]


_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def _apply_yahoo_user_agent(ua: str) -> None:
    try:
        import yfinance.utils as yu

        headers = getattr(yu, "user_agent_headers", None)
        if isinstance(headers, dict):
            headers["User-Agent"] = ua
            headers["user-agent"] = ua
    except Exception:
        pass


def _close_from_frame(data: pd.DataFrame | pd.Series | None) -> pd.Series | None:
    if data is None or getattr(data, "empty", True):
        return None
    if isinstance(data, pd.Series):
        close = data
    else:
        try:
            close = data["Close"]
        except Exception:
            try:
                close = data["close"]
            except Exception:
                return None
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]
    close = pd.to_numeric(close, errors="coerce").dropna()
    close.name = "close"
    return close.sort_index() if not close.empty else None


def _usable_close(series: pd.Series | None) -> pd.Series | None:
    if series is None:
        return None
    close = pd.to_numeric(series, errors="coerce").dropna().sort_index()
    close.name = "close"
    if close.empty or len(close) < 30:
        return None
    return close


def _cache_path(cache_dir: Path, symbol: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", symbol).strip("-") or "symbol"
    return Path(cache_dir) / f"{safe}.csv"


def _save_cache(cache_dir: Path, symbol: str, series: pd.Series) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    frame = series.dropna().rename("close").to_frame().reset_index()
    frame.columns = ["date", "close"]
    frame.to_csv(_cache_path(cache_dir, symbol), index=False)


def _read_cache(cache_dir: Path, symbol: str) -> pd.Series | None:
    path = _cache_path(cache_dir, symbol)
    if not path.is_file():
        return None
    frame = pd.read_csv(path)
    if "date" not in frame.columns or "close" not in frame.columns:
        return None
    series = pd.Series(
        pd.to_numeric(frame["close"], errors="coerce").values,
        index=pd.to_datetime(frame["date"]),
        name="close",
    )
    return series.dropna().sort_index()


def _fetch_yahoo(symbol: str, period: str, interval: str) -> pd.Series:
    import yfinance as yf

    ua = os.environ.get("FORECAST_USER_AGENT", _UA)
    _apply_yahoo_user_agent(ua)
    try:
        hist = yf.Ticker(symbol).history(period=period, interval=interval, auto_adjust=True, timeout=30)
        series = _close_from_frame(hist)
        if series is not None:
            return series
    except Exception:
        pass
    try:
        data = yf.download(
            symbol,
            period=period,
            interval=interval,
            progress=False,
            auto_adjust=True,
            threads=False,
            timeout=30,
        )
    except TypeError:
        data = yf.download(symbol, period=period, interval=interval, progress=False, auto_adjust=True)
    series = _close_from_frame(data)
    if series is None:
        raise ForecastError(f"yfinance returned no rows for {symbol}")
    return series


def _fetch_stooq(symbol: str, config: dict) -> pd.Series:
    code = (config.get("stooq_symbols") or {}).get(symbol)
    if not code:
        raise ForecastError(f"no Stooq symbol for {symbol}")
    url = f"https://stooq.com/q/d/l/?s={code}&i=d"
    ua = os.environ.get("FORECAST_USER_AGENT", _UA)
    req = urllib.request.Request(url, headers={"User-Agent": ua})
    with urllib.request.urlopen(req, timeout=20) as resp:
        raw = resp.read()
    frame = pd.read_csv(io.BytesIO(raw))
    if frame is None or frame.empty:
        raise ForecastError(f"Stooq returned no rows for {symbol}")
    date_col = "Date" if "Date" in frame.columns else "date"
    close_col = "Close" if "Close" in frame.columns else "close"
    if date_col not in frame.columns or close_col not in frame.columns:
        raise ForecastError(f"Stooq returned no rows for {symbol}")
    series = pd.Series(
        pd.to_numeric(frame[close_col], errors="coerce").values,
        index=pd.to_datetime(frame[date_col]),
        name="close",
    )
    series = series.dropna().sort_index()
    if series.empty:
        raise ForecastError(f"Stooq Close empty for {symbol}")
    return series


def load_live_history(
    symbol: str,
    *,
    fetchers: list[HistoryLoader] | None = None,
    cache_dir: Path | str | None = None,
    period: str | None = None,
    interval: str | None = None,
) -> pd.Series:
    cfg = load_forecast_config()
    cache = Path(
        str(
            cache_dir
            if cache_dir is not None
            else os.environ.get("FORECAST_CACHE_PATH") or cfg.get("cache_dir") or "data/forecast_cache"
        )
    )
    period = period or str(cfg.get("history_period", "5y"))
    interval = interval or str(cfg.get("interval", "1d"))
    if fetchers is None:
        fetchers = [
            lambda s, p=period, i=interval: _fetch_yahoo(s, p, i),
            lambda s: _fetch_stooq(s, cfg),
        ]
    last_err: Exception | None = None
    for fetch in fetchers:
        try:
            series = _usable_close(fetch(symbol))
            if series is not None:
                _save_cache(cache, symbol, series)
                return series
        except Exception as exc:
            last_err = exc
    cached = _usable_close(_read_cache(cache, symbol))
    if cached is not None:
        return cached
    raise ForecastError(str(last_err) if last_err else f"no price history for {symbol}")


def default_load_history(symbol: str) -> pd.Series:
    return load_live_history(symbol)


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
    horizon = detect_horizon(question, cfg)
    methods = _fit_all_methods(history, horizon)
    return ForecastResult(symbol=symbol, methods=methods, horizon_days=horizon)


@maybe_traceable("analyst.run_forecast", run_type="tool")
def forecast_for_tool(question: str, load_history: HistoryLoader | None = None) -> dict:
    """Forecast calculation for the Ouroboros extension: three methods, no average, no fake CSV."""

    from oil_gas_analyst.turn import forecast_citations

    try:
        result = run_forecast(question, load_history=load_history)
    except ForecastError as exc:
        result = ForecastResult(
            symbol=detect_symbol(question),
            methods=[],
            unavailable_reason=str(exc),
        )
    citations = [cite.label for cite in forecast_citations(result)]
    methods = [
        {
            "name": method.name,
            "point": method.point,
            "low": method.low,
            "high": method.high,
            "interpretation": method.interpretation,
        }
        for method in result.methods
    ]
    if result.unavailable_reason:
        note = (
            "Forecast history is unavailable. Do not invent prices or a CSV. "
            "Say you are uncertain. Do not proxy Urals with Brent."
        )
    else:
        note = (
            "Show AutoARIMA, UnobservedComponents, and AutoReg with intervals. Do not average them. "
            "Copy citation labels verbatim. Oil-price figures in prose must come from "
            "these methods, Reports, or Web — not invented."
        )
    return {
        "symbol": result.symbol,
        "horizon_days": result.horizon_days,
        "methods": methods,
        "unavailable_reason": result.unavailable_reason,
        "citations": citations,
        "note": note,
    }


def _history_series_to_rows(history: pd.Series) -> tuple[tuple[str, ...], tuple[float, ...]]:
    dates: list[str] = []
    closes: list[float] = []
    for idx, value in history.items():
        dates.append(pd.Timestamp(idx).date().isoformat())
        closes.append(float(value))
    return tuple(dates), tuple(closes)


def _plot_payload_from_history(
    symbol: str,
    history: pd.Series,
    *,
    horizon_days: int,
) -> ForecastPlotPayload:
    fitted = _fit_all_methods_with_paths(history, horizon_days)
    dates, closes = _history_series_to_rows(history)
    methods = tuple(
        MethodPathForecast(
            name=method.name,
            point=float(method.point),
            low=float(method.low),
            high=float(method.high),
            path=path,
            interpretation=method.interpretation,
        )
        for method, path in fitted
    )
    return ForecastPlotPayload(
        symbol=symbol,
        horizon_days=horizon_days,
        history_dates=dates,
        history_closes=closes,
        live_quote=float(history.iloc[-1]),
        methods=methods,
    )


def forecast_plot_payload_to_dict(payload: ForecastPlotPayload) -> dict:
    return {
        "symbol": payload.symbol,
        "horizon_days": payload.horizon_days,
        "history_dates": list(payload.history_dates),
        "history_closes": list(payload.history_closes),
        "live_quote": payload.live_quote,
        "methods": [
            {
                "name": method.name,
                "point": method.point,
                "low": method.low,
                "high": method.high,
                "path": list(method.path),
                "interpretation": method.interpretation,
            }
            for method in payload.methods
        ],
        "unavailable_reason": payload.unavailable_reason,
    }


def _history_from_start(history: pd.Series, history_start: str) -> pd.Series:
    start = pd.Timestamp(history_start)
    index = history.index
    if isinstance(index, pd.DatetimeIndex) and index.tz is not None:
        start = start.tz_localize(index.tz) if start.tzinfo is None else start.tz_convert(index.tz)
    elif start.tzinfo is not None:
        start = start.tz_localize(None)
    return history[index >= start]


@maybe_traceable("analyst.forecast_plot_payload", run_type="tool")
def forecast_plot_payload(
    *,
    symbol: str = "BZ=F",
    horizon_days: int = 21,
    load_history: HistoryLoader | None = None,
    history_start: str | None = None,
) -> dict:
    """Brent history plus per-step AutoARIMA, UnobservedComponents, and AutoReg paths for the Dashboard chart."""

    if symbol.casefold() == "urals":
        payload = ForecastPlotPayload(
            symbol="Urals",
            horizon_days=horizon_days,
            history_dates=(),
            history_closes=(),
            live_quote=None,
            methods=(),
            unavailable_reason="no Yahoo series in v1",
        )
        return forecast_plot_payload_to_dict(payload)

    loader = load_history or default_load_history
    try:
        history = loader(symbol)
    except ForecastError as exc:
        payload = ForecastPlotPayload(
            symbol=symbol,
            horizon_days=horizon_days,
            history_dates=(),
            history_closes=(),
            live_quote=None,
            methods=(),
            unavailable_reason=str(exc),
        )
        return forecast_plot_payload_to_dict(payload)
    except Exception as exc:
        payload = ForecastPlotPayload(
            symbol=symbol,
            horizon_days=horizon_days,
            history_dates=(),
            history_closes=(),
            live_quote=None,
            methods=(),
            unavailable_reason=str(exc),
        )
        return forecast_plot_payload_to_dict(payload)

    if history_start:
        history = _history_from_start(history, history_start)

    if history is None or len(history) < 30:
        payload = ForecastPlotPayload(
            symbol=symbol,
            horizon_days=horizon_days,
            history_dates=(),
            history_closes=(),
            live_quote=None,
            methods=(),
            unavailable_reason="not enough price history",
        )
        return forecast_plot_payload_to_dict(payload)

    return forecast_plot_payload_to_dict(
        _plot_payload_from_history(symbol, history, horizon_days=horizon_days)
    )
