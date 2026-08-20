from __future__ import annotations

import concurrent.futures
import uuid

import streamlit as st

from oil_gas_analyst.chat_ui import handle_chat_message, wait_loop
from oil_gas_analyst.corpus_strip import corpus_strip_entries
from oil_gas_analyst.demo_auth import load_demo_login_config, verify_demo_login
from oil_gas_analyst.dashboard_chart import (
    CHART_UNCERTAINTY_COPY,
    chart_dataframe_from_payload,
    chart_refresh_horizon,
    kpi_from_chart_payload,
    load_brent_chart_payload,
)
from oil_gas_analyst.session_start_web import (
    RAIL_EMPTY_COPY,
    SessionStartRailHit,
    fetch_session_start_web,
    visible_rail_hits,
)

_INFRA_MSG = "I hit an infrastructure error and will not invent figures. ({exc})"
_DEFAULT_HORIZON = 21
_CHAT_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix="analyst-chat")

_DASHBOARD_CSS = """
<style>
    section[data-testid="stSidebar"] {display: none;}
    div[data-testid="stToolbar"] {visibility: hidden; height: 0;}
    header[data-testid="stHeader"] {background: transparent;}
    .block-container {padding-top: 1.25rem; max-width: 96rem;}
</style>
"""


def _session_id() -> str:
    if "rate_key" not in st.session_state:
        st.session_state.rate_key = str(uuid.uuid4())
    return st.session_state.rate_key


def chat_turn_in_progress(future: concurrent.futures.Future | None) -> bool:
    return future is not None and not future.done()


def _chat_future() -> concurrent.futures.Future | None:
    return st.session_state.get("chat_future")


def _logout_demo_session() -> None:
    future = st.session_state.get("chat_future")
    if isinstance(future, concurrent.futures.Future):
        future.cancel()
    st.session_state.demo_authenticated = False
    for key in (
        "chat_future",
        "chat_future_prompt",
        "messages",
        "session_start_web_hits",
        "brent_chart_payload",
        "brent_chart_horizon",
    ):
        st.session_state.pop(key, None)
    st.rerun()


def _ensure_session_start_web() -> list[SessionStartRailHit]:
    if "session_start_web_hits" not in st.session_state:
        payload = fetch_session_start_web()
        st.session_state.session_start_web_hits = visible_rail_hits(payload)
    return st.session_state.session_start_web_hits


def _reload_chart(*, horizon_days: int = _DEFAULT_HORIZON) -> dict:
    payload = load_brent_chart_payload(horizon_days=horizon_days)
    st.session_state.brent_chart_payload = payload
    st.session_state.brent_chart_horizon = horizon_days
    return payload


def _ensure_chart_payload() -> dict:
    if "brent_chart_payload" not in st.session_state:
        return _reload_chart()
    return st.session_state.brent_chart_payload


def _start_chat_turn(prompt: str) -> None:
    session_id = _session_id()
    session_hits = _ensure_session_start_web()

    def _run() -> str:
        return handle_chat_message(
            prompt,
            session_id=session_id,
            session_start_hits=session_hits,
        )

    st.session_state.chat_future_prompt = prompt
    st.session_state.chat_future = _CHAT_EXECUTOR.submit(_run)


def _finish_chat_turn_if_ready() -> bool:
    """Collect a completed background turn. Returns True when the page should rerun."""
    future = _chat_future()
    if not isinstance(future, concurrent.futures.Future) or not future.done():
        return False

    prompt = str(st.session_state.get("chat_future_prompt") or "")
    try:
        content = future.result()
    except concurrent.futures.CancelledError:
        st.session_state.pop("chat_future", None)
        st.session_state.pop("chat_future_prompt", None)
        return False
    except Exception as exc:
        content = _INFRA_MSG.format(exc=exc)

    st.session_state.messages.append({"role": "assistant", "content": content})
    st.session_state.pop("chat_future", None)
    st.session_state.pop("chat_future_prompt", None)

    refresh_horizon = chart_refresh_horizon(prompt) if prompt else None
    if refresh_horizon is not None:
        _reload_chart(horizon_days=refresh_horizon)
    return True


@st.fragment(run_every=1)
def _poll_chat_future() -> None:
    if _finish_chat_turn_if_ready():
        st.rerun()


def _render_kpi_row(payload: dict) -> None:
    kpis = kpi_from_chart_payload(payload)
    corpus = corpus_strip_entries()
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.caption("Brent close")
        close = kpis.get("close")
        st.metric("USD/bbl", f"{close:.2f}" if close is not None else "—")
    with c2:
        st.caption("SARIMA 21д")
        sarima = kpis.get("sarima")
        st.metric("horizon", f"{sarima:.2f}" if sarima is not None else "—")
    with c3:
        st.caption("Holt–Winters 21д")
        holt = kpis.get("holt_winters")
        st.metric("horizon", f"{holt:.2f}" if holt is not None else "—")
    with c4:
        st.caption("Корпус отчётов")
        if corpus:
            for entry in corpus:
                st.write(entry.label())
        else:
            st.write("—")


def _render_session_start_column(hits: list[SessionStartRailHit]) -> None:
    if not hits:
        st.markdown(RAIL_EMPTY_COPY)
        return
    for hit in hits:
        st.markdown(f"**{hit.title}**")
        st.caption(hit.outlet)
        snippet = hit.snippet.strip().replace("\n", " ")
        if snippet:
            st.write(snippet[:220] + ("…" if len(snippet) > 220 else ""))


def _render_chart_panel(payload: dict) -> None:
    st.subheader(f"Brent · факт + Forecast {payload.get('horizon_days', _DEFAULT_HORIZON)}д")
    frame = chart_dataframe_from_payload(payload)
    if frame is None:
        st.warning(CHART_UNCERTAINTY_COPY)
        if payload.get("unavailable_reason"):
            st.caption(str(payload["unavailable_reason"]))
        return
    st.line_chart(frame, height=180)
    st.caption("Две методики, без среднего. Urals на графике нет.")


@st.fragment
def _render_header(*, show_logout: bool) -> None:
    title_col, logout_col = st.columns([8, 1])
    with title_col:
        st.title("Oil & Gas Analyst")
        st.caption("Streamlit Dashboard — the turn runs in Ouroboros.")
    with logout_col:
        if show_logout:
            st.button(
                "Выйти",
                key="demo_logout",
                on_click=_logout_demo_session,
                use_container_width=True,
            )


def _render_login_gate() -> bool:
    cfg = load_demo_login_config()
    if not cfg.enabled:
        return True
    if st.session_state.get("demo_authenticated"):
        return True

    st.subheader("Вход")
    st.caption("Доступ к демо только по выданным учётным данным.")
    with st.form("demo_login", clear_on_submit=False):
        username = st.text_input("Логин", autocomplete="username")
        password = st.text_input("Пароль", type="password", autocomplete="current-password")
        submitted = st.form_submit_button("Войти", use_container_width=True)
    if submitted:
        if verify_demo_login(username, password, cfg):
            st.session_state.demo_authenticated = True
            st.rerun()
        st.error("Неверный логин или пароль.")
    return False


def _render_chat_history() -> None:
    st.subheader("Чат с аналитиком")
    st.caption("Вопрос о нефти, OPEC, Brent или прогнозе — ответ со ссылками на источники.")

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if chat_turn_in_progress(_chat_future()):
        with st.chat_message("assistant"):
            st.markdown("_Analyst is thinking… Обычно ответ приходит за 1–3 минуты._")


def main() -> None:
    st.set_page_config(
        page_title="Oil & Gas Analyst",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    st.markdown(_DASHBOARD_CSS, unsafe_allow_html=True)

    cfg = load_demo_login_config()
    if not _render_login_gate():
        return

    _render_header(show_logout=cfg.enabled)
    _poll_chat_future()

    if "messages" not in st.session_state:
        st.session_state.messages = []

    if _finish_chat_turn_if_ready():
        st.rerun()

    try:
        wait_loop()
    except Exception as exc:
        st.error(f"Startup failed. I will not invent figures. ({exc})")
        return

    chart_payload = _ensure_chart_payload()
    _render_kpi_row(chart_payload)

    _render_chat_history()

    st.divider()

    rail_col, chart_col = st.columns([1, 2], gap="large")
    with rail_col:
        st.subheader("Session-start Web")
        _render_session_start_column(_ensure_session_start_web())

    with chart_col:
        chart_header, chart_btn = st.columns([4, 1])
        with chart_btn:
            if st.button("Обновить график", use_container_width=True):
                _reload_chart(horizon_days=st.session_state.get("brent_chart_horizon", _DEFAULT_HORIZON))
                st.rerun()
        _render_chart_panel(st.session_state.brent_chart_payload)

    busy = chat_turn_in_progress(_chat_future())
    if prompt := st.chat_input(
        "Спросите о нефтегазовом рынке…",
        disabled=busy,
    ):
        st.session_state.messages.append({"role": "user", "content": prompt})
        _start_chat_turn(prompt)
        st.rerun()


if __name__ == "__main__":
    main()
