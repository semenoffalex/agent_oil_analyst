from __future__ import annotations

import os
import re
import statistics
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import TYPE_CHECKING

from oil_gas_analyst.ingest import load_ingest_config

if TYPE_CHECKING:
    from oil_gas_analyst.session_start_web import SessionStartRailHit

REPORT_CONSENSUS_QUERY = "Brent crude oil price forecast outlook USD per barrel"
PRICE_MIN_USD = 20.0
PRICE_MAX_USD = 200.0

_PRICE_PATTERNS = (
    re.compile(r"\$\s*(\d{1,3}(?:[.,]\d{1,2})?)"),
    re.compile(
        r"(\d{1,3}(?:[.,]\d{1,2})?)\s*(?:USD|usd)\s*/?\s*(?:bbl|barrel|b\b)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:Brent|брент|нефт\w*).*?(\d{2,3}(?:[.,]\d{1,2})?)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(\d{2,3}(?:[.,]\d{1,2})?)\s*(?:долл|USD|\$)\s*/?\s*(?:барр|bbl)",
        re.IGNORECASE,
    ),
)


def _parse_price_token(raw: str) -> float | None:
    try:
        value = float(str(raw).replace(",", "."))
    except ValueError:
        return None
    if PRICE_MIN_USD <= value <= PRICE_MAX_USD:
        return value
    return None


def extract_oil_prices(text: str) -> list[float]:
    """Pull plausible Brent/USD-per-barrel figures from free text."""
    if not text or not str(text).strip():
        return []
    found: list[float] = []
    seen: set[float] = set()
    for pattern in _PRICE_PATTERNS:
        for match in pattern.finditer(text):
            price = _parse_price_token(match.group(1))
            if price is None or price in seen:
                continue
            seen.add(price)
            found.append(price)
    return found


def consensus_from_texts(texts: Sequence[str]) -> float | None:
    """Average per-source means so one long report does not dominate."""
    per_source: list[float] = []
    for text in texts:
        prices = extract_oil_prices(text)
        if prices:
            per_source.append(statistics.fmean(prices))
    if not per_source:
        return None
    return statistics.fmean(per_source)


def _samples_dir() -> Path:
    root = Path(__file__).resolve().parent.parent
    return Path(os.environ.get("SAMPLES_PATH", str(root / "data" / "samples")))


def _resolve_sample_path(sample: dict, samples_dir: Path) -> Path | None:
    raw = str(sample.get("path") or "")
    if not raw:
        return None
    path = Path(raw)
    if not path.is_absolute():
        path = samples_dir / path.name
    return path if path.is_file() else None


def sample_report_texts(*, max_pages: int = 20) -> list[str]:
    """Read ingest sample PDFs when retrieve is unavailable."""
    from pypdf import PdfReader

    cfg = load_ingest_config()
    samples_dir = _samples_dir()
    texts: list[str] = []
    for sample in cfg.get("samples") or []:
        path = _resolve_sample_path(sample, samples_dir)
        if path is None:
            continue
        try:
            reader = PdfReader(str(path))
            pages = reader.pages[:max_pages]
            text = "\n".join(page.extract_text() or "" for page in pages)
        except Exception:
            continue
        if text.strip():
            texts.append(text)
    return texts


def report_consensus_price(
    *,
    retrieve: Callable[[str, int], Sequence[str]] | None = None,
    sample_texts: Callable[[], Sequence[str]] | None = None,
) -> float | None:
    texts: list[str] = []
    if retrieve is not None:
        texts.extend(str(t) for t in retrieve(REPORT_CONSENSUS_QUERY, 12))
    else:
        try:
            from oil_gas_analyst.retrieve import retrieve_for_tool

            payload = retrieve_for_tool(REPORT_CONSENSUS_QUERY, k=12)
            texts.extend(str(c.get("text") or "") for c in payload.get("chunks") or [])
        except Exception:
            pass
    if not texts:
        loader = sample_texts or sample_report_texts
        texts.extend(str(t) for t in loader())
    return consensus_from_texts(texts)


def news_consensus_price(hits: Sequence[SessionStartRailHit]) -> float | None:
    texts = [f"{hit.title}\n{hit.snippet}" for hit in hits]
    return consensus_from_texts(texts)


def dashboard_kpi_row(
    chart_payload: dict | None,
    news_hits: Sequence[SessionStartRailHit],
    *,
    report_consensus: float | None = None,
    news_consensus: float | None = None,
) -> dict[str, float | None]:
    close = (chart_payload or {}).get("live_quote")
    reports = report_consensus if report_consensus is not None else report_consensus_price()
    news = news_consensus if news_consensus is not None else news_consensus_price(news_hits)
    return {
        "close": close,
        "reports_consensus": reports,
        "news_consensus": news,
    }
