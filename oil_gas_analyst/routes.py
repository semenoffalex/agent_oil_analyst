from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

_CONFIG = Path(__file__).resolve().parent.parent / "config" / "route_lists.yaml"


@dataclass(frozen=True)
class RouteLists:
    forecast_verbs: tuple[str, ...]
    time_sensitive: tuple[str, ...]


def load_route_lists(path: Path | None = None) -> RouteLists:
    data = yaml.safe_load((path or _CONFIG).read_text(encoding="utf-8"))
    return RouteLists(
        forecast_verbs=tuple(data["forecast_verbs"]),
        time_sensitive=tuple(data["time_sensitive"]),
    )


_CYR = re.compile(r"[а-яё]", re.IGNORECASE)


def _is_cyr_stem(phrase: str) -> bool:
    """Truncated Route-list stems (прогнозир, текущ, актуальн, свеж)."""
    return phrase.endswith(("ир", "щ", "н", "ж")) and phrase != "прогноз"


def _contains(phrase: str, question: str) -> bool:
    q = question.casefold()
    p = phrase.casefold().strip()
    if not p:
        return False
    if _CYR.search(p):
        if _is_cyr_stem(p):
            return re.search(rf"(?<![а-яё]){re.escape(p)}[а-яё]*", q) is not None
        return re.search(rf"(?<![а-яё]){re.escape(p)}(?![а-яё])", q) is not None
    if " " in p:
        return p in q
    return re.search(rf"\b{re.escape(p)}\b", q) is not None


def is_forecast_request(question: str, lists: RouteLists) -> bool:
    return any(_contains(p, question) for p in lists.forecast_verbs)


def is_time_sensitive(question: str, lists: RouteLists) -> bool:
    return any(_contains(p, question) for p in lists.time_sensitive)


# Spec out-of-competence demos. A Forecast verb does not override these.
_OUT_OF_SCOPE = (
    "weather",
    "погод",
    "python",
    "world cup",
    "чемпионат мира",
    "uranium",
    "уран",
    "medicine",
    "медицин",
)


def is_out_of_scope_topic(question: str) -> bool:
    q = question.casefold()
    for phrase in _OUT_OF_SCOPE:
        p = phrase.casefold().strip()
        if not p:
            continue
        if _CYR.search(p):
            if re.search(rf"(?<![а-яё]){re.escape(p)}[а-яё]*", q):
                return True
            continue
        if _contains(p, question):
            return True
    return False
