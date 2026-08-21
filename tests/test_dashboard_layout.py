"""Dashboard layout — chat above the fold, no sidebar logout."""

from oil_gas_analyst.dashboard import chat_turn_in_progress


def test_chat_turn_in_progress():
    import concurrent.futures

    done = concurrent.futures.Future()
    done.set_result("ok")
    pending = concurrent.futures.Future()
    assert chat_turn_in_progress(None) is False
    assert chat_turn_in_progress(done) is False
    assert chat_turn_in_progress(pending) is True


def test_dashboard_puts_chat_before_chart_and_news_rail_at_top():
    from pathlib import Path

    text = Path("oil_gas_analyst/dashboard.py").read_text(encoding="utf-8")
    main_block = text.split("def main() -> None:", 1)[1]
    kpi_pos = main_block.index("_render_kpi_corpus_row(")
    rail_pos = main_block.index("_render_news_pills(")
    chart_pos = main_block.index("_render_chart_panel(")
    chat_pos = main_block.index("_render_chat_panel(")
    assert kpi_pos < rail_pos < chart_pos < chat_pos
    assert "Обновить график" not in main_block
    assert "st.divider()" not in main_block
    assert "_render_news_pills" in text
    assert "_render_kpi_corpus_row" in text
    assert "_render_corpus_pill" in text
    assert "TOP_NEWS_RAIL_TITLE" in text
    assert "max_cards=5" in text
    assert "rail_col" not in main_block
    assert "_start_chat_turn" in text
    assert "_logout_demo_session" in text
    assert "on_click=_logout_demo_session" not in text
    assert "stSidebar" in text
    assert "with st.sidebar" not in text
    assert "_CHAT_HINT" in text
    assert "_CHAT_INPUT_PLACEHOLDER" in text
    assert "st.chat_message" in text
    assert "_THINKING_COPY" in text
    assert "30–60 секунд" in text
    assert "_poll_chat_future" in text
    assert "_render_thinking_indicator" in text
    assert "assistant_box = st.chat_message(\"assistant\")" in text
    assert "_render_cached_spinner(assistant_box," in text
    assert "stCacheSpinner" in text
    assert "_hydrate_from_disk_caches" in text
    assert "_hydrate_news_from_disk" in text
    assert "_start_background_refreshes" in text


def test_dashboard_page_config_collapses_sidebar():
    from pathlib import Path

    text = Path("oil_gas_analyst/dashboard.py").read_text(encoding="utf-8")
    assert 'initial_sidebar_state="collapsed"' in text


def test_rail_exclusions_hide_wikipedia():
    from oil_gas_analyst.session_start_web import visible_rail_hits

    payload = {
        "hits": [
            {
                "title": "Нефть — Википедия",
                "url": "https://ru.wikipedia.org/wiki/Нефть",
                "snippet": "wiki",
                "citation": "[Источник: ru.wikipedia.org, web]",
                "denied": False,
            },
            {
                "title": "Brent rises",
                "url": "https://www.reuters.com/markets/brent",
                "snippet": "Oil up",
                "citation": "[Источник: reuters.com, web]",
                "denied": False,
            },
        ],
        "count": 2,
    }
    visible = visible_rail_hits(payload)
    assert len(visible) == 1
    assert visible[0].outlet == "reuters.com"


import math

import numpy as np
import pandas as pd

from oil_gas_analyst.corpus_strip import corpus_strip_entries
from oil_gas_analyst.dashboard_chart import (
    CHART_HISTORY_START,
    chart_dataframe_from_payload,
    chart_refresh_horizon,
    kpi_from_chart_payload,
    load_brent_chart_payload,
    load_cached_brent_chart_payload,
    save_brent_chart_payload_cache,
)


def _series(n=80):
    idx = pd.bdate_range("2026-05-01", periods=n)
    rng = np.random.default_rng(0)
    values = 70 + np.cumsum(rng.normal(0, 0.5, n))
    return pd.Series(values, index=idx, name="close")


def _plot_payload():
    return load_brent_chart_payload(load_history=lambda symbol: _series())


def test_chart_payload_disk_cache_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("FORECAST_CACHE_PATH", str(tmp_path))
    payload = load_brent_chart_payload(load_history=lambda symbol: _series())
    save_brent_chart_payload_cache(payload)
    cached = load_cached_brent_chart_payload(horizon_days=payload["horizon_days"])
    assert cached is not None
    assert cached["live_quote"] == payload["live_quote"]
    save_brent_chart_payload_cache({"unavailable_reason": "skip"})
    assert load_cached_brent_chart_payload(horizon_days=payload["horizon_days"]) == cached


def test_chart_dataframe_has_actual_and_two_forecast_series():
    payload = _plot_payload()
    frame = chart_dataframe_from_payload(payload)
    assert frame is not None
    assert "Факт" in frame.columns
    assert "SARIMA" in frame.columns
    assert "Хольт–Винтерс" in frame.columns
    assert frame["Факт"].notna().sum() == len(payload["history_closes"])
    assert frame["SARIMA"].notna().sum() == payload["horizon_days"] + 1
    assert frame["Хольт–Винтерс"].notna().sum() == payload["horizon_days"] + 1
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


def test_chart_history_starts_from_configured_date():
    payload = load_brent_chart_payload(load_history=lambda symbol: _series())
    assert payload["history_dates"]
    assert payload["history_dates"][0] >= CHART_HISTORY_START


def test_chart_refresh_horizon_detects_forecast_and_refresh():
    assert chart_refresh_horizon("обнови график Brent") == 21
    assert chart_refresh_horizon("спрогнозируй Brent на 3 месяца") == 90
    assert chart_refresh_horizon("What is OPEC demand?") is None


def test_corpus_strip_lists_agencies_when_samples_exist(tmp_path):
    for name in ("opec.pdf", "eia.pdf", "cbr.pdf"):
        (tmp_path / name).write_bytes(b"%PDF-1.4")
    cfg = {
        "agency_urls": {
            "OPEC": "https://www.opec.org/monthly-oil-market-report.html",
            "EIA": "https://www.eia.gov/outlooks/steo/pdf/steo_full.pdf",
            "CBR": "https://www.cbr.ru/analytics/dkp/ddb/",
        },
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
    assert all(entry.url for entry in entries)
    assert "[OPEC · 2026-06]" in entries[0].link_markdown()
