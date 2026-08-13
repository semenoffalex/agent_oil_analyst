from __future__ import annotations

from dataclasses import dataclass

from urllib.parse import urlparse

from oil_gas_analyst.denylist import is_denied
from oil_gas_analyst.routes import is_forecast_request, is_time_sensitive, load_route_lists
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


@dataclass
class AnalystDeps:
    classifier: CompetenceClassifier
    retriever: Retriever
    dropper: ChunkDropper
    web: WebSearch
    forecast: ForecastModule
    composer: Composer
    denied_domains: list[str]
    retrieve_k: int = 5
    route_lists: object | None = None


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
    )


def _web_citation(hit: WebHit) -> Citation:
    host = urlparse(hit.url).hostname or hit.title
    if host.startswith("www."):
        host = host[4:]
    return Citation(kind="web", label=f"[Источник: {host}, web]")


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
    if deps.classifier.classify(question) == "out":
        return Reply(text=REFUSAL_TEXT, refused=True)

    lists = deps.route_lists or load_route_lists()
    want_forecast = is_forecast_request(question, lists)
    want_web = is_time_sensitive(question, lists)

    chunks = deps.retriever.retrieve(question, k=deps.retrieve_k)
    kept = deps.dropper.keep(question, chunks)
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
