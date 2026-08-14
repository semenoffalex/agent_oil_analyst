from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Callable, Iterable

import yaml
from pypdf import PdfReader

from oil_gas_analyst.types import Chunk

_CONFIG = Path(__file__).resolve().parent.parent / "config" / "ingest.yaml"

TokenCount = Callable[[str], int]


def load_ingest_config(path: Path | None = None) -> dict:
    return yaml.safe_load((path or _CONFIG).read_text(encoding="utf-8"))


def _word_tokens(text: str) -> int:
    return len(text.split())


_E5_TOK = None


def e5_token_count(text: str) -> int:
    global _E5_TOK
    if os.environ.get("EMBEDDING_BASE_URL", "").strip():
        return _word_tokens(text)
    try:
        if _E5_TOK is None:
            from transformers import AutoTokenizer

            model = os.environ.get("EMBEDDING_MODEL", "intfloat/multilingual-e5-base")
            kwargs: dict = {}
            offline = os.environ.get("HF_HUB_OFFLINE", "").strip().lower() in {
                "1",
                "true",
                "yes",
            } or os.environ.get("TRANSFORMERS_OFFLINE", "").strip().lower() in {
                "1",
                "true",
                "yes",
            } or Path(model).is_dir()
            if offline:
                kwargs["local_files_only"] = True
            _E5_TOK = AutoTokenizer.from_pretrained(model, **kwargs)
        return len(_E5_TOK.encode(text, add_special_tokens=False))
    except Exception:
        return _word_tokens(text)


def _compile_headings(agency: str, config: dict) -> list[re.Pattern[str]]:
    raw = config.get("heading_patterns", {}).get(agency, [])
    return [re.compile(p, re.IGNORECASE) for p in raw]


def _is_heading(line: str, patterns: list[re.Pattern[str]], known: tuple[str, ...]) -> str | None:
    stripped = line.strip()
    if not stripped or len(stripped) > 120:
        return None
    for pat in patterns:
        if pat.search(stripped):
            return stripped
    for name in known:
        if stripped.lower() == name.lower() or stripped.lower().startswith(name.lower()):
            return name
    return None


_OPEC_HEADINGS = (
    "Crude Oil Price Movements",
    "World Oil Demand",
    "World Oil Supply",
    "Product Markets and Refinery Operations",
    "Tanker Market",
    "Crude and Refined Products Trade",
    "Stock Movements",
    "Balance of Supply and Demand",
    "Feature Article",
    "Appendix",
)

_EIA_HEADINGS = (
    "Global liquid fuels",
    "Global Oil Markets",
    "Global oil prices",
    "Highlights",
    "Overview",
    "Crude oil",
    "Petroleum products",
    "Natural gas",
    "Electricity",
    "Coal",
    "Renewables",
)


def _known_for(agency: str) -> tuple[str, ...]:
    if agency == "OPEC":
        return _OPEC_HEADINGS
    if agency == "EIA":
        return _EIA_HEADINGS
    return ()


def _flush(
    buf: list[str],
    heading: str,
    page_start: int | None,
    page_end: int | None,
    *,
    title: str,
    date: str | None,
    excerpt: bool,
    max_tokens: int,
    overlap: int,
    token_count: TokenCount,
) -> list[Chunk]:
    text = "\n".join(buf).strip()
    if not text:
        return []
    chunks: list[Chunk] = []
    words = text.split()
    if token_count(text) <= max_tokens:
        chunks.append(
            Chunk(
                text=text,
                title=title,
                date=date,
                page_start=page_start,
                page_end=page_end,
                heading=heading,
                excerpt=excerpt,
            )
        )
        return chunks
    step = max(max_tokens - overlap, 1)
    i = 0
    while i < len(words):
        piece = " ".join(words[i : i + max_tokens])
        chunks.append(
            Chunk(
                text=piece,
                title=title,
                date=date,
                page_start=page_start,
                page_end=page_end,
                heading=heading,
                excerpt=excerpt,
            )
        )
        i += step
    return chunks


def chunk_pages(
    pages: Iterable[tuple[int, str]],
    *,
    title: str,
    date: str | None,
    excerpt: bool,
    agency: str,
    config: dict,
    token_count: TokenCount | None = None,
) -> list[Chunk]:
    token_count = token_count or _word_tokens
    max_tokens = int(config.get("max_tokens", 512))
    overlap = int(config.get("overlap_tokens", 50))
    patterns = _compile_headings(agency, config)
    known = _known_for(agency)

    out: list[Chunk] = []
    heading = "(untitled)"
    buf: list[str] = []
    page_start: int | None = None
    page_end: int | None = None

    def emit():
        nonlocal buf, page_start, page_end
        out.extend(
            _flush(
                buf,
                heading,
                page_start,
                page_end,
                title=title,
                date=date,
                excerpt=excerpt,
                max_tokens=max_tokens,
                overlap=overlap,
                token_count=token_count,
            )
        )
        buf = []
        page_start = None
        page_end = None

    for page_no, text in pages:
        for line in text.splitlines():
            found = _is_heading(line, patterns, known)
            if found:
                emit()
                heading = found
            if page_start is None:
                page_start = page_no
            page_end = page_no
            buf.append(line)
    emit()
    return out


def chunk_pdf(
    path: Path,
    *,
    agency: str,
    excerpt: bool,
    date: str | None,
    title: str,
    config: dict | None = None,
    token_count: TokenCount | None = None,
) -> list[Chunk]:
    cfg = config or load_ingest_config()
    reader = PdfReader(str(path))
    pages = []
    for i, page in enumerate(reader.pages, start=1):
        pages.append((i, page.extract_text() or ""))
    return chunk_pages(
        pages,
        title=title,
        date=date,
        excerpt=excerpt,
        agency=agency,
        config=cfg,
        token_count=token_count,
    )
