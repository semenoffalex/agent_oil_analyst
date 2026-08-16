from __future__ import annotations

import asyncio
import threading

try:
    import engineio.payload

    engineio.payload.Payload.max_decode_packets = 500
except Exception:
    pass

import chainlit as cl

from oil_gas_analyst.deps import build_deps
from oil_gas_analyst.graph import invoke_analyst
from oil_gas_analyst.turn import apply_citation_links, markdown_cite
from oil_gas_analyst.types import Reply

_DEPS = None
_ERR: BaseException | None = None
_READY = threading.Event()


def _warm() -> None:
    global _DEPS, _ERR
    try:
        _DEPS = build_deps()
    except BaseException as exc:
        _ERR = exc
    finally:
        _READY.set()


threading.Thread(target=_warm, daemon=True, name="warm-deps").start()


def _wait_deps():
    if not _READY.wait(timeout=600):
        raise TimeoutError("Timed out loading embeddings / Report index")
    if _ERR is not None:
        raise _ERR
    if _DEPS is None:
        raise RuntimeError("Analyst deps failed to load")
    return _DEPS


def format_reply(reply: Reply) -> str:
    parts = [apply_citation_links(reply.text.strip(), reply.citations)]
    if reply.citations:
        parts.append("\n**Sources**")
        parts.extend(f"- {markdown_cite(c)}" for c in reply.citations)
    flags = []
    if reply.refused:
        flags.append("refused")
    if reply.retrieved:
        flags.append("Reports retrieved")
    if reply.web_ran:
        flags.append("web")
    if reply.forecast_ran:
        flags.append("Forecast unavailable" if reply.forecast_failed else "Forecast")
    if flags:
        parts.append("\n_" + " · ".join(flags) + "_")
    return "\n".join(parts)


@cl.on_chat_start
async def start():
    msg = cl.Message(content="Loading embedding model and Report index…")
    await msg.send()
    try:
        await asyncio.to_thread(_wait_deps)
        msg.content = (
            "Senior oil-and-gas market Analyst. Ask about OPEC/EIA Reports, "
            "live market news, or a Forecast (use an explicit verb: "
            "forecast / спрогнозируй)."
        )
        await msg.update()
    except Exception as exc:
        msg.content = f"Startup failed. I will not invent figures. ({exc})"
        await msg.update()


@cl.on_message
async def on_message(message: cl.Message):
    try:
        deps = await asyncio.to_thread(_wait_deps)
        reply = await asyncio.to_thread(invoke_analyst, message.content, deps)
        await cl.Message(content=format_reply(reply)).send()
    except Exception as exc:
        await cl.Message(
            content=f"I hit an infrastructure error and will not invent figures. ({exc})"
        ).send()
