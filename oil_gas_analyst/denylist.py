from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

import yaml

_CONFIG = Path(__file__).resolve().parent.parent / "config" / "yellow_press_denylist.yaml"


def load_denylist(path: Path | None = None) -> tuple[str, ...]:
    data = yaml.safe_load((path or _CONFIG).read_text(encoding="utf-8"))
    return tuple(d.casefold().strip() for d in data["domains"])


def is_denied(url: str, domains: list[str] | tuple[str, ...]) -> bool:
    host = (urlparse(url).hostname or "").casefold()
    if host.startswith("www."):
        host = host[4:]
    for raw in domains:
        d = raw.casefold().strip()
        if host == d or host.endswith("." + d):
            return True
    return False
