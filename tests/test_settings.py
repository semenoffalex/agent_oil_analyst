"""Main slot and OpenRouter credentials (ADR 0023)."""

import pytest

from oil_gas_analyst.settings import (
    MAIN_MODEL,
    ouroboros_process_env,
    require_openrouter_key,
    resolve_model_slots,
)


def test_missing_openrouter_key_fails_loudly(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="OPENROUTER_API_KEY"):
        require_openrouter_key()


def test_deepseek_key_is_not_a_silent_fallback(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-deepseek-not-used")
    with pytest.raises(RuntimeError, match="OPENROUTER_API_KEY"):
        require_openrouter_key()


def test_unset_slots_use_main_glm_free_with_no_vendor_fallback(monkeypatch):
    monkeypatch.delenv("OUROBOROS_MODEL", raising=False)
    monkeypatch.delenv("MAIN_CHAT_MODEL", raising=False)
    monkeypatch.delenv("OUROBOROS_MODEL_HEAVY", raising=False)
    monkeypatch.delenv("OUROBOROS_MODEL_LIGHT", raising=False)
    monkeypatch.delenv("OUROBOROS_MODEL_FALLBACKS", raising=False)
    monkeypatch.delenv("EVAL_CHAT_MODEL", raising=False)
    monkeypatch.delenv("OUROBOROS_REVIEW_MODELS", raising=False)
    slots = resolve_model_slots()
    assert slots.main == MAIN_MODEL
    assert MAIN_MODEL == "z-ai/glm-5.2:free"
    assert slots.heavy == MAIN_MODEL
    assert slots.light == MAIN_MODEL
    assert slots.eval_chat == MAIN_MODEL
    assert slots.skill_review == MAIN_MODEL
    assert slots.fallbacks == ""
    assert "grok" not in slots.main
    assert "deepseek" not in slots.main.lower()


def test_env_overrides_heavy_and_eval_only(monkeypatch):
    monkeypatch.setenv("OUROBOROS_MODEL", "z-ai/glm-5.2:free")
    monkeypatch.setenv("OUROBOROS_MODEL_HEAVY", "some-heavy-id")
    monkeypatch.setenv("EVAL_CHAT_MODEL", "some-eval-id")
    monkeypatch.delenv("OUROBOROS_REVIEW_MODELS", raising=False)
    slots = resolve_model_slots()
    assert slots.main == "z-ai/glm-5.2:free"
    assert slots.heavy == "some-heavy-id"
    assert slots.eval_chat == "some-eval-id"
    assert slots.skill_review == slots.main


def test_ouroboros_process_env_pins_light_mode_and_thinking_off(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-test")
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
    assert env["OPENROUTER_API_KEY"] == "sk-or-v1-test"


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
    assert "OUROBOROS_RUNTIME_MODE: light" in text
    assert "OUROBOROS_TASK_REVIEW_MODE: off" in text
    assert "OUROBOROS_EFFORT_TASK: none" in text
    assert "z-ai/glm-5.2:free" in text
    assert "OUROBOROS_REVIEW_MODELS: ${OUROBOROS_REVIEW_MODELS:-}" in text
    assert "text-embedding-multilingual-e5-base" in text
    assert "192.168.0.55:1234" in text
    assert "/opt/models/multilingual-e5-base" not in text
    assert "LANGSMITH_PROJECT: ${LANGSMITH_PROJECT:-pr-drab-realization-91}" in text


def test_maybe_traceable_keeps_run_turn_callable():
    from oil_gas_analyst.settings import maybe_traceable

    @maybe_traceable("test.noop")
    def ping(x: int) -> int:
        return x + 1

    assert ping(1) == 2

