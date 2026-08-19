from oil_gas_analyst.types import Reply


def test_handle_chat_message_uses_run_turn(monkeypatch):
    from oil_gas_analyst import chat_ui

    class _Loop:
        pass

    monkeypatch.setattr(chat_ui, "wait_loop", lambda: _Loop())
    monkeypatch.setattr(
        chat_ui,
        "load_rate_limit_config",
        lambda: type("Cfg", (), {"enabled": False})(),
    )

    out = chat_ui.handle_chat_message(
        "What is Brent?",
        session_id="test-session",
        turn_runner=lambda question, loop: Reply(text=f"echo:{question}", retrieved=True),
    )
    assert "echo:What is Brent?" in out


def test_handle_chat_message_rate_limit(monkeypatch):
    from oil_gas_analyst import chat_ui

    class _Cfg:
        enabled = True

    class _Limiter:
        def check(self, key, cfg):
            return False, 42

    monkeypatch.setattr(chat_ui, "load_rate_limit_config", lambda: _Cfg())

    out = chat_ui.handle_chat_message(
        "hello",
        session_id="test-session",
        rate_limiter=_Limiter(),
    )
    assert "rate limit" in out.lower()
    assert "42" in out
