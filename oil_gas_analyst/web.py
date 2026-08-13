from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

from ddgs import DDGS

from oil_gas_analyst.types import WebHit


class DuckDuckGoWeb:
    def search(self, question: str) -> list[WebHit]:
        hits: list[WebHit] = []
        try:
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
        return hits
