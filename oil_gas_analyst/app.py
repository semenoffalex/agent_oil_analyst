from __future__ import annotations

import asyncio
import threading

try:
    import engineio.payload

    engineio.payload.Payload.max_decode_packets = 500
except Exception:
    pass

import chainlit as cl

from oil_gas_analyst.deps import build_loop
from oil_gas_analyst.rate_limit import RateLimiter, client_key, load_rate_limit_config
from oil_gas_analyst.render import format_reply
from oil_gas_analyst.turn import run_turn
from oil_gas_analyst.types import Reply

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


def _wait_loop():
    if not _READY.wait(timeout=60):
        raise TimeoutError("Timed out connecting to the Ouroboros gateway")
    if _ERR is not None:
        raise _ERR
    if _LOOP is None:
        raise RuntimeError("Analyst loop failed to load")
    return _LOOP


@cl.on_chat_start
async def start():
    msg = cl.Message(content="Connecting to the Ouroboros Analyst…")
    await msg.send()
    try:
        await asyncio.to_thread(_wait_loop)
        msg.content = (
            "Senior oil-and-gas market Analyst. This window is Chainlit; "
            "the turn runs in Ouroboros. Ask about the oil and gas market."
        )
        await msg.update()
    except Exception as exc:
        msg.content = f"Startup failed. I will not invent figures. ({exc})"
        await msg.update()


@cl.on_message
async def on_message(message: cl.Message):
    cfg = load_rate_limit_config()
    if cfg.enabled:
        session = cl.context.session
        key = client_key(getattr(session, "environ", None), session.id)
        allowed, retry_after = _RATE_LIMITER.check(key, cfg)
        if not allowed:
            await cl.Message(content=_RATE_LIMIT_MSG.format(retry_after=retry_after)).send()
            return
    try:
        loop = await asyncio.to_thread(_wait_loop)
        reply = await asyncio.to_thread(run_turn, message.content, loop)
        await cl.Message(content=format_reply(reply)).send()
    except Exception as exc:
        await cl.Message(
            content=f"I hit an infrastructure error and will not invent figures. ({exc})"
        ).send()
