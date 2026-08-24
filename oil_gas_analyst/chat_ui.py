from __future__ import annotations

import threading
import uuid
from collections.abc import Sequence
from typing import Callable

from oil_gas_analyst.deps import build_loop
from oil_gas_analyst.rate_limit import RateLimiter, client_key, load_rate_limit_config
from oil_gas_analyst.render import format_reply
from oil_gas_analyst.session_start_web import SessionStartRailHit
from oil_gas_analyst.turn import run_turn

_LOOP = None
_ERR: BaseException | None = None
_READY = threading.Event()
_RATE_LIMITER = RateLimiter()
_RATE_LIMIT_MSG = (
    "Demo rate limit reached for your IP. "
    "Try again in {retry_after}s. This is not a login gate."
)


def _warm() -> None:
    global _LOOP, _ERR
    try:
        _LOOP = build_loop()
    except BaseException as exc:
        _ERR = exc
    finally:
        _READY.set()


threading.Thread(target=_warm, daemon=True, name="warm-ouroboros").start()


def wait_loop():
    if not _READY.wait(timeout=60):
        raise TimeoutError("Timed out connecting to the Ouroboros gateway")
    if _ERR is not None:
        raise _ERR
    if _LOOP is None:
        raise RuntimeError("Analyst loop failed to load")
    return _LOOP


def rate_limit_key(session_id: str) -> str:
    return client_key(None, session_id)


def handle_chat_message(
    content: str,
    *,
    session_id: str,
    session_start_hits: Sequence[SessionStartRailHit] | None = None,
    chat_history: Sequence[dict[str, str]] | None = None,
    rate_limiter: RateLimiter | None = None,
    turn_runner: Callable[..., object] | None = None,
) -> str:
    """Run one Analyst turn with Demo rate limit."""
    cfg = load_rate_limit_config()
    limiter = rate_limiter or _RATE_LIMITER
    if cfg.enabled:
        allowed, retry_after = limiter.check(rate_limit_key(session_id), cfg)
        if not allowed:
            return _RATE_LIMIT_MSG.format(retry_after=retry_after)
    loop = wait_loop()
    if turn_runner is not None:
        reply = turn_runner(content, loop)
    else:
        reply = run_turn(
            content,
            loop,
            session_start_hits=session_start_hits or (),
            chat_history=chat_history or (),
        )
    return format_reply(reply, session_start_hits=session_start_hits or ())
