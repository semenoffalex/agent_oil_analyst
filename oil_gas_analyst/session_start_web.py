from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence
from urllib.parse import urlparse

import yaml

from oil_gas_analyst.denylist import is_denied
from oil_gas_analyst.types import Reply
from oil_gas_analyst.web import search_for_tool

_CONFIG = Path(__file__).resolve().parent.parent / "config" / "session_start_rail_exclusions.yaml"


def load_rail_exclusions(path: Path | None = None) -> tuple[str, ...]:
    data = yaml.safe_load((path or _CONFIG).read_text(encoding="utf-8"))
    return tuple(d.casefold().strip() for d in data.get("domains") or [])


def _is_rail_hidden(url: str, exclusions: Sequence[str]) -> bool:
    return is_denied(url, exclusions)

SESSION_START_WEB_QUERY = "нефть Brent OPEC+ цена добыча"

RAIL_EMPTY_COPY = (
    "Нет свежих Web-источников для ленты. Не выдумываем заголовки — "
    "чат может позже вызвать search_web."
)


@dataclass(frozen=True)
class SessionStartRailHit:
    title: str
    outlet: str
    snippet: str
    url: str
    citation: str


def outlet_from_url(url: str) -> str:
    host = urlparse(url).hostname or urlparse(url).netloc or url
    if host.startswith("www."):
        host = host[4:]
    return host


def fetch_session_start_web(*, searcher=None) -> dict:
    """One host Web fetch for the Dashboard session (not an Ouroboros turn)."""
    return search_for_tool(SESSION_START_WEB_QUERY, searcher=searcher)


def visible_rail_hits(
    payload: dict,
    *,
    exclusions: Sequence[str] | None = None,
) -> list[SessionStartRailHit]:
    """Rows the executive may see and the Analyst may be injected with."""
    hidden = tuple(exclusions) if exclusions is not None else load_rail_exclusions()
    visible: list[SessionStartRailHit] = []
    for row in payload.get("hits") or []:
        if row.get("denied"):
            continue
        url = str(row.get("url") or "")
        if not url or _is_rail_hidden(url, hidden):
            continue
        visible.append(
            SessionStartRailHit(
                title=str(row.get("title") or outlet_from_url(url)),
                outlet=outlet_from_url(url),
                snippet=str(row.get("snippet") or ""),
                url=url,
                citation=str(row.get("citation") or ""),
            )
        )
    return visible


def inject_session_start_web(question: str, hits: Sequence[SessionStartRailHit]) -> str:
    """Prepend visible Session-start hits so the loop may cite them without search_web this turn."""
    if not hits:
        return question
    lines = [
        "Session-start Web for this Dashboard session "
        "(you may cite these URLs without search_web this turn):",
    ]
    for hit in hits:
        snippet = hit.snippet.strip().replace("\n", " ")
        if len(snippet) > 240:
            snippet = snippet[:237] + "..."
        lines.append(
            f"- {hit.title} ({hit.outlet}): {snippet} | {hit.citation} | {hit.url}"
        )
    lines.append("")
    lines.append(f"User question: {question}")
    return "\n".join(lines)


def has_grounded_session_start_web(
    reply: Reply,
    hits: Sequence[SessionStartRailHit],
) -> bool:
    """True when the visible answer cites a Session-start URL from this session's rail."""
    if not hits or "[Источник:" not in (reply.text or ""):
        return False
    allowed_urls = {hit.url for hit in hits}
    allowed_outlets = {hit.outlet.casefold() for hit in hits}
    for citation in reply.citations:
        if citation.kind != "web":
            continue
        if citation.url and citation.url in allowed_urls:
            return True
        label = citation.label.casefold()
        if any(outlet in label for outlet in allowed_outlets):
            return True
    return False
