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


def _contains(phrase: str, question: str) -> bool:
    q = question.casefold()
    p = phrase.casefold().strip()
    if not p:
        return False
    if " " in p or any(ord(c) > 127 for c in p):
        return p in q
    return re.search(rf"\b{re.escape(p)}\b", q) is not None


def is_forecast_request(question: str, lists: RouteLists) -> bool:
    return any(_contains(p, question) for p in lists.forecast_verbs)


def is_time_sensitive(question: str, lists: RouteLists) -> bool:
    return any(_contains(p, question) for p in lists.time_sensitive)
