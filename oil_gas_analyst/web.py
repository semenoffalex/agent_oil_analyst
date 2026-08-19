from __future__ import annotations

import html as html_lib
import re
import urllib.error
import urllib.request
from collections.abc import Callable, Sequence
from urllib.parse import urlparse

from oil_gas_analyst.types import WebHit
from oil_gas_analyst.settings import maybe_traceable

_SCRIPT = re.compile(r"(?is)<(script|style|noscript|svg|iframe)\b[^>]*>.*?</\1>")
_TAG = re.compile(r"(?is)<[^>]+>")
_WS = re.compile(r"\s+")
_UA = (
    "Mozilla/5.0 (compatible; OilGasAnalyst/1.0; +https://localhost) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
_PAGE_LIMIT = 3
_PAGE_CHARS = 2000


def extract_html_text(raw: str) -> str:
    text = _SCRIPT.sub(" ", raw)
    text = _TAG.sub(" ", text)
    text = html_lib.unescape(text)
    return _WS.sub(" ", text).strip()


def fetch_page_text(url: str, timeout: float = 8.0) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return ""
    if parsed.path.lower().endswith(".pdf"):
        return ""
    req = urllib.request.Request(
        url,
        headers={"User-Agent": _UA, "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            ctype = (resp.headers.get_content_type() or "").casefold()
            if ctype and ctype not in {"text/html", "application/xhtml+xml", "text/plain"}:
                return ""
            raw = resp.read()
            charset = resp.headers.get_content_charset() or "utf-8"
            return raw.decode(charset, errors="replace")
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return ""


def fill_page_bodies(
    hits: list[WebHit],
    *,
    fetch_page: Callable[[str], str] | None = None,
    limit: int = _PAGE_LIMIT,
    max_chars: int = _PAGE_CHARS,
    denied_domains: Sequence[str] | None = None,
) -> list[WebHit]:
    """Keep every hit the searcher returned (denylist is a citation contract, not a drop)."""

    fetch = fetch_page or fetch_page_text
    out: list[WebHit] = []
    for i, hit in enumerate(hits):
        snippet = hit.snippet
        if i < limit:
            try:
                raw = fetch(hit.url) or ""
                text = extract_html_text(raw) if "<" in raw else raw
                text = _WS.sub(" ", text).strip()
                if text:
                    snippet = text[:max_chars]
            except Exception:
                snippet = hit.snippet
        out.append(WebHit(title=hit.title, url=hit.url, snippet=snippet))
    return out


class DuckDuckGoWeb:
    def __init__(self, fetch_page: Callable[[str], str] | None = None):
        self._fetch_page = fetch_page

    def search(self, question: str) -> list[WebHit]:
        hits: list[WebHit] = []
        try:
            from ddgs import DDGS

            with DDGS() as client:
                rows = client.text(question, max_results=8)
        except Exception:
            return []
        for row in rows or []:
            url = row.get("href") or row.get("url") or ""
            if not url:
                continue
            hits.append(
                WebHit(
                    title=row.get("title") or urlparse(url).netloc,
                    url=url,
                    snippet=row.get("body") or row.get("snippet") or "",
                )
            )
        return fill_page_bodies(hits, fetch_page=self._fetch_page)


@maybe_traceable("analyst.search_web", run_type="retriever")
def search_for_tool(query: str, searcher=None, k: int = 8) -> dict:
    """DuckDuckGo (or injected searcher) for the Ouroboros Web skill. Does not drop denylist URLs."""

    from oil_gas_analyst.denylist import is_denied, load_denylist
    from oil_gas_analyst.turn import web_citation

    hits = (searcher or DuckDuckGoWeb()).search(query)
    if k is not None:
        hits = hits[:k]
    domains = load_denylist()
    rows = []
    for hit in hits:
        cite = web_citation(hit)
        rows.append(
            {
                "citation": cite.label,
                "url": hit.url,
                "title": hit.title,
                "snippet": hit.snippet,
                "denied": is_denied(hit.url, domains),
            }
        )
    note = (
        "Do not cite hits with denied=true (Yellow-press). Citing them is a prompt failure, "
        "not something the host will strip."
    )
    if not rows:
        note = "No Web sources. Do not invent news, oil prices, or volumes."
    return {"hits": rows, "count": len(rows), "note": note}
