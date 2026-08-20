from oil_gas_analyst.session_start_web import (
    SESSION_START_INJECT_HEADER,
    SESSION_START_WEB_QUERY,
    SessionStartRailHit,
    fetch_session_start_web,
    has_grounded_session_start_web,
    inject_session_start_web,
    visible_rail_hits,
)
from oil_gas_analyst.turn import run_turn
from oil_gas_analyst.types import Citation, LoopResult, Reply


def _payload(kp_denied: bool = True, reuters: bool = True) -> dict:
    hits = []
    if kp_denied:
        hits.append(
            {
                "title": "Shock oil",
                "url": "https://www.kp.ru/oil",
                "snippet": "tabloid",
                "citation": "[Источник: kp.ru, web]",
                "denied": True,
            }
        )
    if reuters:
        hits.append(
            {
                "title": "Brent rises on OPEC",
                "url": "https://www.reuters.com/markets/brent",
                "snippet": "Brent rose after OPEC guidance.",
                "citation": "[Источник: reuters.com, web]",
                "denied": False,
            }
        )
    return {"hits": hits, "count": len(hits), "note": "ok"}


def test_fetch_session_start_web_uses_canned_query():
    seen: list[str] = []

    class _Search:
        def search(self, question: str):
            seen.append(question)
            return []

    fetch_session_start_web(searcher=_Search())
    assert seen == [SESSION_START_WEB_QUERY]


def test_fetch_session_start_web_saves_cache_on_success(tmp_path):
    from oil_gas_analyst.types import WebHit

    class _Search:
        def search(self, question: str):
            return [
                WebHit(
                    title="Brent rises",
                    url="https://www.reuters.com/markets/brent",
                    snippet="OPEC held output.",
                )
            ]

    payload = fetch_session_start_web(searcher=_Search(), cache_dir=tmp_path)
    assert visible_rail_hits(payload)
    assert (tmp_path / "top_news_rail.json").is_file()

    class _Empty:
        def search(self, question: str):
            return []

    cached = fetch_session_start_web(searcher=_Empty(), cache_dir=tmp_path)
    assert cached.get("cached") is True
    assert visible_rail_hits(cached)[0].title == "Brent rises"


def test_visible_rail_hits_hides_denied_domains():
    visible = visible_rail_hits(_payload())
    assert len(visible) == 1
    assert visible[0].outlet == "reuters.com"
    assert all("kp.ru" not in hit.url for hit in visible)


def test_visible_rail_hits_skips_older_than_today(monkeypatch):
    from datetime import date

    monkeypatch.setattr(
        "oil_gas_analyst.session_start_web._today_moscow",
        lambda: date(2026, 8, 20),
    )
    payload = {
        "hits": [
            {
                "title": "Yesterday",
                "url": "https://www.reuters.com/yesterday",
                "snippet": "old",
                "citation": "[Источник: reuters.com, web]",
                "denied": False,
                "published": "2026-08-19T12:00:00+00:00",
            },
            {
                "title": "Today",
                "url": "https://www.reuters.com/today",
                "snippet": "fresh",
                "citation": "[Источник: reuters.com, web]",
                "denied": False,
                "published": "2026-08-20T09:00:00+00:00",
            },
        ],
        "count": 2,
        "note": "ok",
    }
    visible = visible_rail_hits(payload)
    assert len(visible) == 1
    assert visible[0].title == "Today"


def test_inject_session_start_web_prepends_visible_hits():
    visible = visible_rail_hits(_payload(reuters=True))
    prompt = inject_session_start_web("What moved Brent?", visible)
    assert SESSION_START_INJECT_HEADER in prompt
    assert "reuters.com" in prompt
    assert "kp.ru" not in prompt
    assert prompt.endswith("User question: What moved Brent?")


def test_inject_skips_when_no_visible_hits():
    prompt = inject_session_start_web("What moved Brent?", [])
    assert prompt == "What moved Brent?"


def test_run_turn_injects_without_web_ran_this_turn():
    visible = visible_rail_hits(_payload())

    class _Loop:
        def __init__(self):
            self.questions: list[str] = []

        def complete(self, question: str) -> LoopResult:
            self.questions.append(question)
            return LoopResult(
                text="Brent moved [Источник: reuters.com, web].",
                web_ran=False,
                citations=[
                    Citation(
                        kind="web",
                        label="[Источник: reuters.com, web]",
                        url="https://www.reuters.com/markets/brent",
                    )
                ],
            )

    loop = _Loop()
    reply = run_turn("Tell me about the headline.", loop, session_start_hits=visible)
    assert reply.web_ran is False
    assert SESSION_START_INJECT_HEADER in loop.questions[0]
    assert has_grounded_session_start_web(reply, visible) is True


def test_has_grounded_session_start_web_false_without_rail_match():
    visible = visible_rail_hits(_payload(reuters=True))
    reply = Reply(
        text="Brent moved [Источник: bloomberg.com, web].",
        citations=[
            Citation(
                kind="web",
                label="[Источник: bloomberg.com, web]",
                url="https://www.bloomberg.com/news/oil",
            )
        ],
        web_ran=True,
    )
    assert has_grounded_session_start_web(reply, visible) is False
