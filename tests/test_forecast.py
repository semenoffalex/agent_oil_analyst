from oil_gas_analyst.forecast import ForecastError, detect_horizon, detect_symbol, run_forecast
from oil_gas_analyst.types import ForecastResult
import pandas as pd
import numpy as np


def _series(n=400):
    idx = pd.bdate_range("2024-01-01", periods=n)
    rng = np.random.default_rng(0)
    values = 70 + np.cumsum(rng.normal(0, 0.5, n))
    return pd.Series(values, index=idx, name="close")


def test_detect_urals_has_no_symbol():
    assert detect_symbol("спрогнозируй Urals на 3 месяца") == "urals"
    assert detect_symbol("forecast Brent") == "BZ=F"
    assert detect_symbol("predict WTI") == "CL=F"


def test_detect_horizon_closed_list():
    assert detect_horizon("Построй свой прогноз.") == 90
    assert detect_horizon("спрогнозируй Brent на ближайший месяц") == 21
    assert detect_horizon("спрогнозируй цену Brent на 3 месяца") == 90
    assert detect_horizon("forecast WTI for a year") == 252
    assert detect_horizon("predict Brent in 12 months") == 252


def test_run_forecast_returns_two_methods_with_intervals():
    result = run_forecast("спрогнозируй цену Brent на 3 месяца", load_history=lambda symbol: _series())
    assert isinstance(result, ForecastResult)
    assert result.unavailable_reason is None
    assert result.horizon_days == 90
    names = {m.name for m in result.methods}
    assert names == {"sarima", "holt_winters"}
    for method in result.methods:
        assert method.point is not None
        assert method.low is not None
        assert method.high is not None
        assert method.low <= method.point <= method.high
        assert "90" in method.interpretation


def test_month_horizon_is_not_the_quarter_point():
    hist = lambda symbol: _series()
    month = run_forecast("спрогнозируй Brent на ближайший месяц", load_history=hist)
    quarter = run_forecast("спрогнозируй цену Brent на 3 месяца", load_history=hist)
    bare = run_forecast("Построй свой прогноз.", load_history=hist)
    assert month.horizon_days == 21
    assert quarter.horizon_days == 90
    assert bare.horizon_days == 90
    month_pts = {m.name: (m.point, m.low, m.high) for m in month.methods}
    quarter_pts = {m.name: (m.point, m.low, m.high) for m in quarter.methods}
    assert month_pts != quarter_pts


def test_urals_unavailable():
    result = run_forecast("forecast Urals", load_history=lambda symbol: _series())
    assert result.methods == []
    assert result.unavailable_reason is not None
    assert "no" in result.unavailable_reason.lower()


def test_history_failure_raises():
    def boom(symbol):
        raise RuntimeError("yahoo")

    try:
        run_forecast("predict Brent", load_history=boom)
        assert False, "expected ForecastError"
    except ForecastError:
        pass


def test_stooq_used_when_yahoo_empty(tmp_path):
    from oil_gas_analyst.forecast import load_live_history

    calls: list[str] = []

    def yahoo(symbol: str):
        calls.append("yahoo")
        return pd.Series(dtype=float)

    def stooq(symbol: str):
        calls.append("stooq")
        return _series()

    out = load_live_history("BZ=F", fetchers=[yahoo, stooq], cache_dir=tmp_path)
    assert calls == ["yahoo", "stooq"]
    assert len(out) >= 30
    cached = pd.read_csv(tmp_path / "BZ-F.csv")
    assert list(cached.columns) == ["date", "close"]
    assert "Unnamed" not in "".join(cached.columns)


def test_cache_used_when_live_sources_fail(tmp_path):
    from oil_gas_analyst.forecast import load_live_history

    load_live_history("BZ=F", fetchers=[lambda symbol: _series()], cache_dir=tmp_path)

    def boom(symbol: str):
        raise RuntimeError("blocked")

    out = load_live_history("BZ=F", fetchers=[boom, boom], cache_dir=tmp_path)
    assert len(out) >= 30


def test_no_live_history_or_cache_raises(tmp_path):
    from oil_gas_analyst.forecast import load_live_history

    def boom(symbol: str):
        raise RuntimeError("blocked")

    try:
        load_live_history("BZ=F", fetchers=[boom], cache_dir=tmp_path)
        assert False, "expected ForecastError"
    except ForecastError:
        pass


def test_forecast_for_tool_shows_two_methods_and_no_average():
    from oil_gas_analyst.forecast import forecast_for_tool

    payload = forecast_for_tool(
        "спрогнозируй цену Brent на 3 месяца",
        load_history=lambda symbol: _series(),
    )
    names = {m["name"] for m in payload["methods"]}
    assert names == {"sarima", "holt_winters"}
    assert "average" not in payload
    assert payload.get("unavailable_reason") in (None, "")
    assert len(payload["citations"]) == 2
    assert all(c.startswith("[Forecast ") for c in payload["citations"])
    blob = " ".join(payload["citations"]).lower()
    assert "sarima" in blob and "holt" in blob


def test_forecast_for_tool_defaults_to_brent_and_honors_wti():
    from oil_gas_analyst.forecast import forecast_for_tool

    bare = forecast_for_tool("What is the oil price path?", load_history=lambda symbol: _series())
    assert bare["symbol"] in {"BZ=F", "Brent"}
    wti = forecast_for_tool("forecast WTI", load_history=lambda symbol: _series())
    assert wti["symbol"] == "CL=F"


def test_forecast_for_tool_urals_has_no_series_and_no_brent_proxy():
    from oil_gas_analyst.forecast import forecast_for_tool

    payload = forecast_for_tool("forecast Urals", load_history=lambda symbol: _series())
    assert payload["methods"] == []
    assert payload["unavailable_reason"]
    assert "brent" not in (payload["unavailable_reason"] or "").casefold()
    assert payload["symbol"].lower() == "urals"
    assert any("Forecast" in c for c in payload["citations"])


def test_forecast_for_tool_history_failure_is_uncertainty():
    from oil_gas_analyst.forecast import forecast_for_tool

    def boom(symbol):
        raise RuntimeError("yahoo blocked")

    payload = forecast_for_tool("predict Brent", load_history=boom)
    assert payload["methods"] == []
    note = (payload.get("note") or payload.get("unavailable_reason") or "").lower()
    assert "uncertain" in note or "unavail" in note or "invent" in note
    assert "78.40" not in str(payload)
