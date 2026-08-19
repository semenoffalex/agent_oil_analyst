from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from oil_gas_analyst.ingest import load_ingest_config
from oil_gas_analyst.retrieve import drop_redundant_excerpts

_AGENCIES = ("OPEC", "EIA", "CBR")


@dataclass(frozen=True)
class CorpusStripEntry:
    agency: str
    title: str
    date: str
    excerpt: bool

    def label(self) -> str:
        suffix = " (excerpt)" if self.excerpt else ""
        return f"{self.title}, {self.date}{suffix}"


def _samples_dir() -> Path:
    root = Path(__file__).resolve().parent.parent
    return Path(os.environ.get("SAMPLES_PATH", str(root / "data" / "samples")))


def _resolve_path(sample: dict, samples_dir: Path) -> Path | None:
    raw = str(sample.get("path") or "")
    if not raw:
        return None
    path = Path(raw)
    if not path.is_absolute():
        path = samples_dir / path.name
    return path if path.is_file() else None


def corpus_strip_entries(
    *,
    cfg: dict | None = None,
    samples_dir: Path | None = None,
) -> list[CorpusStripEntry]:
    """Report corpus metadata for the Dashboard strip (not a retrieve)."""
    config = cfg or load_ingest_config()
    samples_root = samples_dir or _samples_dir()
    samples = drop_redundant_excerpts(list(config.get("samples") or []))
    by_agency: dict[str, CorpusStripEntry] = {}
    for sample in samples:
        agency = str(sample.get("agency") or "")
        if agency not in _AGENCIES:
            continue
        if _resolve_path(sample, samples_root) is None:
            continue
        entry = CorpusStripEntry(
            agency=agency,
            title=str(sample.get("title") or agency),
            date=str(sample.get("date") or ""),
            excerpt=bool(sample.get("excerpt", False)),
        )
        current = by_agency.get(agency)
        if current is None or entry.date > current.date:
            by_agency[agency] = entry
    return [by_agency[agency] for agency in _AGENCIES if agency in by_agency]
