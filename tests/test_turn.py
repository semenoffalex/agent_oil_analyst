"""Analyst turn seam: question → reply through a frozen Ouroboros loop."""

from oil_gas_analyst.turn import (
    apply_citation_links,
    drop_listing,
    footer_flags,
    has_grounded_report,
    markdown_cite,
    run_turn,
)
from oil_gas_analyst.types import Chunk, Citation, LoopError, LoopResult, Reply


class _FrozenLoop:
    def __init__(self, result: LoopResult):
        self.result = result
        self.questions: list[str] = []

    def complete(self, question: str) -> LoopResult:
        self.questions.append(question)
        return self.result


def test_live_reply_passes_through_without_host_report_patch():
    loop = _FrozenLoop(LoopResult(text="Demand grew."))
    reply = run_turn("What is OPEC's 2026 world oil demand outlook?", loop)
    assert reply.text == "Demand grew."
    assert "[Отчёт" not in reply.text
    assert reply.citations == []
    assert loop.questions == ["What is OPEC's 2026 world oil demand outlook?"]


def test_host_does_not_refuse_out_of_competence_question():
    loop = _FrozenLoop(LoopResult(text="I will not invent a weather forecast."))
    reply = run_turn("what's the weather today?", loop)
    assert reply.refused is False
    assert reply.web_ran is False
    assert reply.forecast_ran is False
    assert reply.text == "I will not invent a weather forecast."


def test_reply_records_which_tools_the_loop_ran():
    loop = _FrozenLoop(
        LoopResult(text="Brent path.", retrieved=True, web_ran=True, forecast_ran=True)
    )
    reply = run_turn("What's Brent today given OPEC demand?", loop)
    assert reply.retrieved is True
    assert reply.web_ran is True
    assert reply.forecast_ran is True
    assert "Reports retrieved" in footer_flags(reply)
    assert "web" in footer_flags(reply)
    assert "Forecast" in footer_flags(reply)
    assert not any("classify" in flag for flag in footer_flags(reply))


def test_web_citation_markdown_includes_full_url():
    web = Citation(
        kind="web",
        label="[Источник: reuters.com, web]",
        url="https://www.reuters.com/markets/brent",
    )
    assert markdown_cite(web) == (
        "[Источник: reuters.com, web](https://www.reuters.com/markets/brent)"
    )
    body = apply_citation_links(f"Price rose {web.label}.", [web])
    assert "https://www.reuters.com/markets/brent" in body
    assert "](https://" in body


def test_report_citation_markdown_includes_pdf_page_url():
    from oil_gas_analyst.turn import report_citation

    momr = Chunk(
        text="The global oil demand growth forecast for 2026 remains at 1.4 mb/d.",
        title="OPEC Monthly Oil Market Report — March 2026 (excerpt, World Oil Demand)",
        date="2026-03",
        page_start=42,
        page_end=46,
        heading="World Oil Demand",
        excerpt=True,
        url="https://www.opec.org/assets/assetdb/momr-march-2026.pdf",
    )
    report = report_citation(momr)
    assert report.url == "https://www.opec.org/assets/assetdb/momr-march-2026.pdf#page=42"
    linked = markdown_cite(report)
    assert linked.startswith("[Отчёт ")
    assert linked.endswith("](https://www.opec.org/assets/assetdb/momr-march-2026.pdf#page=42)")
    assert "excerpt" in report.label.lower()


def test_dropper_sees_figure_past_800_chars():
    marker = "DEMAND_GROWTH_REMAINS_1.4_MBD"
    chunk = Chunk(
        text=("Lead-in. " * 120) + marker,
        title="OPEC MOMR June 2026",
        date="2026-06",
        page_start=42,
        page_end=46,
        heading="World Oil Demand",
    )
    assert marker not in chunk.text[:800]
    listed = drop_listing([chunk])
    assert marker in listed
    assert "World Oil Demand" in listed


def test_format_reply_does_not_require_langgraph_steps():
    from oil_gas_analyst.render import format_reply

    text = format_reply(Reply(text="Senior Analyst reply."))
    assert "Senior Analyst reply." in text
    assert "classify" not in text


def test_format_reply_links_web_sources_from_session_rail():
    from oil_gas_analyst.render import format_reply
    from oil_gas_analyst.session_start_web import SessionStartRailHit

    label = "[Источник: reuters.com, web]"
    hit = SessionStartRailHit(
        title="Brent rises",
        outlet="reuters.com",
        snippet="Oil up",
        url="https://www.reuters.com/markets/brent",
        citation=label,
    )
    text = format_reply(
        Reply(text=f"Цена выросла {label}.", citations=[Citation(kind="web", label=label)]),
        session_start_hits=[hit],
    )
    assert "[Источник: reuters.com, web](https://www.reuters.com/markets/brent)" in text
    assert "**Источники**" in text
    assert "**Sources**" not in text


def test_format_reply_links_report_source_from_ingest_config():
    from oil_gas_analyst.render import format_reply

    label = "[Отчёт OPEC Monthly Oil Market Report — June 2026, 2026-06, p. 42]"
    text = format_reply(
        Reply(text=f"Спрос растёт {label}.", citations=[Citation(kind="report", label=label)]),
    )
    assert "](https://www.opec.org/monthly-oil-market-report.html)" in text
    assert "**Источники**" in text


def test_format_reply_normalizes_bare_web_citations():
    from oil_gas_analyst.render import format_reply

    raw = (
        "Brent выше 94. Источник: oil.rftoday.ru, web(https://oil.rftoday.ru/); "
        "Источник: vc.ru, web(https://vc.ru/t/123)."
    )
    text = format_reply(Reply(text=raw))
    assert "[Источник: oil.rftoday.ru, web](https://oil.rftoday.ru/)" in text
    assert "[Источник: vc.ru, web](https://vc.ru/t/123)" in text
    assert "web(https://" not in text


def test_format_reply_dedupes_double_markdown_urls():
    from oil_gas_analyst.render import format_reply
    from oil_gas_analyst.session_start_web import SessionStartRailHit

    label = "[Источник: reuters.com, web]"
    hit = SessionStartRailHit(
        title="Brent rises",
        outlet="reuters.com",
        snippet="Oil up",
        url="https://www.reuters.com/markets/brent",
        citation=label,
    )
    raw = (
        f"Цена выросла {label}(https://www.reuters.com/markets/brent). "
        f"{label}(https://www.reuters.com/markets/brent)"
    )
    text = format_reply(
        Reply(text=raw, citations=[Citation(kind="web", label=label)]),
        session_start_hits=[hit],
    )
    assert "](https://www.reuters.com/markets/brent)(https://" not in text
    assert text.count("[Источник: reuters.com, web](https://www.reuters.com/markets/brent)") >= 2


def test_format_reply_fixes_spaced_markdown_urls():
    from oil_gas_analyst.render import format_reply

    raw = (
        "Диапазон *90–100**. [Источник : ru.economies.com, web]"
        "(https : //ru.economies.com/commodities/brent-oil-charts)."
    )
    text = format_reply(Reply(text=raw))
    assert "**90–100**" in text
    assert "[Источник : ru.economies.com, web](https://ru.economies.com/commodities/brent-oil-charts)" in text


def test_format_reply_links_inline_web_sources_from_session_rail():
    from oil_gas_analyst.render import format_reply
    from oil_gas_analyst.session_start_web import SessionStartRailHit

    hit = SessionStartRailHit(
        title="Brent close",
        outlet="lenta.profinansy.ru",
        snippet="Oil",
        url="https://lenta.profinansy.ru/news/brent",
        citation="[Источник: lenta.profinansy.ru, web]",
    )
    raw = "Brent — 93, 78/барр. Источник: lenta.profinansy.ru, web."
    text = format_reply(Reply(text=raw), session_start_hits=[hit])
    assert "93,78" in text
    assert "[Источник: lenta.profinansy.ru, web](https://lenta.profinansy.ru/news/brent)" in text


def test_format_reply_fixes_glued_cyrillic_and_broken_vc_url():
    from oil_gas_analyst.render import format_reply
    from oil_gas_analyst.session_start_web import SessionStartRailHit

    hit = SessionStartRailHit(
        title="Brent index",
        outlet="vc.ru",
        snippet="Oil",
        url="https://vc.ru/money/3089964-neft-brent-i-indeks-mosbirzhi",
        citation="[Источник: vc.ru, web]",
    )
    raw = (
        "сегодняднёмподнималасьдо94,58 "
        "[Источник : vc.ru, web](https : //vc.ru/money/3089964 — neft — brent — i — indeks — mosbirzhi)."
    )
    text = format_reply(Reply(text=raw), session_start_hits=[hit])
    assert "сегодня днём поднималась до 94,58" in text
    assert "3089964-neft-brent-i-indeks-mosbirzhi" in text
    assert " — " not in text.split("](", 1)[-1]


def test_format_reply_fixes_broken_bold_with_multiplication():
    from oil_gas_analyst.render import format_reply

    raw = "**Brent – WTI ≈ 7 * * (93,78 – $86,83)."
    text = format_reply(Reply(text=raw))
    assert "**Brent – WTI ≈ 7 × (" in text


def test_format_reply_normalizes_realistic_broken_prose():
    from oil_gas_analyst.render import chat_html, format_reply
    from oil_gas_analyst.session_start_web import SessionStartRailHit

    hits = [
        SessionStartRailHit(
            title="Brent",
            outlet="oil.rftoday.ru",
            snippet="Oil",
            url="https://oil.rftoday.ru/",
            citation="",
        ),
        SessionStartRailHit(
            title="Chart",
            outlet="ru.economies.com",
            snippet="Oil",
            url="https://ru.economies.com/commodities/brent-oil-charts",
            citation="",
        ),
        SessionStartRailHit(
            title="Trend",
            outlet="vc.ru",
            snippet="Oil",
            url="https://vc.ru/money/3089964-neft-brent-i-indeks-mosbirzhi",
            citation="",
        ),
        SessionStartRailHit(
            title="View",
            outlet="finam.ru",
            snippet="Oil",
            url="https://finam.ru/news/123",
            citation="",
        ),
    ]
    raw = (
        "пробивала 94—октябрьскийфьючерснаICEподнималсявыше94 Источник: oil.rftoday.ru, web(https://oil.rftoday.ru/); "
        "свежий срез на 11:30 UTC — около 94**[Источник : ru.economies.com, web]"
        "(https : //ru.economies.com/commodities/brent – oil – charts)"
        "(https : //ru.economies.com/commodities/brent – oil – charts)."
        "К11 : 46мскценаскорректироваласьдо 93,23 (-0,6%), "
        "пятыйденьростаподряд[Источник : vc.ru, web]"
        "(https : //vc.ru/money/3089964 — neft — brent);"
        "занеделюприбавилапримерно787 до 93+)."
        "Изболеераннегоконтекстасессии: рядэкспертовдопускаетзакреплениеBrentвдиапазоне * *90–100** "
        "[Источник: finam.ru, web]"
    )
    text = format_reply(Reply(text=raw), session_start_hits=hits)
    html = chat_html(text)

    assert "октябрьский фьючерс на ICE" in text
    assert "пятый день роста подряд" in text
    assert "за неделю" in text
    assert "Brent в диапазоне" in text
    assert "**90–100**" in text
    assert "https : //" not in text
    assert "web(https://" not in text
    assert "(https" not in html
    assert "<strong>90–100</strong>" in html


def test_chat_html_renders_links_and_bold():
    from oil_gas_analyst.render import chat_html

    html = chat_html(
        "**Спреды**\n\n"
        "Диапазон **90–100**. [Источник: vc.ru, web](https://vc.ru/t/1)."
    )
    assert '<strong>Спреды</strong>' in html
    assert '<strong>90–100</strong>' in html
    assert 'href="https://vc.ru/t/1"' in html
    assert "Источник: vc.ru, web" in html


MOMR = Chunk(
    text="The global oil demand growth forecast for 2026 remains at 1.4 mb/d.",
    title="OPEC Monthly Oil Market Report — March 2026 (excerpt, World Oil Demand)",
    date="2026-03",
    page_start=42,
    page_end=46,
    heading="World Oil Demand",
    excerpt=True,
    url="https://www.opec.org/assets/assetdb/momr-march-2026.pdf",
)


def test_corpus_covered_outlook_is_grounded_when_retrieve_ran_this_turn():
    from oil_gas_analyst.turn import report_citation

    cite = report_citation(MOMR)
    loop = _FrozenLoop(
        LoopResult(
            text=f"OPEC sees 2026 demand growth at 1.4 mb/d {cite.label}.",
            retrieved=True,
            citations=[cite],
        )
    )
    reply = run_turn("What is OPEC's 2026 world oil demand outlook?", loop)
    assert has_grounded_report(reply) is True
    assert "excerpt" in " ".join(c.label for c in reply.citations).lower()
    assert "1.4 mb/d" in reply.text


def test_report_tag_without_retrieve_this_turn_is_not_grounded():
    loop = _FrozenLoop(
        LoopResult(
            text="Demand grew [Отчёт OPEC MOMR, 2026-03, pp. 42–46 (excerpt)].",
            retrieved=False,
        )
    )
    reply = run_turn("What is OPEC's 2026 world oil demand outlook?", loop)
    assert "[Отчёт" in reply.text
    assert reply.retrieved is False
    assert has_grounded_report(reply) is False


def test_russian_question_can_use_english_report_chunks():
    from oil_gas_analyst.retrieve import retrieve_for_tool

    class _Retr:
        def retrieve(self, question: str, k: int = 10):
            assert "спрос" in question.casefold()
            return [MOMR]

    payload = retrieve_for_tool("Какой спрос OPEC на нефть в 2026?", retriever=_Retr())
    assert payload["count"] == 1
    assert "1.4 mb/d" in payload["chunks"][0]["text"]
    assert "excerpt" in payload["chunks"][0]["citation"].lower()


def test_live_weather_with_tools_is_not_host_blocked():
    loop = _FrozenLoop(
        LoopResult(text="I will not invent a forecast.", retrieved=True, web_ran=True)
    )
    reply = run_turn("what's the weather today?", loop)
    assert reply.refused is False
    assert reply.web_ran is True
    assert reply.retrieved is True


def test_infra_timeout_on_weather_uses_competence_safety_net():
    class _Boom:
        def complete(self, question: str) -> LoopResult:
            raise LoopError("timeout")

    reply = run_turn("what's the weather today?", _Boom())
    assert reply.refused is True
    assert "outside" in reply.text.lower() or "competence" in reply.text.casefold()
    assert "1.4 mb/d" not in reply.text
    assert reply.web_ran is False


def test_infra_timeout_on_oil_question_is_uncertainty_not_invented_figures():
    class _Boom:
        def complete(self, question: str) -> LoopResult:
            raise LoopError("timeout")

    reply = run_turn("What is OPEC's 2026 world oil demand outlook?", _Boom())
    assert reply.refused is False
    assert "1.4 mb/d" not in reply.text
    assert "uncertain" in reply.text.lower() or "infrastructure" in reply.text.lower()


def test_playbook_documents_prompt_failure_not_host_lock():
    from pathlib import Path

    text = Path("skills/oil_gas_analyst/SKILL.md").read_text(encoding="utf-8")
    lower = text.lower()
    assert "prompt" in lower
    assert "weather" in lower
    assert "uranium" in lower
    assert "forecast" in lower
    assert "kp.ru" in lower
    assert "dailymail" in lower
    assert "search_web" in lower or "web search" in lower
    assert "run_forecast" in lower or "sarima" in lower
    assert "average" in lower
    assert "urals" in lower


def test_live_denylist_citation_is_not_host_stripped():
    loop = _FrozenLoop(
        LoopResult(
            text="Tabloid said oil crashed [Источник: kp.ru, web].",
            web_ran=True,
        )
    )
    reply = run_turn("What's the latest OPEC statement on output?", loop)
    assert "kp.ru" in reply.text
    assert reply.web_ran is True
    assert reply.refused is False


def test_combined_report_and_web_tags_are_allowed():
    loop = _FrozenLoop(
        LoopResult(
            text=(
                "Demand growth is 1.4 mb/d "
                "[Отчёт OPEC MOMR, 2026-03, pp. 42–46 (excerpt)]. "
                "Brent is $78 [Источник: reuters.com, web]."
            ),
            retrieved=True,
            web_ran=True,
        )
    )
    reply = run_turn("What's Brent today given OPEC demand?", loop)
    assert has_grounded_report(reply) is True
    assert reply.web_ran is True
    assert "[Источник:" in reply.text


def test_host_does_not_refuse_forecast_without_a_verb():
    loop = _FrozenLoop(
        LoopResult(
            text=(
                "Brent 90d SARIMA 74 (70–78) Holt–Winters 73 (69–77) "
                "[Forecast sarima BZ=F 90d 74 (70–78)] "
                "[Forecast holt_winters BZ=F 90d 73 (69–77)]."
            ),
            forecast_ran=True,
        )
    )
    reply = run_turn("What's Brent in three months?", loop)
    assert reply.refused is False
    assert reply.forecast_ran is True
    assert "[Forecast " in reply.text


def test_live_forecast_reply_is_not_host_patched_with_tags():
    loop = _FrozenLoop(LoopResult(text="Brent may drift.", forecast_ran=True))
    reply = run_turn("спрогнозируй цену Brent на 3 месяца", loop)
    assert reply.text == "Brent may drift."
    assert "[Forecast " not in reply.text
