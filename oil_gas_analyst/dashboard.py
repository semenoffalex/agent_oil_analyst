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
    load_cached_brent_chart_payload,
)
from oil_gas_analyst.session_start_web import (
    NEWS_REFRESH_COPY,
    RAIL_EMPTY_COPY,
    TOP_NEWS_RAIL_TITLE,
    SessionStartRailHit,
    cached_top_news_hits,
    refresh_top_news_hits,
    visible_rail_hits,
)

_INFRA_MSG = "I hit an infrastructure error and will not invent figures. ({exc})"
_DEFAULT_HORIZON = 21
_CHAT_HINT = "Спросите о цене Brent, решениях ОПЕК+, прогнозе или заголовках из ленты выше."
_CHAT_INPUT_PLACEHOLDER = "Например: как изменилась цена Brent за последнюю неделю?"
_CHAT_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=3, thread_name_prefix="analyst-chat")
_CHART_LOADING_COPY = "Загрузка графика Brent…"
_CHAT_LOADING_COPY = "Подключение чата…"

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
        "_chart_frame",
        "_chart_frame_payload_id",
        "_chart_refresh_future",
        "_news_refresh_future",
        "_ouroboros_future",
        "_ouroboros_ready",
        "_ouroboros_error",
        "_dashboard_refresh_started",
    ):
        st.session_state.pop(key, None)


def _hydrate_from_disk_caches() -> None:
    if "brent_chart_payload" not in st.session_state:
        cached = load_cached_brent_chart_payload(horizon_days=_DEFAULT_HORIZON)
        if cached is not None:
            st.session_state.brent_chart_payload = cached
            st.session_state.brent_chart_horizon = int(cached.get("horizon_days") or _DEFAULT_HORIZON)
    if "session_start_web_hits" not in st.session_state:
        cached_hits = cached_top_news_hits()
        if cached_hits:
            st.session_state.session_start_web_hits = cached_hits


def _chart_refresh_in_progress() -> bool:
    future = st.session_state.get("_chart_refresh_future")
    return isinstance(future, concurrent.futures.Future) and not future.done()


def _news_refresh_in_progress() -> bool:
    future = st.session_state.get("_news_refresh_future")
    return isinstance(future, concurrent.futures.Future) and not future.done()


def _start_background_refreshes() -> None:
    if st.session_state.get("_dashboard_refresh_started"):
        return
    st.session_state._dashboard_refresh_started = True

    if not _chart_refresh_in_progress():
        st.session_state._chart_refresh_future = _CHAT_EXECUTOR.submit(
            load_brent_chart_payload,
            horizon_days=_DEFAULT_HORIZON,
        )
    if not _news_refresh_in_progress():
        st.session_state._news_refresh_future = _CHAT_EXECUTOR.submit(refresh_top_news_hits)
    if not st.session_state.get("_ouroboros_ready") and "_ouroboros_future" not in st.session_state:
        st.session_state._ouroboros_future = _CHAT_EXECUTOR.submit(wait_loop)


def _collect_background_refreshes() -> bool:
    updated = False

    chart_future = st.session_state.get("_chart_refresh_future")
    if isinstance(chart_future, concurrent.futures.Future) and chart_future.done():
        try:
            st.session_state.brent_chart_payload = chart_future.result()
            st.session_state.brent_chart_horizon = _DEFAULT_HORIZON
            st.session_state.pop("_chart_frame", None)
        except Exception:
            pass
        st.session_state.pop("_chart_refresh_future", None)
        updated = True

    news_future = st.session_state.get("_news_refresh_future")
    if isinstance(news_future, concurrent.futures.Future) and news_future.done():
        try:
            hits = news_future.result()
            if hits:
                st.session_state.session_start_web_hits = hits
        except Exception:
            pass
        st.session_state.pop("_news_refresh_future", None)
        updated = True

    ouroboros_future = st.session_state.get("_ouroboros_future")
    if isinstance(ouroboros_future, concurrent.futures.Future) and ouroboros_future.done():
        try:
            ouroboros_future.result()
            st.session_state._ouroboros_ready = True
            st.session_state.pop("_ouroboros_error", None)
        except Exception as exc:
            st.session_state._ouroboros_error = str(exc)
        st.session_state.pop("_ouroboros_future", None)
        updated = True

    return updated


@st.fragment(run_every=1)
def _poll_dashboard_refresh() -> None:
    if _collect_background_refreshes():
        st.rerun()


def _ensure_session_start_web() -> list[SessionStartRailHit]:
    if "session_start_web_hits" not in st.session_state:
        _hydrate_from_disk_caches()
    return st.session_state.get("session_start_web_hits") or []


def _reload_chart(*, horizon_days: int = _DEFAULT_HORIZON) -> dict:
    payload = load_brent_chart_payload(horizon_days=horizon_days)
    st.session_state.brent_chart_payload = payload
    st.session_state.brent_chart_horizon = horizon_days
    st.session_state.pop("_chart_frame", None)
    return payload


def _ensure_chart_payload() -> dict | None:
    if "brent_chart_payload" not in st.session_state:
        _hydrate_from_disk_caches()
    return st.session_state.get("brent_chart_payload")


def _chart_frame(payload: dict):
    cached = st.session_state.get("_chart_frame")
    if cached is not None and st.session_state.get("_chart_frame_payload_id") == id(payload):
        return cached
    frame = chart_dataframe_from_payload(payload)
    st.session_state._chart_frame = frame
    st.session_state._chart_frame_payload_id = id(payload)
    return frame


def _ouroboros_ready() -> bool:
    return bool(st.session_state.get("_ouroboros_ready"))


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


def _render_kpi_row(payload: dict | None) -> None:
    if payload is None:
        c1, c2, c3 = st.columns(3)
        with c1:
            st.caption("Brent, закрытие")
            st.metric("долл./барр.", "—")
        with c2:
            st.caption("SARIMA, 21 дн.")
            st.metric("прогноз", "—")
        with c3:
            st.caption("Хольт–Винтерс, 21 дн.")
            st.metric("прогноз", "—")
        return

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


def _render_session_start_rail(
    hits: list[SessionStartRailHit],
    *,
    max_cards: int = 3,
    refreshing: bool = False,
) -> None:
    """Top-N narrow cards in a horizontal strip."""
    if not hits:
        if refreshing or _news_refresh_in_progress():
            with st.spinner(NEWS_REFRESH_COPY):
                st.caption("Ищем свежие заголовки…")
            return
        st.caption(RAIL_EMPTY_COPY)
        return

    if refreshing or _news_refresh_in_progress():
        st.caption(NEWS_REFRESH_COPY)

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


def _render_news_and_corpus_row(
    hits: list[SessionStartRailHit],
    *,
    refreshing: bool = False,
) -> None:
    news_col, corpus_col = st.columns([3, 1], gap="medium")
    with news_col:
        st.subheader(TOP_NEWS_RAIL_TITLE)
        _render_session_start_rail(hits, max_cards=3, refreshing=refreshing)
    with corpus_col:
        _render_corpus_strip()


def _render_chart_panel(payload: dict | None, *, refreshing: bool = False) -> None:
    if payload is None:
        if refreshing or _chart_refresh_in_progress():
            with st.spinner(_CHART_LOADING_COPY):
                st.caption("Считаем прогноз и подтягиваем котировки…")
            return
        st.warning(CHART_UNCERTAINTY_COPY)
        return

    horizon = payload.get("horizon_days", _DEFAULT_HORIZON)
    st.subheader(f"Brent · факт и прогноз {horizon} дн.")
    if refreshing or _chart_refresh_in_progress():
        st.caption("Обновляем график…")
    frame = _chart_frame(payload)
    if frame is None:
        st.warning(CHART_UNCERTAINTY_COPY)
        if payload.get("unavailable_reason"):
            st.caption(str(payload["unavailable_reason"]))
        return
    st.line_chart(frame, height=180)


def _render_header(*, show_logout: bool) -> bool:
    """Title row. Returns True when the user clicked logout."""
    title_col, logout_col = st.columns([8, 1])
    with title_col:
        st.title("Нефтегазовый аналитик")
    with logout_col:
        if show_logout:
            return st.button(
                "Выйти",
                key="demo_logout",
                use_container_width=True,
            )
    return False


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

    chat_ready = _ouroboros_ready()
    chat_loading = (
        not chat_ready
        and (
            "_ouroboros_future" in st.session_state
            or st.session_state.get("_ouroboros_error") is None
        )
    )
    if chat_loading and not st.session_state.get("_ouroboros_error"):
        with st.spinner(_CHAT_LOADING_COPY):
            st.caption("Можно уже смотреть котировки и новости выше.")
    elif st.session_state.get("_ouroboros_error"):
        st.error(f"Чат недоступен. ({st.session_state._ouroboros_error})")

    if prompt := st.chat_input(
        _CHAT_INPUT_PLACEHOLDER,
        disabled=busy or not chat_ready,
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

    if _render_header(show_logout=cfg.enabled):
        _logout_demo_session()
        st.rerun()

    _poll_chat_future()
    _poll_dashboard_refresh()

    if "messages" not in st.session_state:
        st.session_state.messages = []

    if _finish_chat_turn_if_ready():
        st.rerun()

    _hydrate_from_disk_caches()
    _start_background_refreshes()
    _collect_background_refreshes()

    chart_payload = _ensure_chart_payload()
    news_hits = _ensure_session_start_web()
    chart_refreshing = _chart_refresh_in_progress()
    news_refreshing = _news_refresh_in_progress()

    _render_kpi_row(chart_payload)
    _render_news_and_corpus_row(news_hits, refreshing=news_refreshing)
    _render_chart_panel(chart_payload, refreshing=chart_refreshing)
    _render_chat_panel(busy=chat_turn_in_progress(_chat_future()))


if __name__ == "__main__":
    main()
