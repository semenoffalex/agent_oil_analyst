from __future__ import annotations

import chainlit as cl

from oil_gas_analyst.deps import build_deps
from oil_gas_analyst.graph import invoke_analyst
from oil_gas_analyst.types import Reply

_DEPS = None


def _deps():
    global _DEPS
    if _DEPS is None:
        _DEPS = build_deps()
    return _DEPS


def format_reply(reply: Reply) -> str:
    parts = [reply.text.strip()]
    if reply.citations:
        parts.append("\n**Sources**")
        parts.extend(f"- {c.label}" for c in reply.citations)
    flags = []
    if reply.refused:
        flags.append("refused")
    if reply.retrieved:
        flags.append("Reports retrieved")
    if reply.web_ran:
        flags.append("web")
    if reply.forecast_ran:
        flags.append("Forecast")
    if flags:
        parts.append("\n_" + " · ".join(flags) + "_")
    return "\n".join(parts)


@cl.on_chat_start
async def start():
    await cl.Message(
        content=(
            "Senior oil-and-gas market Analyst. Ask about OPEC/EIA Reports, "
            "live market news, or a Forecast (use an explicit verb: "
            "forecast / спрогнозируй)."
        )
    ).send()


@cl.on_message
async def on_message(message: cl.Message):
    try:
        reply = invoke_analyst(message.content, _deps())
        await cl.Message(content=format_reply(reply)).send()
    except Exception as exc:
        await cl.Message(
            content=f"I hit an infrastructure error and will not invent figures. ({exc})"
        ).send()
