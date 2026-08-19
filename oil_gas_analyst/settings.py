"""Main slot, OpenRouter credentials, and Ouroboros process pins (ADR 0023, 0024)."""

from __future__ import annotations

import os
from dataclasses import dataclass

MAIN_MODEL = "z-ai/glm-5.2:free"


@dataclass(frozen=True)
class ModelSlots:
    main: str
    heavy: str
    light: str
    eval_chat: str
    skill_review: str
    fallbacks: str


def require_openrouter_key() -> str:
    """Return OPENROUTER_API_KEY or fail loudly. DeepSeek/Grok are not fallbacks."""

    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "OPENROUTER_API_KEY is missing. Copy .env.example to .env and set the OpenRouter key. "
            "There is no silent fallback to DeepSeek or Grok."
        )
    return key


def _env(name: str) -> str:
    return os.environ.get(name, "").strip()


def maybe_traceable(name: str, run_type: str = "chain"):
    """LangSmith ``traceable`` when the package is installed; otherwise a no-op.

    Tracing is a no-op unless ``LANGSMITH_TRACING`` / ``LANGCHAIN_TRACING_V2`` is on
    and an API key is present. Does not wrap a live reply.
    """

    try:
        from langsmith import traceable
    except ImportError:
        def _passthrough(fn):
            return fn

        return _passthrough
    return traceable(name=name, run_type=run_type)


def resolve_model_slots() -> ModelSlots:
    """Main is GLM 5.2 free. Unset Heavy / Light / Eval / skill-review use Main.

    An unset fallbacks chain is empty so Ouroboros cannot walk to Grok or another vendor.
    """

    main = _env("MAIN_CHAT_MODEL") or _env("OUROBOROS_MODEL") or MAIN_MODEL
    heavy = _env("OUROBOROS_MODEL_HEAVY") or main
    light = _env("OUROBOROS_MODEL_LIGHT") or main
    eval_chat = _env("EVAL_CHAT_MODEL") or main
    skill_review = _env("OUROBOROS_REVIEW_MODELS") or main
    fallbacks = _env("OUROBOROS_MODEL_FALLBACKS")
    return ModelSlots(
        main=main,
        heavy=heavy,
        light=light,
        eval_chat=eval_chat,
        skill_review=skill_review,
        fallbacks=fallbacks,
    )


def ouroboros_process_env() -> dict[str, str]:
    """Env the Ouroboros process must see. Missing key raises. Thinking and evolve stay off."""

    key = require_openrouter_key()
    slots = resolve_model_slots()
    return {
        "OPENROUTER_API_KEY": key,
        "OUROBOROS_MODEL": slots.main,
        "OUROBOROS_MODEL_HEAVY": "" if slots.heavy == slots.main else slots.heavy,
        "OUROBOROS_MODEL_LIGHT": "" if slots.light == slots.main else slots.light,
        "OUROBOROS_MODEL_FALLBACKS": slots.fallbacks,
        "OUROBOROS_REVIEW_MODELS": slots.skill_review,
        "OUROBOROS_RUNTIME_MODE": _env("OUROBOROS_RUNTIME_MODE") or "light",
        "OUROBOROS_TASK_REVIEW_MODE": _env("OUROBOROS_TASK_REVIEW_MODE") or "off",
        "OUROBOROS_POST_TASK_EVOLUTION": _env("OUROBOROS_POST_TASK_EVOLUTION") or "false",
        "OUROBOROS_EFFORT_TASK": _env("OUROBOROS_EFFORT_TASK") or "none",
        "OUROBOROS_RETURN_REASONING": _env("OUROBOROS_RETURN_REASONING") or "false",
        "OUROBOROS_TRUST_NONLOCAL_BIND_WITHOUT_PASSWORD": "1",
    }
