import math

import numpy as np
import pandas as pd

from oil_gas_analyst.dashboard_chart import (
    chart_dataframe_from_payload,
    chart_refresh_horizon,
    kpi_from_chart_payload,
    load_brent_chart_payload,
)
from oil_gas_analyst.corpus_strip import corpus_strip_entries


def _series(n=80):
    idx = pd.bdate_range("2024-01-01", periods=n)
    rng = np.random.default_rng(0)
    values = 70 + np.cumsum(rng.normal(0, 0.5, n))
    return pd.Series(values, index=idx, name="close")


def _plot_payload():
    return load_brent_chart_payload(load_history=lambda symbol: _series())


def test_chart_dataframe_has_actual_and_two_forecast_series():
    payload = _plot_payload()
    frame = chart_dataframe_from_payload(payload)
    assert frame is not None
    assert "Brent actual" in frame.columns
    assert "SARIMA" in frame.columns
    assert "Holt-Winters" in frame.columns
    assert frame["Brent actual"].notna().sum() == len(payload["history_closes"])
    assert frame["SARIMA"].notna().sum() == payload["horizon_days"] + 1
    assert frame["Holt-Winters"].notna().sum() == payload["horizon_days"] + 1
    assert "average" not in frame.columns


def test_chart_dataframe_none_on_unavailable():
    payload = {"unavailable_reason": "no history", "history_closes": [], "methods": []}
    assert chart_dataframe_from_payload(payload) is None


def test_kpi_from_chart_payload():
    payload = _plot_payload()
    kpis = kpi_from_chart_payload(payload)
    assert kpis["close"] == payload["live_quote"]
    assert kpis["sarima"] is not None
    assert kpis["holt_winters"] is not None
    assert kpis["sarima"] != kpis["holt_winters"] or math.isclose(kpis["sarima"], kpis["holt_winters"])


def test_chart_refresh_horizon_detects_forecast_and_refresh():
    assert chart_refresh_horizon("обнови график Brent") == 21
    assert chart_refresh_horizon("спрогнозируй Brent на 3 месяца") == 90
    assert chart_refresh_horizon("What is OPEC demand?") is None


def test_corpus_strip_lists_agencies_when_samples_exist(tmp_path):
    for name in ("opec.pdf", "eia.pdf", "cbr.pdf"):
        (tmp_path / name).write_bytes(b"%PDF-1.4")
    cfg = {
        "samples": [
            {
                "path": str(tmp_path / "opec.pdf"),
                "title": "OPEC MOMR",
                "agency": "OPEC",
                "date": "2026-06",
                "excerpt": False,
            },
            {
                "path": str(tmp_path / "eia.pdf"),
                "title": "EIA STEO",
                "agency": "EIA",
                "date": "2026-08",
                "excerpt": True,
            },
            {
                "path": str(tmp_path / "cbr.pdf"),
                "title": "CBR trends",
                "agency": "CBR",
                "date": "2026-07",
                "excerpt": False,
            },
        ]
    }
    entries = corpus_strip_entries(cfg=cfg, samples_dir=tmp_path)
    agencies = {entry.agency for entry in entries}
    assert agencies == {"OPEC", "EIA", "CBR"}
    assert any("excerpt" in entry.label() for entry in entries)
