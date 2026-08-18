from oil_gas_analyst.denylist import is_denied, load_denylist
from oil_gas_analyst.types import WebHit


def test_kp_and_subdomain_denied():
    domains = load_denylist()
    assert is_denied("https://www.kp.ru/daily/oil", domains) is True
    assert is_denied("https://news.kp.ru/x", domains) is True


def test_reuters_not_denied():
    domains = load_denylist()
    assert is_denied("https://www.reuters.com/markets/brent", domains) is False


def test_page_body_puts_article_figure_in_snippet():
    from oil_gas_analyst.web import fill_page_bodies

    hit = WebHit(
        title="Brent rises on OPEC statement",
        url="https://www.reuters.com/markets/brent",
        snippet="Brent rose.",
    )
    html = (
        "<html><head><script>window.tracker()</script></head><body>"
        "<nav>Markets</nav>"
        "<article><p>Brent crude settled at $78.40 a barrel after the OPEC meeting.</p></article>"
        "</body></html>"
    )
    filled = fill_page_bodies([hit], fetch_page=lambda url: html)
    assert "$78.40" in filled[0].snippet
    assert "window.tracker()" not in filled[0].snippet
    assert len(filled[0].snippet) <= 2000


def test_denied_domain_stays_in_hits_for_the_model():
    from oil_gas_analyst.web import fill_page_bodies, search_for_tool

    fetched: list[str] = []

    def fake(url: str) -> str:
        fetched.append(url)
        return "<p>Brent settled at $78.40</p>"

    hits = [
        WebHit(title="Shock oil", url="https://www.kp.ru/oil", snippet="tabloid"),
        WebHit(title="Reuters", url="https://www.reuters.com/markets/brent", snippet="short"),
    ]
    out = fill_page_bodies(hits, fetch_page=fake, denied_domains=["kp.ru"])
    assert "https://www.kp.ru/oil" in [hit.url for hit in out]
    assert "https://www.reuters.com/markets/brent" in [hit.url for hit in out]

    class _Search:
        def search(self, question: str):
            return hits

    payload = search_for_tool("latest OPEC statement", searcher=_Search())
    urls = [row["url"] for row in payload["hits"]]
    assert "https://www.kp.ru/oil" in urls
    assert any(row.get("denied") for row in payload["hits"])


def test_page_fetch_keeps_ddg_snippet_on_failure():
    from oil_gas_analyst.web import fill_page_bodies

    hit = WebHit(
        title="Reuters",
        url="https://www.reuters.com/markets/brent",
        snippet="Brent rose.",
    )

    def boom(url: str) -> str:
        raise OSError("timeout")

    out = fill_page_bodies([hit], fetch_page=boom, denied_domains=[])
    assert out[0].snippet == "Brent rose."


def test_page_fetch_stops_after_three_allowed_hits():
    from oil_gas_analyst.web import fill_page_bodies

    fetched: list[str] = []

    def fake(url: str) -> str:
        fetched.append(url)
        return f"<p>body {url}</p>"

    hits = [
        WebHit(title=str(i), url=f"https://www.reuters.com/{i}", snippet=f"s{i}")
        for i in range(5)
    ]
    out = fill_page_bodies(hits, fetch_page=fake, denied_domains=[])
    assert fetched == [f"https://www.reuters.com/{i}" for i in range(3)]
    assert len(out) == 5


def test_empty_web_search_asks_not_to_invent_news():
    from oil_gas_analyst.web import search_for_tool

    class _Empty:
        def search(self, question: str):
            return []

    payload = search_for_tool("latest OPEC statement", searcher=_Empty())
    assert payload["count"] == 0
    assert payload["hits"] == []
    note = (payload.get("note") or "").lower()
    assert "invent" in note or "uncertain" in note


def test_kp_and_subdomain_denied():
    domains = load_denylist()
    assert is_denied("https://www.kp.ru/daily/oil", domains) is True
    assert is_denied("https://news.kp.ru/x", domains) is True


def test_reuters_not_denied():
    domains = load_denylist()
    assert is_denied("https://www.reuters.com/markets/brent", domains) is False
