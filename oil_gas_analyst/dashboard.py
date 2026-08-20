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
    TOP_NEWS_RAIL_TITLE,
    SessionStartRailHit,
    fetch_session_start_web,
    visible_rail_hits,
)

_INFRA_MSG = "I hit an infrastructure error and will not invent figures. ({exc})"
_DEFAULT_HORIZON = 21
_CHAT_HINT = "Спросите о цене Brent, решениях ОПЕК+, прогнозе или заголовках из ленты выше."
_CHAT_INPUT_PLACEHOLDER = "Например: как изменилась цена Brent за последнюю неделю?"
_CHAT_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix="analyst-chat")

_DASHBOARD_CSS = """
<style>
    section[data-testid="stSidebar"] {display: none;}
    div[data-testid="stToolbar"] {visibility: hidden; height: 0;}
    header[data-testid="stHeader"] {background: transparent;}
    .block-container {padding-top: 1.25rem; max-width: 96rem; padding-bottom: 5.5rem;}
    .news-rail-card {font-size: 0.82rem; line-height: 1.3;}
    .news-rail-card p {margin-bottom: 0.25rem;}
    .chat-panel {
        margin-top: 1.25rem;
        padding-top: 0.75rem;
        border-top: 1px solid rgba(148, 163, 184, 0.22);
    }
    .chat-hint {
        color: rgba(148, 163, 184, 0.95);
        font-size: 0.95rem;
        margin: 0.25rem 0 0.9rem 0;
        line-height: 1.5;
        max-width: 52rem;
    }
    [data-testid="stChatInput"] {
        position: sticky;
        bottom: 0;
        z-index: 100;
        background: linear-gradient(transparent, var(--background-color) 28%);
        padding: 0.5rem 0 1rem;
        max-width: 52rem;
    }
    [data-testid="stChatInput"] textarea {
        min-height: 3rem;
        font-size: 1rem;
        line-height: 1.45;
        border: 1px solid rgba(148, 163, 184, 0.38);
        border-radius: 12px;
        box-shadow: 0 2px 10px rgba(15, 23, 42, 0.08);
        padding: 0.85rem 1rem;
    }
    [data-testid="stChatInput"] textarea:focus {
        border-color: rgba(96, 165, 250, 0.55);
        box-shadow: 0 2px 14px rgba(59, 130, 246, 0.12);
        outline: none;
    }
    [data-testid="stChatInput"] textarea::placeholder {
        color: rgba(148, 163, 184, 0.75);
        font-style: italic;
    }
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
        "_dashboard_loaded",
    ):
        st.session_state.pop(key, None)
    st.rerun()


def _bootstrap_dashboard_data() -> None:
    """Load chart and top news in parallel."""
    needs_chart = "brent_chart_payload" not in st.session_state
    needs_news = "session_start_web_hits" not in st.session_state
    if not needs_chart and not needs_news:
        return

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        chart_future = (
            pool.submit(load_brent_chart_payload, horizon_days=_DEFAULT_HORIZON)
            if needs_chart
            else None
        )
        news_future = (
            pool.submit(lambda: visible_rail_hits(fetch_session_start_web()))
            if needs_news
            else None
        )
        if chart_future is not None:
            st.session_state.brent_chart_payload = chart_future.result()
            st.session_state.brent_chart_horizon = _DEFAULT_HORIZON
        if news_future is not None:
            st.session_state.session_start_web_hits = news_future.result()


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


def _load_dashboard_data() -> tuple[dict, list[SessionStartRailHit]]:
    if st.session_state.get("_dashboard_loaded"):
        return _ensure_chart_payload(), _ensure_session_start_web()

    with st.status("Загрузка панели", expanded=True) as status:
        st.write("График Brent и котировки…")
        st.write("Топ новостей…")
        _bootstrap_dashboard_data()
        st.write("Чат с аналитиком…")
        wait_loop()
        status.update(label="Панель загружена", state="complete", expanded=False)

    st.session_state._dashboard_loaded = True
    return st.session_state.brent_chart_payload, st.session_state.session_start_web_hits


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
    if not chat_turn_in_progress(_chat_future()):
        return
    if _finish_chat_turn_if_ready():
        st.rerun()


def _render_corpus_strip() -> None:
    corpus = corpus_strip_entries()
    st.caption("Корпус отчётов")
    if corpus:
        for entry in corpus:
            st.write(entry.label())
    else:
        st.write("—")


def _render_kpi_row(payload: dict) -> None:
    kpis = kpi_from_chart_payload(payload)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.caption("Brent, закрытие")
        close = kpis.get("close")
        st.metric("долл./барр.", f"{close:.2f}" if close is not None else "—")
    with c2:
        st.caption("SARIMA, 21 дн.")
        sarima = kpis.get("sarima")
        st.metric("прогноз", f"{sarima:.2f}" if sarima is not None else "—")
    with c3:
        st.caption("Хольт–Винтерс, 21 дн.")
        holt = kpis.get("holt_winters")
        st.metric("прогноз", f"{holt:.2f}" if holt is not None else "—")


def _render_session_start_rail(hits: list[SessionStartRailHit], *, max_cards: int = 3) -> None:
    """Top-N narrow cards in a horizontal strip."""
    if not hits:
        st.caption(RAIL_EMPTY_COPY)
        return

    visible = hits[:max_cards]
    cols = st.columns(len(visible), gap="small")
    for col, hit in zip(cols, visible, strict=True):
        with col:
            with st.container(border=True, height=120):
                st.markdown(
                    f'<div class="news-rail-card"><strong>{hit.title[:72]}</strong></div>',
                    unsafe_allow_html=True,
                )
                st.caption(hit.outlet)
                snippet = hit.snippet.strip().replace("\n", " ")
                if snippet:
                    st.caption(snippet[:96] + ("…" if len(snippet) > 96 else ""))


def _render_news_and_corpus_row(hits: list[SessionStartRailHit]) -> None:
    news_col, corpus_col = st.columns([3, 1], gap="medium")
    with news_col:
        st.subheader(TOP_NEWS_RAIL_TITLE)
        _render_session_start_rail(hits, max_cards=3)
    with corpus_col:
        _render_corpus_strip()


def _render_chart_panel(payload: dict) -> None:
    horizon = payload.get("horizon_days", _DEFAULT_HORIZON)
    st.subheader(f"Brent · факт и прогноз {horizon} дн.")
    frame = chart_dataframe_from_payload(payload)
    if frame is None:
        st.warning(CHART_UNCERTAINTY_COPY)
        if payload.get("unavailable_reason"):
            st.caption(str(payload["unavailable_reason"]))
        return
    st.line_chart(frame, height=180)


@st.fragment
def _render_header(*, show_logout: bool) -> None:
    title_col, logout_col = st.columns([8, 1])
    with title_col:
        st.title("Нефтегазовый аналитик")
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
    """Скрыт временно: история чата не выводится на панель."""
    if chat_turn_in_progress(_chat_future()):
        with st.spinner("Аналитик готовит ответ… Обычно это занимает 1–3 минуты."):
            st.caption("Можно дождаться ответа здесь — поле ввода снова откроется после завершения.")


def _render_chat_panel(*, busy: bool) -> None:
    st.markdown('<div class="chat-panel">', unsafe_allow_html=True)
    st.subheader("Вопрос аналитику")
    st.markdown(f'<p class="chat-hint">{_CHAT_HINT}</p>', unsafe_allow_html=True)
    _render_chat_history()
    if prompt := st.chat_input(
        _CHAT_INPUT_PLACEHOLDER,
        disabled=busy,
    ):
        st.session_state.messages.append({"role": "user", "content": prompt})
        _start_chat_turn(prompt)
        st.rerun()


def main() -> None:
    st.set_page_config(
        page_title="Нефтегазовый аналитик",
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
        chart_payload, news_hits = _load_dashboard_data()
    except Exception as exc:
        st.error(f"Не удалось загрузить панель. ({exc})")
        return

    _render_kpi_row(chart_payload)
    _render_news_and_corpus_row(news_hits)
    _render_chart_panel(chart_payload)
    _render_chat_panel(busy=chat_turn_in_progress(_chat_future()))


if __name__ == "__main__":
    main()
