from __future__ import annotations

import os
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RateLimitConfig:
    max_requests: int
    window_sec: int

    @property
    def enabled(self) -> bool:
        return self.max_requests > 0 and self.window_sec > 0


def load_rate_limit_config() -> RateLimitConfig:
    """Read Demo rate-limit knobs from the environment (ADR 0017)."""
    max_requests = int(os.environ.get("DEMO_RATE_LIMIT_MAX", "0") or "0")
    window_sec = int(os.environ.get("DEMO_RATE_LIMIT_WINDOW_SEC", "3600") or "3600")
    return RateLimitConfig(max_requests=max_requests, window_sec=window_sec)


def client_key(environ: dict[str, Any] | None, session_id: str) -> str:
    """Prefer client IP; fall back to Chainlit session id."""
    if environ:
        forwarded = environ.get("HTTP_X_FORWARDED_FOR") or environ.get("x-forwarded-for")
        if forwarded:
            ip = str(forwarded).split(",")[0].strip()
            if ip:
                return f"ip:{ip}"
        for name in ("REMOTE_ADDR", "remote_addr"):
            ip = environ.get(name)
            if ip:
                return f"ip:{ip}"
    return f"session:{session_id}"


class RateLimiter:
    """In-memory sliding-window limiter (per process)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str, cfg: RateLimitConfig) -> tuple[bool, int]:
        """Return ``(allowed, retry_after_seconds)``."""
        if not cfg.enabled:
            return True, 0
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] >= cfg.window_sec:
                hits.popleft()
            if len(hits) >= cfg.max_requests:
                retry_after = int(cfg.window_sec - (now - hits[0])) + 1
                return False, max(retry_after, 1)
            hits.append(now)
            return True, 0
