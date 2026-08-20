from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Sequence
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

import yaml

from oil_gas_analyst.denylist import is_denied, load_denylist
from oil_gas_analyst.types import Reply, WebHit
from oil_gas_analyst.web import search_for_tool

_CONFIG = Path(__file__).resolve().parent.parent / "config" / "session_start_rail_exclusions.yaml"
_MOSCOW = ZoneInfo("Europe/Moscow")

TOP_NEWS_RAIL_TITLE = "ТОП новостей"
SESSION_START_WEB_QUERY = "цена на нефть Brent"
SESSION_START_INJECT_HEADER = (
    "ТОП новостей этой сессии Dashboard (Яндекс, за сегодня; "
    "можете цитировать эти URL без search_web в этом ходу):"
)

RAIL_EMPTY_COPY = (
    "Нет свежих новостей за сегодня. Не выдумываем заголовки — "
    "чат может позже вызвать search_web."
)
NEWS_REFRESH_COPY = "Обновляем новости…"

_RELATIVE_YESTERDAY = re.compile(r"(?i)\b(вчера|yesterday|1\s*day\s*ago)\b")
_RELATIVE_TODAY = re.compile(r"(?i)\b(сегодня|today)\b")


def load_rail_exclusions(path: Path | None = None) -> tuple[str, ...]:
    data = yaml.safe_load((path or _CONFIG).read_text(encoding="utf-8"))
    return tuple(d.casefold().strip() for d in data.get("domains") or [])


def _is_rail_hidden(url: str, exclusions: Sequence[str]) -> bool:
    return is_denied(url, exclusions)


def _today_moscow() -> date:
    return datetime.now(_MOSCOW).date()


def _parse_iso_date(raw: object) -> date | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).astimezone(_MOSCOW).date()
    except ValueError:
        return None


def _infer_date_from_snippet(snippet: str) -> date | None:
    text = snippet.strip()
    if not text:
        return None
    if _RELATIVE_TODAY.search(text):
        return _today_moscow()
    if _RELATIVE_YESTERDAY.search(text):
        return _today_moscow() - timedelta(days=1)
    return None


def _is_fresh_for_rail(published: date | None, *, assume_today_if_unknown: bool) -> bool:
    today = _today_moscow()
    if published is None:
        return assume_today_if_unknown
    return published >= today


@dataclass(frozen=True)
class SessionStartRailHit:
    title: str
    outlet: str
    snippet: str
    url: str
    citation: str
    published: date | None = None


@dataclass(frozen=True)
class _RankedWebHit:
    hit: WebHit
    published: date | None
    assume_today_if_unknown: bool = False


def outlet_from_url(url: str) -> str:
    host = urlparse(url).hostname or urlparse(url).netloc or url
    if host.startswith("www."):
        host = host[4:]
    return host


class YandexTopNewsSearcher:
    """Yandex text (day) plus Russian news (day) for the Dashboard top-news rail."""

    def search(self, question: str) -> list[WebHit]:
        ranked = _collect_yandex_top_news(question)
        fresh = [
            item.hit
            for item in ranked
            if _is_fresh_for_rail(
                item.published,
                assume_today_if_unknown=item.assume_today_if_unknown,
            )
        ]
        return fresh


def _collect_yandex_top_news(question: str) -> list[_RankedWebHit]:
    from ddgs import DDGS

    ranked: list[_RankedWebHit] = []
    seen: set[str] = set()

    def add(
        *,
        title: str,
        url: str,
        snippet: str,
        published: date | None,
        assume_today_if_unknown: bool,
    ) -> None:
        if not url or url in seen:
            return
        seen.add(url)
        ranked.append(
            _RankedWebHit(
                hit=WebHit(title=title or outlet_from_url(url), url=url, snippet=snippet),
                published=published,
                assume_today_if_unknown=assume_today_if_unknown,
            )
        )

    with DDGS() as client:
        for row in client.text(
            question,
            region="ru-ru",
            timelimit="d",
            max_results=12,
            backend="yandex",
        ) or []:
            url = str(row.get("href") or row.get("url") or "")
            snippet = str(row.get("body") or row.get("snippet") or "")
            published = _infer_date_from_snippet(snippet)
            add(
                title=str(row.get("title") or ""),
                url=url,
                snippet=snippet,
                published=published,
                assume_today_if_unknown=published is None,
            )

    with DDGS() as client:
        for row in client.news(
            question,
            region="ru-ru",
            timelimit="d",
            max_results=12,
        ) or []:
            url = str(row.get("url") or "")
            published = _parse_iso_date(row.get("date"))
            add(
                title=str(row.get("title") or ""),
                url=url,
                snippet=str(row.get("body") or row.get("excerpt") or ""),
                published=published,
                assume_today_if_unknown=False,
            )

    ranked.sort(
        key=lambda item: (
            item.published or date.min,
            item.hit.title,
        ),
        reverse=True,
    )
    return ranked


def _cache_path(cache_dir: Path | None = None) -> Path:
    root = (
        cache_dir
        if cache_dir is not None
        else Path(os.environ.get("TOP_NEWS_CACHE_PATH") or "data/top_news_cache")
    )
    return root / "top_news_rail.json"


def _save_top_news_cache(payload: dict, *, cache_dir: Path | None = None) -> None:
    path = _cache_path(cache_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    body = {
        "query": SESSION_START_WEB_QUERY,
        "fetched_at": datetime.now(_MOSCOW).isoformat(),
        "hits": payload.get("hits") or [],
        "count": payload.get("count", 0),
        "note": payload.get("note", ""),
    }
    path.write_text(json.dumps(body, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_top_news_cache(*, cache_dir: Path | None = None) -> dict | None:
    path = _cache_path(cache_dir)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    hits = data.get("hits") or []
    if not hits:
        return None
    return {
        "hits": hits,
        "count": data.get("count", len(hits)),
        "note": data.get("note", ""),
        "cached": True,
        "fetched_at": data.get("fetched_at"),
    }


def _build_payload_from_ranked(ranked: list[_RankedWebHit]) -> dict:
    from oil_gas_analyst.turn import web_citation

    domains = load_denylist()
    rows = []
    for item in ranked:
        hit = item.hit
        cite = web_citation(hit)
        rows.append(
            {
                "citation": cite.label,
                "url": hit.url,
                "title": hit.title,
                "snippet": hit.snippet,
                "denied": is_denied(hit.url, domains),
                "published": item.published.isoformat() if item.published else None,
            }
        )
    note = (
        "Do not cite hits with denied=true (Yellow-press). Citing them is a prompt failure, "
        "not something the host will strip."
    )
    if not rows:
        note = "No Web sources. Do not invent news, oil prices, or volumes."
    return {"hits": rows, "count": len(rows), "note": note}


def cached_top_news_hits(*, cache_dir: Path | str | None = None) -> list[SessionStartRailHit]:
    """Instant rail from on-disk cache (no network)."""
    cache = Path(cache_dir) if cache_dir is not None else None
    payload = _load_top_news_cache(cache_dir=cache)
    if payload is None:
        return []
    return visible_rail_hits(payload)


def _fetch_live_top_news_payload(*, cache_dir: Path | None = None) -> dict:
    ranked = _collect_yandex_top_news(SESSION_START_WEB_QUERY)
    fresh = [
        item
        for item in ranked
        if _is_fresh_for_rail(
            item.published,
            assume_today_if_unknown=item.assume_today_if_unknown,
        )
    ]
    return _build_payload_from_ranked(fresh)


def refresh_top_news_hits(*, cache_dir: Path | str | None = None) -> list[SessionStartRailHit]:
    """Live fetch; keep cached hits visible when today has no fresh rows."""
    cache = Path(cache_dir) if cache_dir is not None else None
    fallback = cached_top_news_hits(cache_dir=cache)
    try:
        payload = _fetch_live_top_news_payload(cache_dir=cache)
        fresh = visible_rail_hits(payload)
        if fresh:
            _save_top_news_cache(payload, cache_dir=cache)
            return fresh
    except Exception:
        pass
    return fallback


def fetch_session_start_web(
    *,
    searcher=None,
    cache_dir: Path | str | None = None,
) -> dict:
    """One host Web fetch for the Dashboard session (not an Ouroboros turn)."""
    cache = Path(cache_dir) if cache_dir is not None else None
    payload: dict = {"hits": [], "count": 0, "note": "No Web sources. Do not invent news, oil prices, or volumes."}

    try:
        if searcher is not None:
            payload = search_for_tool(SESSION_START_WEB_QUERY, searcher=searcher)
        else:
            payload = _fetch_live_top_news_payload(cache_dir=cache)
    except Exception:
        pass

    if visible_rail_hits(payload):
        _save_top_news_cache(payload, cache_dir=cache)
        return payload

    cached_payload = _load_top_news_cache(cache_dir=cache)
    if cached_payload is not None:
        return cached_payload

    return payload


def visible_rail_hits(
    payload: dict,
    *,
    exclusions: Sequence[str] | None = None,
) -> list[SessionStartRailHit]:
    """Rows the executive may see and the Analyst may be injected with."""
    hidden = tuple(exclusions) if exclusions is not None else load_rail_exclusions()
    today = _today_moscow()
    from_cache = bool(payload.get("cached"))
    visible: list[SessionStartRailHit] = []
    for row in payload.get("hits") or []:
        if row.get("denied"):
            continue
        url = str(row.get("url") or "")
        if not url or _is_rail_hidden(url, hidden):
            continue
        published = _parse_iso_date(row.get("published"))
        if not from_cache and published is not None and published < today:
            continue
        visible.append(
            SessionStartRailHit(
                title=str(row.get("title") or outlet_from_url(url)),
                outlet=outlet_from_url(url),
                snippet=str(row.get("snippet") or ""),
                url=url,
                citation=str(row.get("citation") or ""),
                published=published,
            )
        )
    visible.sort(key=lambda hit: hit.published or date.min, reverse=True)
    return visible


def inject_session_start_web(question: str, hits: Sequence[SessionStartRailHit]) -> str:
    """Prepend visible top-news hits so the loop may cite them without search_web this turn."""
    if not hits:
        return question
    lines = [SESSION_START_INJECT_HEADER]
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
