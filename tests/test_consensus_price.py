from oil_gas_analyst.consensus_price import (
    consensus_from_texts,
    dashboard_kpi_row,
    extract_oil_prices,
    news_consensus_price,
    report_consensus_price,
)
from oil_gas_analyst.session_start_web import SessionStartRailHit


def test_extract_oil_prices_finds_dollar_and_contextual_brent():
    text = "Brent settled at $78.40 a barrel. WTI at 74.20 USD/bbl."
    prices = extract_oil_prices(text)
    assert 78.40 in prices
    assert 74.20 in prices


def test_extract_oil_prices_ignores_out_of_range_values():
    assert extract_oil_prices("Oil at $5 and $250 per barrel") == []


def test_consensus_from_texts_averages_per_source():
    texts = [
        "Report A: Brent $80 and $82.",
        "Report B: Brent $70.",
    ]
    assert consensus_from_texts(texts) == 75.5


def test_report_consensus_price_uses_retrieve_then_samples():
    def retrieve(query: str, k: int):
        assert "Brent" in query
        return ["OPEC sees Brent at $81.00 per barrel."]

    value = report_consensus_price(retrieve=retrieve, sample_texts=lambda: [])
    assert value == 81.0


def test_news_consensus_price_from_rail_hits():
    hits = [
        SessionStartRailHit(
            title="Brent rises to $79.10",
            outlet="reuters.com",
            snippet="Crude gained on supply concerns.",
            url="https://www.reuters.com/markets/brent",
            citation="[Источник: reuters.com, web]",
        ),
        SessionStartRailHit(
            title="Oil steady",
            outlet="bloomberg.com",
            snippet="Brent traded near $77.50.",
            url="https://www.bloomberg.com/news/oil",
            citation="[Источник: bloomberg.com, web]",
        ),
    ]
    assert news_consensus_price(hits) == 78.3


def test_dashboard_kpi_row_combines_close_and_consensus():
    payload = {"live_quote": 80.0}
    row = dashboard_kpi_row(
        payload,
        [],
        report_consensus=81.0,
        news_consensus=79.0,
    )
    assert row == {
        "close": 80.0,
        "reports_consensus": 81.0,
        "news_consensus": 79.0,
    }
