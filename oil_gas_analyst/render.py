from __future__ import annotations

import re
from collections.abc import Sequence

from oil_gas_analyst.ingest import load_ingest_config
from oil_gas_analyst.session_start_web import SessionStartRailHit
from oil_gas_analyst.turn import apply_citation_links, footer_flags, markdown_cite
from oil_gas_analyst.types import Citation, Reply

_WEB_TAG = re.compile(r"\[Источник:\s*([^,\]]+),\s*web\]", re.IGNORECASE)
_REPORT_TAG = re.compile(r"\[Отчёт [^\]]+\]")
_REPORT_PAGE = re.compile(r",\s*p+\.\s*(\d+)", re.IGNORECASE)


def _normalize_host(host: str) -> str:
    value = host.strip().lower()
    return value[4:] if value.startswith("www.") else value


def _web_url_for_host(host: str, hits: Sequence[SessionStartRailHit]) -> str | None:
    needle = _normalize_host(host)
    for hit in hits:
        outlet = _normalize_host(hit.outlet)
        if needle == outlet or needle in _normalize_host(hit.url):
            return hit.url
    return None


def _report_url_for_label(label: str) -> str | None:
    inner = label.strip()
    if inner.startswith("[") and inner.endswith("]"):
        inner = inner[1:-1]
    if not inner.startswith("Отчёт "):
        return None

    body = inner.removeprefix("Отчёт ").strip()
    page_match = _REPORT_PAGE.search(body)
    page = page_match.group(1) if page_match else None

    cfg = load_ingest_config()
    agency_urls = {
        str(key): str(value)
        for key, value in (cfg.get("agency_urls") or {}).items()
        if value
    }

    best_url: str | None = None
    best_len = 0
    for sample in cfg.get("samples") or []:
        title = str(sample.get("title") or "")
        if title and title in body and len(title) > best_len:
            url = str(sample.get("url") or "").strip() or agency_urls.get(
                str(sample.get("agency") or ""), ""
            )
            if url:
                best_url = url
                best_len = len(title)

    if not best_url:
        upper = body.upper()
        for agency, url in agency_urls.items():
            if agency in upper:
                best_url = url
                break

    if not best_url:
        return None
    if page and best_url.lower().endswith(".pdf"):
        return f"{best_url}#page={page}"
    return best_url


def enrich_citations(
    citations: list[Citation],
    hits: Sequence[SessionStartRailHit] | None,
) -> list[Citation]:
    """Attach URLs to citation tags scraped from Ouroboros text."""

    session_hits = hits or ()
    enriched: list[Citation] = []
    for citation in citations:
        if citation.url:
            enriched.append(citation)
            continue
        url: str | None = None
        web_match = _WEB_TAG.fullmatch(citation.label.strip())
        if web_match:
            url = _web_url_for_host(web_match.group(1), session_hits)
        elif citation.label.startswith("[Отчёт"):
            url = _report_url_for_label(citation.label)
        enriched.append(
            Citation(kind=citation.kind, label=citation.label, url=url or citation.url)
        )
    return enriched


def _link_tags_in_text(
    text: str,
    hits: Sequence[SessionStartRailHit] | None,
) -> str:
    session_hits = hits or ()

    def link_web(match: re.Match[str]) -> str:
        host = match.group(1)
        url = _web_url_for_host(host, session_hits)
        if not url:
            return match.group(0)
        return f"[Источник: {host.strip()}, web]({url})"

    def link_report(match: re.Match[str]) -> str:
        label = match.group(0)
        url = _report_url_for_label(label)
        if not url:
            return label
        return markdown_cite(Citation(kind="report", label=label, url=url))

    out = _WEB_TAG.sub(link_web, text)
    return _REPORT_TAG.sub(link_report, out)


def _sources_for_footer(body: str, citations: list[Citation]) -> list[Citation]:
    seen: set[str] = set()
    footer: list[Citation] = []
    for citation in citations:
        if not citation.url or citation.label not in body:
            continue
        if citation.label in seen:
            continue
        seen.add(citation.label)
        footer.append(citation)
    return footer


def format_reply(
    reply: Reply,
    *,
    session_start_hits: Sequence[SessionStartRailHit] | None = None,
) -> str:
    """Render chat message: linked body, Russian sources list, and footer flags."""

    citations = enrich_citations(list(reply.citations), session_start_hits)
    body = apply_citation_links(reply.text.strip(), citations)
    body = _link_tags_in_text(body, session_start_hits)

    parts = [body]
    sources = _sources_for_footer(body, citations)
    if sources:
        parts.append("")
        parts.append("**Источники**")
        parts.extend(f"- {markdown_cite(citation)}" for citation in sources)

    flags = footer_flags(reply)
    if flags:
        parts.append("")
        parts.append("_" + " · ".join(flags) + "_")
    return "\n".join(parts)
