from __future__ import annotations

import html as html_module
import re
from collections.abc import Sequence

from oil_gas_analyst.ingest import load_ingest_config
from oil_gas_analyst.session_start_web import SessionStartRailHit
from oil_gas_analyst.turn import apply_citation_links, footer_flags, markdown_cite
from oil_gas_analyst.types import Citation, Reply

_WEB_BRACKET = re.compile(
    r"\[Источник\s*:\s*([^,\]]+?)\s*,\s*web\](?!\()",
    re.IGNORECASE,
)
_WEB_BARE = re.compile(
    r"(?<!\[)Источник\s*:\s*([^,;]+?)\s*,\s*web\s*\(\s*((?:https?)\s*:\s*//[^)]+?)\s*\)",
    re.IGNORECASE,
)
_WEB_INLINE = re.compile(
    r"(?<!\[)Источник\s*:\s*([^,;\]]+?)\s*,\s*web(?!\s*[\(\[])",
    re.IGNORECASE,
)
_REPORT_TAG = re.compile(r"\[Отчёт [^\]]+\](?!\()")
_REPORT_PAGE = re.compile(r",\s*p+\.\s*(\d+)", re.IGNORECASE)
_MD_LINK = re.compile(
    r"\[([^\]]+)\]\(\s*((?:https?)\s*:\s*//[^)]+?)\s*\)",
    re.IGNORECASE,
)
_GLUE_WORDS = (
    "сегодня",
    "днём",
    "утром",
    "вечером",
    "вчера",
    "впервые",
    "около",
    "примерно",
    "сессии",
    "контекста",
    "раннего",
    "более",
    "поднималась",
    "поднимался",
    "скорректировалась",
    "закрылась",
    "закрылся",
    "прибавила",
    "снизилась",
    "выросла",
    "упала",
    "пробивала",
    "допускает",
    "закрепление",
    "октябрьский",
    "фьючерс",
    "цена",
    "диапазоне",
    "экспертов",
    "пятый",
    "шестой",
    "седьмой",
    "выше",
    "ниже",
    "занеделю",
)
_GLUE_PHRASES = (
    (r"занеделю", "за неделю"),
    (r"пятыйденьростаподряд", "пятый день роста подряд"),
    (r"роста под ряд", "роста подряд"),
    (r"октябрьскийфьючерсна", "октябрьский фьючерс на"),
    (r"Изболеераннегоконтекстасессии", "Из более раннего контекста сессии"),
    (r"рядэкспертовдопускаетзакрепление", "ряд экспертов допускает закрепление"),
    (r"прибавилапримерно", "прибавила примерно"),
    (r"Brentвдиапазоне", "Brent в диапазоне"),
    (r"(\d)мск", r"\1 мск"),
    (r"\.К(\d)", r". К \1"),
    (r"К(\d{1,2})\s*:\s*(\d{2})мск", r"К \1:\2 мск"),
    (r"(?<![A-Za-z])К(\d{1,2})", r"К \1"),
)
_PROTECTED = re.compile(
    r"\[[^\]]+\]\([^)]+\)|\(\s*(?:https?\s*:\s*//[^)]+)\)|https?://\S+",
    re.IGNORECASE,
)


def _normalize_host(host: str) -> str:
    value = host.strip().lower()
    return value[4:] if value.startswith("www.") else value


def _clean_url(url: str) -> str:
    cleaned = url.strip().replace("—", "-").replace("–", "-")
    cleaned = re.sub(r"\s*-\s*", "-", cleaned)
    cleaned = re.sub(r"\s+", "", cleaned)
    return cleaned


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
        web_match = _WEB_BRACKET.fullmatch(citation.label.strip())
        if web_match:
            url = _web_url_for_host(web_match.group(1), session_hits)
        elif citation.label.startswith("[Отчёт"):
            url = _report_url_for_label(citation.label)
        enriched.append(
            Citation(kind=citation.kind, label=citation.label, url=url or citation.url)
        )
    return enriched


def _fix_markdown_links(text: str) -> str:
    def repl(match: re.Match[str]) -> str:
        return f"[{match.group(1).strip()}]({_clean_url(match.group(2))})"

    return _MD_LINK.sub(repl, text)


def _dedupe_trailing_urls(text: str) -> str:
    spaced_url = r"\(\s*(?:https?\s*:\s*//[^)]+)\)"
    while True:
        updated = re.sub(
            rf"(\]\([^)]+\))\s*{spaced_url}",
            r"\1",
            text,
            flags=re.IGNORECASE,
        )
        updated = re.sub(
            r"(\]\(https?://[^)]+\))\s*\(https?://[^)]+\)",
            r"\1",
            updated,
        )
        if updated == text:
            return text
        text = updated


def _strip_orphan_markdown(text: str) -> str:
    text = re.sub(r"\*\*(?=\[)", "", text)
    text = re.sub(r"(?<=\d)\*\*(?=\[)", "", text)
    return text


def _fix_bold_markdown(chunk: str) -> str:
    chunk = re.sub(r"\* +\*(?=[^*\s(])", "**", chunk)
    chunk = re.sub(r"(?<!\*)\*(?!\*)([^*\n]+)\*\*(?!\*)", r"**\1**", chunk)
    chunk = re.sub(r"(?<=\d)\s*\*\s*\*\s*\(", " × (", chunk)
    return chunk


def _link_web_brackets(text: str, hits: Sequence[SessionStartRailHit]) -> str:
    def repl(match: re.Match[str]) -> str:
        host = match.group(1).strip()
        url = _web_url_for_host(host, hits)
        if not url:
            return f"[Источник: {host}, web]"
        return f"[Источник: {host}, web]({url})"

    return _WEB_BRACKET.sub(repl, text)


def _link_inline_web_sources(text: str, hits: Sequence[SessionStartRailHit]) -> str:
    def repl(match: re.Match[str]) -> str:
        host = match.group(1).strip()
        url = _web_url_for_host(host, hits)
        if not url:
            return match.group(0)
        return f"[Источник: {host}, web]({url})"

    return _WEB_INLINE.sub(repl, text)


def _normalize_bare_web_citations(text: str) -> str:
    def repl(match: re.Match[str]) -> str:
        host = match.group(1).strip()
        url = _clean_url(match.group(2))
        return f"[Источник: {host}, web]({url})"

    return _WEB_BARE.sub(repl, text)


def _link_report_tags(text: str) -> str:
    def repl(match: re.Match[str]) -> str:
        label = match.group(0)
        url = _report_url_for_label(label)
        if not url:
            return label
        return markdown_cite(Citation(kind="report", label=label, url=url))

    return _REPORT_TAG.sub(repl, text)


def _split_glued_cyrillic(chunk: str) -> str:
    for word in sorted(_GLUE_WORDS, key=len, reverse=True):
        chunk = re.sub(rf"(?<=[а-яё])(?={re.escape(word)})", " ", chunk, flags=re.IGNORECASE)
    chunk = re.sub(r"(?<=[а-яё])(?=до)", " ", chunk)
    chunk = re.sub(r"до(?=\d)", "до ", chunk)
    chunk = re.sub(r"(?<=[а-яё])(?=на(?=(?:\s*(?:ICE|Brent|WTI|[A-Z]{2,}))))", " ", chunk)
    chunk = re.sub(r"(?<=[а-яё])(?=(?:ICE|Brent|WTI)\b)", " ", chunk)
    chunk = re.sub(r"(?<=ICE)(?=[а-яё])", " ", chunk)
    chunk = re.sub(r"(?<=Brent)(?=[а-яё])", " ", chunk)
    chunk = re.sub(r"(?<=WTI)(?=[а-яё])", " ", chunk)
    chunk = re.sub(r"(?<=\d)(?=[а-яё]{3,})", " ", chunk)
    chunk = re.sub(r"(?<=[.!?)\]])(?=[А-ЯA-Z])", " ", chunk)
    for pattern, replacement in _GLUE_PHRASES:
        chunk = re.sub(pattern, replacement, chunk, flags=re.IGNORECASE)
    return chunk


def _fix_prose_chunk(chunk: str) -> str:
    chunk = re.sub(r"(\d),\s+(\d)", r"\1,\2", chunk)
    chunk = re.sub(r"—(?=[а-яА-ЯёЁ0-9])", "— ", chunk)
    chunk = re.sub(r"(?<=[а-яё])(?=\d)", " ", chunk)
    chunk = re.sub(r"(?<=[а-яё])(?=[A-Z])", " ", chunk)
    chunk = _fix_bold_markdown(chunk)
    chunk = re.sub(r"(?<=[а-яё0-9%\)])(?=\[Источник)", " ", chunk, flags=re.IGNORECASE)
    chunk = re.sub(r"\)\s*;\s*(?=Источник\s*:)", ");\n\n", chunk, flags=re.IGNORECASE)
    chunk = re.sub(r";\s*(?=Источник\s*:)", ";\n\n", chunk, flags=re.IGNORECASE)
    chunk = re.sub(r"(\d)\s+:\s+(\d)", r"\1:\2", chunk)
    chunk = re.sub(r"(?<=[;)])\s*(?=[а-яА-Я])", "\n\n", chunk)
    chunk = re.sub(r"(?<=[.!?»\"])\s+(?=[А-ЯЁ])", "\n\n", chunk)
    chunk = _split_glued_cyrillic(chunk)
    chunk = re.sub(r" {2,}", " ", chunk)
    return chunk


def _fix_prose_spacing(text: str) -> str:
    parts: list[str] = []
    last = 0
    for match in _PROTECTED.finditer(text):
        parts.append(_fix_prose_chunk(text[last : match.start()]))
        parts.append(match.group(0))
        last = match.end()
    parts.append(_fix_prose_chunk(text[last:]))
    return "".join(parts)


def _prepare_body(
    text: str,
    citations: list[Citation],
    hits: Sequence[SessionStartRailHit] | None,
) -> str:
    session_hits = hits or ()
    body = text.strip()
    body = _normalize_bare_web_citations(body)
    body = _fix_markdown_links(body)
    body = apply_citation_links(body, citations)
    body = _link_web_brackets(body, session_hits)
    body = _link_inline_web_sources(body, session_hits)
    body = _link_report_tags(body)
    body = _dedupe_trailing_urls(body)
    body = _strip_orphan_markdown(body)
    body = _fix_prose_spacing(body)
    return body


def _sources_for_footer(body: str, citations: list[Citation]) -> list[Citation]:
    seen: set[str] = set()
    footer: list[Citation] = []
    for citation in citations:
        if not citation.url:
            continue
        label = citation.label
        if label not in body and f"]({citation.url})" not in body:
            continue
        key = citation.url
        if key in seen:
            continue
        seen.add(key)
        footer.append(citation)
    return footer


def format_reply(
    reply: Reply,
    *,
    session_start_hits: Sequence[SessionStartRailHit] | None = None,
) -> str:
    """Render chat message: linked body, Russian sources list, and footer flags."""

    citations = enrich_citations(list(reply.citations), session_start_hits)
    body = _prepare_body(reply.text, citations, session_start_hits)

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


def _md_inline_html(text: str) -> str:
    parts: list[str] = []
    cursor = 0
    pattern = re.compile(
        r"\[([^\]]+)\]\(([^)]+)\)|\*\*([^*]+)\*\*|\* *\*([^*]+)\*\*|_([^_]+)_",
    )
    for match in pattern.finditer(text):
        if match.start() > cursor:
            parts.append(html_module.escape(text[cursor : match.start()]))
        if match.group(1) is not None:
            label = html_module.escape(match.group(1).strip())
            url = html_module.escape(_clean_url(match.group(2)), quote=True)
            parts.append(
                f'<a href="{url}" target="_blank" rel="noopener noreferrer">{label}</a>'
            )
        elif match.group(3) is not None:
            parts.append(f"<strong>{html_module.escape(match.group(3))}</strong>")
        elif match.group(4) is not None:
            parts.append(f"<strong>{html_module.escape(match.group(4))}</strong>")
        elif match.group(5) is not None:
            parts.append(f"<em>{html_module.escape(match.group(5))}</em>")
        cursor = match.end()
    parts.append(html_module.escape(text[cursor:]))
    return "".join(parts)


def chat_html(markdown: str) -> str:
    """Render normalized chat markdown as HTML for Streamlit."""

    blocks: list[str] = []
    for block in markdown.split("\n\n"):
        block = block.strip()
        if not block:
            continue
        if block.startswith("**Источники**"):
            lines = block.split("\n")
            title = lines[0].removeprefix("**").removesuffix("**")
            items = "".join(
                f"<li>{_md_inline_html(line[2:].strip())}</li>"
                for line in lines[1:]
                if line.startswith("- ")
            )
            blocks.append(f"<p><strong>{html_module.escape(title)}</strong></p><ul>{items}</ul>")
            continue
        if block.startswith("_") and block.endswith("_"):
            inner = block[1:-1]
            blocks.append(f'<p class="chat-flags">{_md_inline_html(inner)}</p>')
            continue
        if block.startswith("- "):
            items = "".join(
                f"<li>{_md_inline_html(line[2:].strip())}</li>"
                for line in block.split("\n")
                if line.startswith("- ")
            )
            blocks.append(f"<ul>{items}</ul>")
            continue
        inner = "<br>".join(_md_inline_html(line) for line in block.split("\n"))
        blocks.append(f"<p>{inner}</p>")
    return "\n".join(blocks)
