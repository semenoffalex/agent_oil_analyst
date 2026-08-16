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
            interpretation=f"SARIMA on daily closes; last point is day {horizon}.",
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
            interpretation=f"SARIMA fallback (random-walk with drift) after fit failure; day {horizon}.",
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
            interpretation=f"Holt–Winters additive; last point is day {horizon}.",
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
            interpretation=f"Holt–Winters fallback to last close after fit failure; day {horizon}.",
        )


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
    methods = [_fit_sarima(history, horizon), _fit_holt(history, horizon)]
    return ForecastResult(symbol=symbol, methods=methods, horizon_days=horizon)
