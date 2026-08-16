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
