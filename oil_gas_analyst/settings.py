"""Main slot, DeepSeek chat credentials, and Ouroboros process pins (ADR 0027, 0024)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

DEEPSEEK_MODEL = "deepseek-v4-flash"
DEEPSEEK_BASE_URL_DEFAULT = "https://api.deepseek.com"
MAIN_MODEL = f"openai-compatible::{DEEPSEEK_MODEL}"


@dataclass(frozen=True)
class ModelSlots:
    main: str
    heavy: str
    light: str
    eval_chat: str
    skill_review: str
    fallbacks: str


def require_deepseek_key() -> str:
    """Return DEEPSEEK_API_KEY (or OPENAI_COMPATIBLE_API_KEY) or fail loudly."""

    key = (
        os.environ.get("DEEPSEEK_API_KEY", "").strip()
        or os.environ.get("OPENAI_COMPATIBLE_API_KEY", "").strip()
    )
    if not key:
        raise RuntimeError(
            "DEEPSEEK_API_KEY is missing. Copy .env.example to .env and set the DeepSeek key. "
            "There is no silent fallback to OpenRouter or Grok."
        )
    return key


def require_embedding_api_key() -> str:
    """Return EMBEDDING_API_KEY or OPENROUTER_API_KEY for Nemotron embeddings."""

    key = (
        os.environ.get("EMBEDDING_API_KEY", "").strip()
        or os.environ.get("OPENROUTER_API_KEY", "").strip()
    )
    if not key:
        raise RuntimeError(
            "EMBEDDING_API_KEY or OPENROUTER_API_KEY is missing. "
            "Embeddings use OpenRouter Nemotron; set one of these keys in .env."
        )
    return key


def require_openrouter_key() -> str:
    """Backward-compatible alias for embedding key checks in older call sites."""

    return require_embedding_api_key()


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


def normalize_chat_model(model: str) -> str:
    """Map bare ``deepseek-v4-flash`` to Ouroboros ``openai-compatible::`` lane."""

    name = model.strip()
    if not name:
        return MAIN_MODEL
    if "::" in name:
        return name
    if "/" in name:
        # OpenRouter-style slug (e.g. z-ai/glm-5.2:free) — leave unprefixed for explicit overrides.
        return name
    if name.startswith("openai-compatible/"):
        return f"openai-compatible::{name.split('/', 1)[1]}"
    return f"openai-compatible::{name}"


def resolve_model_slots() -> ModelSlots:
    """Main is DeepSeek V4 Flash via DeepSeek API. Unset slots use Main.

    An unset fallbacks chain is empty so Ouroboros cannot walk to Grok or OpenRouter.
    """

    main = normalize_chat_model(
        _env("MAIN_CHAT_MODEL") or _env("DEEPSEEK_MODEL") or _env("OUROBOROS_MODEL") or DEEPSEEK_MODEL
    )
    heavy_raw = _env("OUROBOROS_MODEL_HEAVY")
    light_raw = _env("OUROBOROS_MODEL_LIGHT")
    heavy = normalize_chat_model(heavy_raw) if heavy_raw else main
    light = normalize_chat_model(light_raw) if light_raw else main
    eval_raw = _env("EVAL_CHAT_MODEL")
    eval_chat = normalize_chat_model(eval_raw) if eval_raw else main
    review_raw = _env("OUROBOROS_REVIEW_MODELS")
    skill_review = normalize_chat_model(review_raw) if review_raw else main
    fallbacks = _env("OUROBOROS_MODEL_FALLBACKS")
    return ModelSlots(
        main=main,
        heavy=heavy,
        light=light,
        eval_chat=eval_chat,
        skill_review=skill_review,
        fallbacks=fallbacks,
    )


DOCKER_OUROBOROS_URL = "http://ouroboros:8765"
LOCAL_OUROBOROS_URL = "http://127.0.0.1:8765"
_LOOPBACK_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})


def running_in_docker() -> bool:
    return Path("/.dockerenv").exists()


def resolve_ouroboros_url() -> str:
    """Return the Ouroboros gateway URL for the Streamlit adapter.

    Inside Docker, loopback points at this container, not the ``ouroboros`` service.
    A developer ``.env`` with ``127.0.0.1`` must not override the compose network.
    """

    configured = os.environ.get("OUROBOROS_URL", "").strip()
    if not configured:
        return DOCKER_OUROBOROS_URL if running_in_docker() else LOCAL_OUROBOROS_URL
    host = (urlparse(configured).hostname or "").lower()
    if running_in_docker() and host in _LOOPBACK_HOSTS:
        return DOCKER_OUROBOROS_URL
    return configured.rstrip("/")


def ouroboros_process_env() -> dict[str, str]:
    """Env the Ouroboros process must see. Missing key raises. Thinking and evolve stay off."""

    key = require_deepseek_key()
    base_url = (
        _env("DEEPSEEK_BASE_URL")
        or _env("OPENAI_COMPATIBLE_BASE_URL")
        or DEEPSEEK_BASE_URL_DEFAULT
    ).rstrip("/")
    slots = resolve_model_slots()
    return {
        "OPENAI_COMPATIBLE_API_KEY": key,
        "OPENAI_COMPATIBLE_BASE_URL": base_url,
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
