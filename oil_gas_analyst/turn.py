"""Analyst turn seam and citation helpers. Conversation path is the Ouroboros loop."""

from __future__ import annotations

from collections.abc import Sequence
from urllib.parse import urlparse

from oil_gas_analyst.ingest import load_ingest_config
from oil_gas_analyst.routes import is_out_of_scope_topic
from oil_gas_analyst.session_start_web import SessionStartRailHit, inject_session_start_web
from oil_gas_analyst.settings import maybe_traceable
from oil_gas_analyst.types import (
    AnalystLoop,
    Chunk,
    Citation,
    ForecastResult,
    LoopError,
    Reply,
    WebHit,
)

REFUSAL_TEXT = (
    "This question is outside my Competence as a senior oil-and-gas market Analyst. "
    "I will not retrieve Reports, search the web, or run a Forecast."
)

INFRA_TEXT = (
    "I hit an infrastructure error and will not invent figures. "
    "Any oil-price or volume claims would be uncertain."
)


def drop_listing(chunks: list[Chunk]) -> str:
    """Format chunks for a Dropper prompt (index, heading, full text).

    Args:
        chunks: Retrieved Report chunks to list for relevance scoring.

    Returns:
        Numbered lines ``[i] heading: text``, one chunk per line.
    """
    return "\n".join(f"[{i}] {c.heading}: {c.text}" for i, c in enumerate(chunks))


def footer_flags(reply: Reply) -> list[str]:
    """Build Chainlit footer tokens from a ``Reply`` (tools that ran, not graph steps)."""

    flags: list[str] = []
    if reply.refused:
        flags.append("refused")
    if reply.retrieved:
        flags.append("Reports retrieved")
    if reply.web_ran:
        flags.append(f"web ({reply.web_reason})" if reply.web_reason else "web")
    if reply.forecast_ran:
        flags.append("Forecast unavailable" if reply.forecast_failed else "Forecast")
    return flags


def _agency_of(chunk: Chunk) -> str:
    if chunk.agency:
        return chunk.agency
    blob = f"{chunk.title} {chunk.heading}"
    upper = blob.upper()
    if "OPEC" in upper or "MOMR" in upper:
        return "OPEC"
    if "EIA" in upper or "STEO" in upper:
        return "EIA"
    if "CBR" in upper or "Банк России" in blob:
        return "CBR"
    return ""


def _agency_urls() -> dict[str, str]:
    cfg = load_ingest_config()
    raw = cfg.get("agency_urls") or {}
    return {str(key): str(value) for key, value in raw.items() if value}


def _report_url(chunk: Chunk) -> str | None:
    base = (chunk.url or "").strip() or _agency_urls().get(_agency_of(chunk), "")
    if not base:
        return None
    path = urlparse(base).path.lower()
    if chunk.page_start is not None and path.endswith(".pdf"):
        return f"{base}#page={chunk.page_start}"
    return base


def report_citation(chunk: Chunk) -> Citation:
    """Build a Report citation label (title, date, pages, excerpt)."""

    pages = ""
    if chunk.page_start is not None:
        if chunk.page_end and chunk.page_end != chunk.page_start:
            pages = f", pp. {chunk.page_start}–{chunk.page_end}"
        else:
            pages = f", p. {chunk.page_start}"
    date = f", {chunk.date}" if chunk.date else ""
    excerpt = " (excerpt)" if chunk.excerpt else ""
    return Citation(
        kind="report",
        label=f"[Отчёт {chunk.title}{date}{pages}{excerpt}]",
        url=_report_url(chunk),
    )


def web_citation(hit: WebHit) -> Citation:
    host = urlparse(hit.url).hostname or hit.title
    if host.startswith("www."):
        host = host[4:]
    return Citation(kind="web", label=f"[Источник: {host}, web]", url=hit.url)


def forecast_citations(result: ForecastResult) -> list[Citation]:
    if result.unavailable_reason:
        return [
            Citation(
                kind="forecast",
                label=f"[Forecast {result.symbol}: no series — {result.unavailable_reason}]",
            )
        ]
    out: list[Citation] = []
    horizon = f"{result.horizon_days}d " if result.horizon_days else ""
    for method in result.methods:
        out.append(
            Citation(
                kind="forecast",
                label=(
                    f"[Forecast {method.name} {result.symbol} {horizon}"
                    f"{method.point} ({method.low}–{method.high})]"
                ),
            )
        )
    return out


def has_grounded_report(reply: Reply) -> bool:
    """True when the visible answer has ``[Отчёт …]`` and retrieve ran this turn."""

    return "[Отчёт" in (reply.text or "") and reply.retrieved is True


def _safety_net(question: str, *, infra_detail: str | None = None) -> Reply:
    """Fallback when the loop did not return a live completion.

    ``is_out_of_scope_topic`` is only this fallback, not a Competence gate.
    """

    if is_out_of_scope_topic(question):
        return Reply(text=REFUSAL_TEXT, refused=True)
    text = INFRA_TEXT
    if infra_detail:
        text = f"{INFRA_TEXT} ({infra_detail})"
    return Reply(text=text, refused=False)


@maybe_traceable("analyst.run_turn")
def run_turn(
    question: str,
    loop: AnalystLoop,
    *,
    session_start_hits: Sequence[SessionStartRailHit] | None = None,
) -> Reply:
    """Run one Analyst turn through the Ouroboros loop.

    Public seam: ``question → reply`` (text, citation tags, which tools ran).
    A live completion is not refused or citation-patched by the host.
    Timeout / 500 / empty completions use Safety nets only.
    """
    prompt = inject_session_start_web(question, session_start_hits or ())
    try:
        result = loop.complete(prompt)
    except (TimeoutError, LoopError) as exc:
        return _safety_net(question, infra_detail=str(exc))
    return Reply(
        text=result.text,
        citations=list(result.citations),
        retrieved=result.retrieved,
        web_ran=result.web_ran,
        forecast_ran=result.forecast_ran,
        forecast_failed=result.forecast_failed,
        refused=False,
        steps=[],
        web_reason=result.web_reason,
    )


def markdown_cite(citation: Citation) -> str:
    """Turn a citation label into a Markdown link when a URL is present."""

    if not citation.url:
        return citation.label
    if citation.label.startswith("[") and citation.label.endswith("]"):
        return f"{citation.label[:-1]}]({citation.url})"
    return f"[{citation.label}]({citation.url})"


def apply_citation_links(text: str, citations: list[Citation]) -> str:
    """Replace citation labels in prose with clickable Markdown links."""

    out = text
    for citation in sorted(citations, key=lambda c: len(c.label), reverse=True):
        if citation.url:
            out = out.replace(citation.label, markdown_cite(citation))
    return out
