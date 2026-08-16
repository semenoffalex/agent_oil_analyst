from __future__ import annotations

from dataclasses import dataclass, field

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


def drop_listing(chunks: list[Chunk]) -> str:
    return "\n".join(f"[{i}] {c.heading}: {c.text}" for i, c in enumerate(chunks))


def _keep_or_restore(chunks: list[Chunk], kept: list[Chunk]) -> list[Chunk]:
    if kept:
        return kept
    return [chunk for chunk in chunks if _is_report_relevant(chunk)]


WEB_REASON_TIME_SENSITIVE = "time-sensitive"
WEB_REASON_RETRIEVE_ERROR = "retrieve-error"
WEB_REASON_NO_KEPT = "no-kept-reports"


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


@dataclass
class TurnCtx:
    question: str
    deps: AnalystDeps
    lists: object
    want_forecast: bool = False
    want_web: bool = False
    web_reason: str | None = None
    refused: bool = False
    chunks: list[Chunk] = field(default_factory=list)
    kept: list[Chunk] = field(default_factory=list)
    forecast_result: ForecastResult | None = None
    forecast_ran: bool = False
    forecast_failed: bool = False
    web_hits: list[WebHit] = field(default_factory=list)
    web_ran: bool = False
    citations: list[Citation] = field(default_factory=list)
    text: str = ""
    steps: list[str] = field(default_factory=list)


def new_turn(question: str, deps: AnalystDeps) -> TurnCtx:
    return TurnCtx(
        question=question,
        deps=deps,
        lists=deps.route_lists or load_route_lists(),
    )


def _mark_web(ctx: TurnCtx, reason: str) -> None:
    if ctx.web_reason is None:
        ctx.web_reason = reason
    ctx.want_web = True


def step_classify(ctx: TurnCtx) -> None:
    ctx.steps.append("classify")
    ctx.want_forecast = is_forecast_request(ctx.question, ctx.lists)
    try:
        classified_out = ctx.deps.classifier.classify(ctx.question) == "out"
    except Exception:
        # Infrastructure error only: fail-open to in, except spec out-of-scope demos.
        classified_out = is_out_of_scope_topic(ctx.question)
    # Forecast verbs are in Competence (default Brent) unless the topic is a
    # spec out-of-scope demo. Classify must not block the calculation module.
    if classified_out and not (ctx.want_forecast and not is_out_of_scope_topic(ctx.question)):
        ctx.refused = True
        return
    if is_time_sensitive(ctx.question, ctx.lists):
        _mark_web(ctx, WEB_REASON_TIME_SENSITIVE)


def step_retrieve(ctx: TurnCtx) -> None:
    ctx.steps.append("retrieve")
    try:
        ctx.chunks = ctx.deps.retriever.retrieve(ctx.question, k=ctx.deps.retrieve_k)
    except Exception:
        ctx.chunks = []
        _mark_web(ctx, WEB_REASON_RETRIEVE_ERROR)


def step_drop(ctx: TurnCtx) -> None:
    ctx.steps.append("drop")
    ctx.kept = _keep_or_restore(ctx.chunks, ctx.deps.dropper.keep(ctx.question, ctx.chunks))
    if not ctx.kept:
        _mark_web(ctx, WEB_REASON_NO_KEPT)


def step_tools(ctx: TurnCtx) -> None:
    ctx.steps.append("tools")
    if ctx.want_forecast:
        ctx.forecast_ran = True
        try:
            ctx.forecast_result = ctx.deps.forecast.forecast(ctx.question)
        except Exception:
            ctx.forecast_failed = True
    if ctx.want_web:
        ctx.web_ran = True
        try:
            raw = ctx.deps.web.search(ctx.question)
        except Exception:
            raw = []
        ctx.web_hits = [h for h in raw if not is_denied(h.url, ctx.deps.denied_domains)]


def needs_tools(ctx: TurnCtx) -> bool:
    return ctx.want_web or ctx.want_forecast


def step_compose(ctx: TurnCtx) -> None:
    ctx.steps.append("compose")
    ctx.citations = [_report_citation(c) for c in ctx.kept]
    ctx.citations.extend(_web_citation(h) for h in ctx.web_hits)
    if ctx.forecast_result is not None:
        ctx.citations.extend(_forecast_citations(ctx.forecast_result))
    ctx.text = ctx.deps.composer.compose(
        ctx.question,
        kept=ctx.kept,
        web=ctx.web_hits,
        forecast=ctx.forecast_result,
        forecast_failed=ctx.forecast_failed,
        citations=ctx.citations,
        refused=False,
    )
    ctx.text = _ensure_report_tags(ctx.text, ctx.kept, ctx.citations)
    if ctx.forecast_failed:
        ctx.text = f"{ctx.text}\n{FORECAST_UNAVAILABLE}"
    if ctx.web_ran and not ctx.web_hits:
        ctx.text = f"{ctx.text}\nWeb search returned no usable sources; those claims are uncertain."


def finish_refuse(ctx: TurnCtx) -> Reply:
    return Reply(text=REFUSAL_TEXT, refused=True, steps=list(ctx.steps), web_reason=ctx.web_reason)


def finish_compose(ctx: TurnCtx) -> Reply:
    return Reply(
        text=ctx.text,
        citations=ctx.citations,
        retrieved=True,
        web_ran=ctx.web_ran,
        forecast_ran=ctx.forecast_ran,
        forecast_failed=ctx.forecast_failed,
        refused=False,
        steps=list(ctx.steps),
        web_reason=ctx.web_reason,
    )


def footer_flags(reply: Reply) -> list[str]:
    flags: list[str] = []
    if reply.refused:
        flags.append("refused")
    if reply.retrieved:
        flags.append("Reports retrieved")
    if reply.web_ran:
        flags.append(f"web ({reply.web_reason})" if reply.web_reason else "web")
    if reply.forecast_ran:
        flags.append("Forecast unavailable" if reply.forecast_failed else "Forecast")
    if reply.steps:
        flags.append(" → ".join(reply.steps))
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


def run_turn(question: str, deps: AnalystDeps) -> Reply:
    ctx = new_turn(question, deps)
    step_classify(ctx)
    if ctx.refused:
        return finish_refuse(ctx)
    step_retrieve(ctx)
    step_drop(ctx)
    if needs_tools(ctx):
        step_tools(ctx)
    step_compose(ctx)
    return finish_compose(ctx)


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
