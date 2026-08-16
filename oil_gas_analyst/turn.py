from __future__ import annotations

from dataclasses import dataclass

from urllib.parse import urlparse

from oil_gas_analyst.denylist import is_denied
from oil_gas_analyst.ingest import load_ingest_config
from oil_gas_analyst.routes import (
    is_forecast_request,
    is_out_of_scope_topic,
    is_time_sensitive,
    load_route_lists,
)
from oil_gas_analyst.types import (
    Chunk,
    ChunkDropper,
    Citation,
    CompetenceClassifier,
    Composer,
    ForecastModule,
    ForecastResult,
    Reply,
    Retriever,
    WebHit,
    WebSearch,
)

REFUSAL_TEXT = (
    "This question is outside my Competence as a senior oil-and-gas market Analyst. "
    "I will not retrieve Reports, search the web, or run a Forecast."
)

FORECAST_UNAVAILABLE = (
    "Forecast unavailable: price history could not be loaded. Any oil-price figures would be uncertain."
)

# Closed markers: a Retrieved chunk may support a price/demand/supply answer.
# Used when Drop empties the set so Web does not replace an on-topic Report.
_REPORT_HEADING_MARKERS = (
    "crude oil price",
    "world oil demand",
    "world oil supply",
    "balance of supply and demand",
    "global oil price",
    "global oil market",
    "global liquid fuel",
    "нефть",
)
_REPORT_TEXT_MARKERS = (
    "oil demand",
    "oil supply",
    "oil price",
    "crude oil price",
    "mb/d",
    "спрос на нефть",
    "цены на нефть",
    "цен на нефть",
)


def _is_report_relevant(chunk: Chunk) -> bool:
    heading = (chunk.heading or "").casefold()
    if any(marker in heading for marker in _REPORT_HEADING_MARKERS):
        return True
    blob = f"{chunk.heading}\n{chunk.text}".casefold()
    return any(marker in blob for marker in _REPORT_TEXT_MARKERS)


def _keep_or_restore(chunks: list[Chunk], kept: list[Chunk]) -> list[Chunk]:
    if kept:
        return kept
    return [chunk for chunk in chunks if _is_report_relevant(chunk)]


@dataclass
class AnalystDeps:
    classifier: CompetenceClassifier
    retriever: Retriever
    dropper: ChunkDropper
    web: WebSearch
    forecast: ForecastModule
    composer: Composer
    denied_domains: list[str]
    retrieve_k: int = 10
    route_lists: object | None = None


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


def _report_citation(chunk: Chunk) -> Citation:
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


def _web_citation(hit: WebHit) -> Citation:
    host = urlparse(hit.url).hostname or hit.title
    if host.startswith("www."):
        host = host[4:]
    return Citation(kind="web", label=f"[Источник: {host}, web]", url=hit.url)


def _forecast_citations(result: ForecastResult) -> list[Citation]:
    if result.unavailable_reason:
        return [
            Citation(
                kind="forecast",
                label=f"[Forecast {result.symbol}: no series — {result.unavailable_reason}]",
            )
        ]
    out: list[Citation] = []
    for method in result.methods:
        out.append(
            Citation(
                kind="forecast",
                label=(
                    f"[Forecast {method.name} {result.symbol} "
                    f"{method.point} ({method.low}–{method.high})]"
                ),
            )
        )
    return out


def run_turn(question: str, deps: AnalystDeps) -> Reply:
    lists = deps.route_lists or load_route_lists()
    want_forecast = is_forecast_request(question, lists)
    want_web = is_time_sensitive(question, lists)
    classified_out = deps.classifier.classify(question) == "out"
    # Forecast verbs are in Competence (default Brent) unless the topic is a
    # spec out-of-scope demo. Classify must not block the calculation module.
    if classified_out and not (want_forecast and not is_out_of_scope_topic(question)):
        return Reply(text=REFUSAL_TEXT, refused=True)

    chunks = []
    try:
        chunks = deps.retriever.retrieve(question, k=deps.retrieve_k)
    except Exception:
        want_web = True
    kept = _keep_or_restore(chunks, deps.dropper.keep(question, chunks))
    if not kept:
        want_web = True

    forecast_result: ForecastResult | None = None
    forecast_ran = False
    forecast_failed = False
    if want_forecast:
        forecast_ran = True
        try:
            forecast_result = deps.forecast.forecast(question)
        except Exception:
            forecast_failed = True

    web_hits: list[WebHit] = []
    web_ran = False
    if want_web:
        web_ran = True
        try:
            raw = deps.web.search(question)
        except Exception:
            raw = []
        web_hits = [h for h in raw if not is_denied(h.url, deps.denied_domains)]

    citations: list[Citation] = [_report_citation(c) for c in kept]
    citations.extend(_web_citation(h) for h in web_hits)
    if forecast_result is not None:
        citations.extend(_forecast_citations(forecast_result))

    text = deps.composer.compose(
        question,
        kept=kept,
        web=web_hits,
        forecast=forecast_result,
        forecast_failed=forecast_failed,
        citations=citations,
        refused=False,
    )
    text = _ensure_report_tags(text, kept, citations)
    if forecast_failed:
        text = f"{text}\n{FORECAST_UNAVAILABLE}"
    if web_ran and not web_hits:
        text = f"{text}\nWeb search returned no usable sources; those claims are uncertain."

    return Reply(
        text=text,
        citations=citations,
        retrieved=True,
        web_ran=web_ran,
        forecast_ran=forecast_ran,
        refused=False,
    )


def markdown_cite(citation: Citation) -> str:
    if not citation.url:
        return citation.label
    if citation.label.startswith("[") and citation.label.endswith("]"):
        return f"{citation.label[:-1]}]({citation.url})"
    return f"[{citation.label}]({citation.url})"


def _ensure_report_tags(text: str, kept: list[Chunk], citations: list[Citation]) -> str:
    if not kept or "[Отчёт" in text:
        return text
    report_cites = [c for c in citations if c.kind == "report"]
    lines = [text.rstrip(), ""]
    for chunk, cite in zip(kept, report_cites):
        snippet = " ".join(chunk.text.split())
        if len(snippet) > 400:
            snippet = snippet[:400].rstrip() + "…"
        lines.append(f"{snippet} {cite.label}")
    return "\n".join(lines)


def apply_citation_links(text: str, citations: list[Citation]) -> str:
    out = text
    for citation in sorted(citations, key=lambda c: len(c.label), reverse=True):
        if citation.url:
            out = out.replace(citation.label, markdown_cite(citation))
    return out
