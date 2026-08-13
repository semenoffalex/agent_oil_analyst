from oil_gas_analyst.forecast import ForecastError, detect_symbol, run_forecast
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


def test_run_forecast_returns_two_methods_with_intervals():
    result = run_forecast("спрогнозируй цену Brent на 3 месяца", load_history=lambda symbol: _series())
    assert isinstance(result, ForecastResult)
    assert result.unavailable_reason is None
    names = {m.name for m in result.methods}
    assert names == {"sarima", "holt_winters"}
    for method in result.methods:
        assert method.point is not None
        assert method.low is not None
        assert method.high is not None
        assert method.low <= method.point <= method.high


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
