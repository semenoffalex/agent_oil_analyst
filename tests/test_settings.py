"""Main slot and DeepSeek chat credentials (ADR 0027)."""

import pytest

from oil_gas_analyst.settings import (
    DEEPSEEK_MODEL,
    MAIN_MODEL,
    normalize_chat_model,
    ouroboros_process_env,
    require_deepseek_key,
    require_embedding_api_key,
    resolve_model_slots,
)


def test_missing_deepseek_key_fails_loudly(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_COMPATIBLE_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="DEEPSEEK_API_KEY"):
        require_deepseek_key()


def test_openrouter_key_is_not_a_silent_chat_fallback(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_COMPATIBLE_API_KEY", raising=False)
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-not-used-for-chat")
    with pytest.raises(RuntimeError, match="DEEPSEEK_API_KEY"):
        require_deepseek_key()


def test_missing_embedding_key_fails_loudly(monkeypatch):
    monkeypatch.delenv("EMBEDDING_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="OPENROUTER_API_KEY"):
        require_embedding_api_key()


def test_unset_slots_use_main_deepseek_flash_with_no_vendor_fallback(monkeypatch):
    monkeypatch.delenv("OUROBOROS_MODEL", raising=False)
    monkeypatch.delenv("MAIN_CHAT_MODEL", raising=False)
    monkeypatch.delenv("DEEPSEEK_MODEL", raising=False)
    monkeypatch.delenv("OUROBOROS_MODEL_HEAVY", raising=False)
    monkeypatch.delenv("OUROBOROS_MODEL_LIGHT", raising=False)
    monkeypatch.delenv("OUROBOROS_MODEL_FALLBACKS", raising=False)
    monkeypatch.delenv("EVAL_CHAT_MODEL", raising=False)
    monkeypatch.delenv("OUROBOROS_REVIEW_MODELS", raising=False)
    slots = resolve_model_slots()
    assert slots.main == MAIN_MODEL
    assert MAIN_MODEL == f"openai-compatible::{DEEPSEEK_MODEL}"
    assert slots.heavy == MAIN_MODEL
    assert slots.light == MAIN_MODEL
    assert slots.eval_chat == MAIN_MODEL
    assert slots.skill_review == MAIN_MODEL
    assert slots.fallbacks == ""
    assert "grok" not in slots.main
    assert "deepseek-v4-flash" in slots.main


def test_normalize_chat_model_adds_openai_compatible_prefix():
    assert normalize_chat_model("deepseek-v4-flash") == MAIN_MODEL
    assert normalize_chat_model(MAIN_MODEL) == MAIN_MODEL


def test_env_overrides_heavy_and_eval_only(monkeypatch):
    monkeypatch.setenv("OUROBOROS_MODEL", "openai-compatible::deepseek-v4-flash")
    monkeypatch.setenv("OUROBOROS_MODEL_HEAVY", "some-heavy-id")
    monkeypatch.setenv("EVAL_CHAT_MODEL", "some-eval-id")
    monkeypatch.delenv("OUROBOROS_REVIEW_MODELS", raising=False)
    slots = resolve_model_slots()
    assert slots.main == "openai-compatible::deepseek-v4-flash"
    assert slots.heavy == "openai-compatible::some-heavy-id"
    assert slots.eval_chat == "openai-compatible::some-eval-id"
    assert slots.skill_review == slots.main


def test_ouroboros_process_env_pins_light_mode_and_thinking_off(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-deepseek-test")
    monkeypatch.delenv("OUROBOROS_MODEL_FALLBACKS", raising=False)
    env = ouroboros_process_env()
    assert env["OUROBOROS_MODEL"] == MAIN_MODEL
    assert env["OUROBOROS_RUNTIME_MODE"] == "light"
    assert env["OUROBOROS_TASK_REVIEW_MODE"] == "off"
    assert env["OUROBOROS_POST_TASK_EVOLUTION"] == "false"
    assert env["OUROBOROS_EFFORT_TASK"] == "none"
    assert env["OUROBOROS_RETURN_REASONING"] in {"0", "false", "False"}
    assert env["OUROBOROS_MODEL_FALLBACKS"] == ""
    assert env["OUROBOROS_MODEL_LIGHT"] == ""
    assert "x-ai/grok" not in env["OUROBOROS_MODEL"]
    assert env["OPENAI_COMPATIBLE_API_KEY"] == "sk-deepseek-test"
    assert env["OPENAI_COMPATIBLE_BASE_URL"] == "https://api.deepseek.com"
    assert "OPENROUTER_API_KEY" not in env


def test_local_requirements_do_not_pull_legacy_langgraph_stack():
    from pathlib import Path

    pins = [
        line.split(">=", 1)[0].strip().lower()
        for line in Path("requirements.txt").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    assert "langchain" not in pins
    assert "langgraph" not in pins
    assert "langchain-openai" not in pins


def test_readme_names_ouroboros_adapter_evolve_off_and_port_8000():
    from pathlib import Path

    text = Path("README.md").read_text(encoding="utf-8")
    lower = text.lower()
    assert "ouroboros" in lower
    assert "streamlit" in lower
    assert "dashboard" in lower
    assert "reviewed skills" in lower or "reviewed skill" in lower
    assert "/evolve" in lower
    assert "8000" in text
    assert "chainlit" not in lower or "не chainlit" in lower
    assert "langgraph" in lower  # named as what we are not


def test_readme_eval_targets_streamlit_dashboard():
    from pathlib import Path

    text = Path("README.md").read_text(encoding="utf-8")
    lower = text.lower()
    assert "live_eval" in lower
    assert "testliveeval" in lower.replace("_", "")
    assert "streamlit" in lower
    assert "8765" not in text or "не нужен" in lower or ":8765" in lower


def test_compose_publishes_streamlit_only_and_pins_light_mode():
    from pathlib import Path

    text = Path("docker-compose.yml").read_text(encoding="utf-8")
    dockerfile = Path("Dockerfile").read_text(encoding="utf-8")
    analyst_req = Path("requirements-analyst.txt").read_text(encoding="utf-8").lower()
    assert "8000:8000" in text
    assert "8765:8765" not in text
    assert '"streamlit"' in dockerfile
    assert '"run"' in dockerfile
    assert "chainlit" not in analyst_req
    assert "streamlit" in analyst_req
    assert "statsmodels" in analyst_req
    assert "yfinance" in analyst_req
    assert "ddgs" in analyst_req
    assert "OUROBOROS_RUNTIME_MODE: light" in text
    assert "OUROBOROS_TASK_REVIEW_MODE: off" in text
    assert "OUROBOROS_EFFORT_TASK: none" in text
    assert "openai-compatible::deepseek-v4-flash" in text
    assert "DEEPSEEK_API_KEY" in text
    assert "OPENAI_COMPATIBLE_BASE_URL" in text
    assert "OUROBOROS_REVIEW_MODELS: ${OUROBOROS_REVIEW_MODELS:-}" in text
    assert "nvidia/nemotron-3-embed-1b:free" in text
    assert "openrouter.ai/api/v1" in text
    assert "/opt/models/multilingual-e5-base" not in text
    assert "LANGSMITH_PROJECT: ${LANGSMITH_PROJECT:-pr-drab-realization-91}" in text


def test_maybe_traceable_keeps_run_turn_callable():
    from oil_gas_analyst.settings import maybe_traceable

    @maybe_traceable("test.noop")
    def ping(x: int) -> int:
        return x + 1

    assert ping(1) == 2
