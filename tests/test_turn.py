"""Analyst turn seam: question → reply through a frozen Ouroboros loop."""

from oil_gas_analyst.turn import (
    apply_citation_links,
    drop_listing,
    footer_flags,
    markdown_cite,
    run_turn,
)
from oil_gas_analyst.types import Chunk, Citation, LoopResult, Reply


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
    from oil_gas_analyst.app import format_reply

    text = format_reply(Reply(text="Senior Analyst reply."))
    assert "Senior Analyst reply." in text
    assert "classify" not in text
