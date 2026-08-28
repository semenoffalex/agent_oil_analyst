from __future__ import annotations

import concurrent.futures
import html
import uuid

import streamlit as st

from oil_gas_analyst.chat_ui import handle_chat_message, wait_loop
from oil_gas_analyst.corpus_strip import corpus_strip_entries
from oil_gas_analyst.demo_auth import load_demo_login_config, verify_demo_login
from oil_gas_analyst.consensus_price import dashboard_kpi_row, report_consensus_price
from oil_gas_analyst.dashboard_chart import (
    CHART_METHOD_LABELS,
    CHART_METHOD_SHORT_LABELS,
    CHART_UNCERTAINTY_COPY,
    brent_chart_altair,
    chart_dataframe_from_payload,
    chart_display_dataframe,
    chart_refresh_horizon,
    forecast_model_consensus,
    load_brent_chart_payload,
    load_cached_brent_chart_payload,
)
from oil_gas_analyst.forecast import FORECAST_METHOD_ORDER
from oil_gas_analyst.session_start_web import (
    NEWS_REFRESH_COPY,
    RAIL_EMPTY_COPY,
    TOP_NEWS_RAIL_TITLE,
    SessionStartRailHit,
    cached_top_news_hits,
    refresh_top_news_hits,
    visible_rail_hits,
)
from oil_gas_analyst.topic_dynamics import (
    OTHER_KEY,
    OTHER_LABEL,
    TOPIC_CHART_EMPTY_COPY,
    TOPIC_PANEL_TITLE,
    TOPIC_REFRESH_COPY,
    load_cached_topic_payload,
    posts_for_topic,
    refresh_topic_dynamics_payload,
    topic_chart_dataframe,
    topic_payload_is_fresh,
    topic_streamgraph_altair,
)

_INFRA_MSG = "I hit an infrastructure error and will not invent figures. ({exc})"
_DEFAULT_HORIZON = 21
_CHAT_HINT = "Спросите о цене Brent, решениях ОПЕК+, прогнозе или заголовках из ленты выше."
_CHAT_INPUT_PLACEHOLDER = "Например: как изменилась цена Brent за последнюю неделю?"
_CHAT_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=4, thread_name_prefix="analyst-chat")
_CHART_LOADING_COPY = "Загрузка графика Brent…"
_CHAT_LOADING_COPY = "Подключение чата…"
_THINKING_COPY = "Аналитик готовит ответ… Обычно это занимает 30–60 секунд."
_THINKING_HINT = "Можно дождаться ответа здесь — поле ввода снова откроется после завершения."

_DASHBOARD_CSS = """
<style>
    :root {
        --workspace-height: 28rem;
        --chart-plot-height: 22rem;
        --chat-height: 17.5rem;
    }
    html, body, [data-testid="stAppViewContainer"], section.main {
        overflow-x: hidden;
    }
    [data-testid="stAppViewContainer"] > section.main {
        overflow: visible;
    }
    section[data-testid="stSidebar"] {display: none;}
    div[data-testid="stToolbar"] {visibility: hidden; height: 0;}
    header[data-testid="stHeader"] {background: transparent;}
    .stApp {overflow-x: hidden;}
    footer, [data-testid="stFooter"] {visibility: hidden; height: 0;}
    /* Streamlit 1.62+ titles the html shim "st.iframe"; do not match Vega charts. */
    iframe[title="streamlit_components_v1"],
    iframe[title="st.iframe"],
    [data-testid="stIFrame"] {
        display: block;
        height: 0 !important;
        min-height: 0 !important;
        width: 0 !important;
        border: 0;
        position: absolute !important;
        overflow: hidden !important;
    }
    [data-testid="stElementContainer"]:has(> iframe[title="streamlit_components_v1"]),
    [data-testid="element-container"]:has(> iframe[title="streamlit_components_v1"]),
    [data-testid="stElementContainer"]:has(> [data-testid="stIFrame"]),
    [data-testid="element-container"]:has(> [data-testid="stIFrame"]) {
        height: 0 !important;
        min-height: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
        overflow: hidden !important;
        position: absolute !important;
    }
    [data-testid="stAppViewContainer"] {padding-bottom: 0;}
    .block-container, [data-testid="stMainBlockContainer"] {
        padding-top: 0.75rem;
        max-width: 96rem;
        padding-bottom: 0 !important;
    }
    section.main > div.block-container {padding-bottom: 0;}
    h1 {margin-bottom: 0.15rem; font-size: 1.85rem;}
    h3 {margin-top: 0.55rem; margin-bottom: 0.2rem; font-size: 1.05rem;}
    div[data-testid="stMetric"] {margin-bottom: 0;}
    div[data-testid="stMetricLabel"] p {font-size: 0.82rem;}
    .news-rail-card {font-size: 0.82rem; line-height: 1.3;}
    .news-rail-card p {margin-bottom: 0.25rem;}
    .st-key-brent_chart_panel {
        min-height: var(--workspace-height);
        margin-top: 0.15rem;
    }
    .st-key-brent_chart_panel [data-testid="stArrowVegaLiteChart"] {
        min-height: var(--chart-plot-height);
        height: var(--chart-plot-height) !important;
    }
    .st-key-brent_chart_panel [data-testid="stArrowVegaLiteChart"] iframe {
        height: var(--chart-plot-height) !important;
        max-height: var(--chart-plot-height) !important;
    }
    .st-key-chat_panel {
        margin-top: 0.65rem;
        min-height: var(--chat-height);
        max-height: 22rem;
        overflow: hidden;
        display: flex;
        flex-direction: column;
    }
    .st-key-chat_panel [data-testid="stVerticalBlockBorderWrapper"] {
        flex: 1 1 auto;
        min-height: 0;
        overflow-y: auto;
    }
    .chat-hint {
        color: rgba(148, 163, 184, 0.95);
        font-size: 0.9rem;
        margin: 0.1rem 0 0.45rem 0;
        line-height: 1.4;
        max-width: none;
    }
    [data-testid="stChatInput"] {
        position: relative;
        bottom: auto;
        z-index: 1;
        background: transparent;
        padding: 0.35rem 0 0;
        max-width: none;
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
    .news-pill {
        font-size: 0.78rem;
        line-height: 1.35;
    }
    .news-pill-title {
        font-size: 0.8rem;
        font-weight: 600;
        line-height: 1.25;
        margin-bottom: 0.2rem;
    }
    .news-pill-title a {
        color: inherit;
        text-decoration: none;
    }
    .news-pill-title a:hover {
        color: rgba(96, 165, 250, 0.95);
        text-decoration: underline;
    }
    .corpus-pill {
        display: block;
        text-align: center;
        font-size: 0.78rem;
        line-height: 1.3;
        padding: 0.4rem 0.65rem;
        border: 1px solid rgba(148, 163, 184, 0.28);
        border-radius: 9999px;
    }
    .corpus-pill a {
        color: rgba(96, 165, 250, 0.95);
        text-decoration: none;
    }
    .corpus-pill a:hover {
        text-decoration: underline;
    }
    .kpi-metric-block {
        display: flex;
        align-items: flex-end;
        gap: 0.75rem;
        margin-top: -0.15rem;
    }
    .kpi-metric-main {
        flex: 0 0 auto;
        min-width: 0;
    }
    .kpi-metric-label {
        font-size: 0.875rem;
        line-height: 1.25;
        color: rgba(250, 250, 250, 0.6);
        margin-bottom: 0.1rem;
    }
    .kpi-metric-value {
        font-size: 2.25rem;
        font-weight: 600;
        line-height: 1.2;
        letter-spacing: -0.02em;
    }
    .kpi-metric-side {
        flex: 1 1 auto;
        min-width: 0;
        font-size: 0.72rem;
        line-height: 1.45;
        color: rgba(148, 163, 184, 0.95);
        padding-bottom: 0.3rem;
    }
    .kpi-metric-side div + div {
        margin-top: 0.08rem;
    }
    .kpi-corpus-list {
        margin-top: -0.1rem;
        font-size: 0.78rem;
        line-height: 1.4;
    }
    .kpi-corpus-line + .kpi-corpus-line {
        margin-top: 0.12rem;
    }
    .kpi-corpus-line a {
        color: rgba(96, 165, 250, 0.95);
        text-decoration: none;
    }
    .kpi-corpus-line a:hover {
        text-decoration: underline;
    }
    .topic-post {
        font-size: 0.85rem;
        line-height: 1.35;
        margin-bottom: 0.35rem;
    }
    .topic-post a {
        color: rgba(96, 165, 250, 0.95);
        text-decoration: none;
    }
    .topic-post a:hover {
        text-decoration: underline;
    }
    @keyframes analyst-avatar-pulse {
        0%, 100% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.62; transform: scale(0.94); }
    }
    div[data-testid="stChatMessage"]:has(.stCacheSpinner) [data-testid="stChatMessageAvatarAssistant"] {
        animation: analyst-avatar-pulse 1.2s ease-in-out infinite;
    }
    div[data-testid="stChatMessageContent"] {
        font-size: 0.96rem;
        line-height: 1.55;
        max-width: none;
    }
    div[data-testid="stChatMessageContent"] p {
        margin: 0 0 0.65rem 0;
    }
    div[data-testid="stChatMessageContent"] p:last-child {
        margin-bottom: 0;
    }
    div[data-testid="stChatMessageContent"] a {
        color: rgba(96, 165, 250, 0.95);
        text-decoration: underline;
        text-underline-offset: 2px;
    }
    div[data-testid="stChatMessageContent"] a:hover {
        color: rgba(147, 197, 253, 0.98);
    }
    div[data-testid="stChatMessageContent"] ul {
        margin: 0.35rem 0 0.65rem 1.1rem;
        padding: 0;
    }
    div[data-testid="stChatMessageContent"] .chat-flags {
        color: rgba(148, 163, 184, 0.9);
        font-size: 0.88rem;
        margin-top: 0.75rem;
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
        "reports_consensus",
        "_reports_consensus_loaded",
        "_news_refresh_future",
        "_ouroboros_future",
        "_ouroboros_ready",
        "_ouroboros_error",
        "_dashboard_refresh_started",
        "topic_payload",
        "_topics_hydrated",
        "_topics_refresh_future",
    ):
        st.session_state.pop(key, None)


def _hydrate_news_from_disk() -> list[SessionStartRailHit]:
    """Sync read of the on-disk news rail; safe to call every authenticated run."""
    if st.session_state.get("_session_start_web_hydrated"):
        return st.session_state.get("session_start_web_hits") or []

    hits = cached_top_news_hits()
    st.session_state.session_start_web_hits = hits
    st.session_state._session_start_web_hydrated = True
    st.session_state._session_start_web_from_cache = bool(hits)
    return hits


def _hydrate_topics_from_disk() -> dict | None:
    if st.session_state.get("_topics_hydrated"):
        return st.session_state.get("topic_payload")
    cached = load_cached_topic_payload()
    if cached is not None:
        st.session_state.topic_payload = cached
    st.session_state._topics_hydrated = True
    return st.session_state.get("topic_payload")


def _hydrate_from_disk_caches() -> None:
    _hydrate_news_from_disk()
    if "brent_chart_payload" not in st.session_state:
        cached = load_cached_brent_chart_payload(horizon_days=_DEFAULT_HORIZON)
        if cached is not None:
            st.session_state.brent_chart_payload = cached
            st.session_state.brent_chart_horizon = int(cached.get("horizon_days") or _DEFAULT_HORIZON)
    _hydrate_topics_from_disk()


def _chart_refresh_in_progress() -> bool:
    future = st.session_state.get("_chart_refresh_future")
    return isinstance(future, concurrent.futures.Future) and not future.done()


def _news_refresh_in_progress() -> bool:
    future = st.session_state.get("_news_refresh_future")
    return isinstance(future, concurrent.futures.Future) and not future.done()


def _topics_refresh_in_progress() -> bool:
    future = st.session_state.get("_topics_refresh_future")
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
    if not _topics_refresh_in_progress() and not topic_payload_is_fresh(
        st.session_state.get("topic_payload")
    ):
        st.session_state._topics_refresh_future = _CHAT_EXECUTOR.submit(
            refresh_topic_dynamics_payload
        )
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
                st.session_state._session_start_web_from_cache = False
        except Exception:
            pass
        st.session_state.pop("_news_refresh_future", None)
        updated = True

    topics_future = st.session_state.get("_topics_refresh_future")
    if isinstance(topics_future, concurrent.futures.Future) and topics_future.done():
        try:
            st.session_state.topic_payload = topics_future.result()
        except Exception as exc:
            st.session_state.topic_payload = {
                "topics": [],
                "series": [],
                "posts": [],
                "unavailable_reason": str(exc)[:240],
            }
        st.session_state.pop("_topics_refresh_future", None)
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
    if not st.session_state.get("_session_start_web_hydrated"):
        _hydrate_news_from_disk()
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


def _chat_history_for_turn() -> list[dict[str, str]]:
    messages = list(st.session_state.get("messages") or [])
    if messages and messages[-1].get("role") == "user":
        return messages[:-1]
    return messages


def _start_chat_turn(prompt: str) -> None:
    session_id = _session_id()
    session_hits = _ensure_session_start_web()
    history = _chat_history_for_turn()

    def _run() -> str:
        return handle_chat_message(
            prompt,
            session_id=session_id,
            session_start_hits=session_hits,
            chat_history=history,
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


def _chat_turn_pending() -> bool:
    return isinstance(_chat_future(), concurrent.futures.Future)


def _render_cached_spinner(container, text: str) -> None:
    """Persistent spinner for async turns (transient ``st.spinner`` clears too soon)."""

    from streamlit.elements.lib.layout_utils import create_layout_config
    from streamlit.proto.Spinner_pb2 import Spinner as SpinnerProto
    from streamlit.string_util import clean_text

    spinner_proto = SpinnerProto()
    spinner_proto.text = clean_text(text)
    spinner_proto.cache = True
    container._enqueue(
        "spinner",
        spinner_proto,
        layout_config=create_layout_config(width="content", allow_content_width=True),
    )


def _render_chat_messages() -> None:
    from oil_gas_analyst.render import chat_html

    for msg in st.session_state.get("messages") or []:
        with st.chat_message(msg["role"]):
            if msg["role"] == "assistant":
                st.markdown(chat_html(msg["content"]), unsafe_allow_html=True)
            else:
                st.markdown(msg["content"])


def _render_thinking_indicator() -> None:
    assistant_box = st.chat_message("assistant")
    with assistant_box:
        _render_cached_spinner(assistant_box, _THINKING_COPY)
        st.caption(_THINKING_HINT)


@st.fragment(run_every=1)
def _poll_chat_future() -> None:
    """Poll for completed turns without re-rendering the thinking animation."""
    if _finish_chat_turn_if_ready():
        st.rerun()


def _render_corpus_pill() -> None:
    corpus = corpus_strip_entries()
    st.caption("Корпус отчётов")
    if not corpus:
        st.caption("—")
        return
    rows = "".join(f'<div class="kpi-corpus-line">{entry.link_html()}</div>' for entry in corpus)
    st.markdown(f'<div class="kpi-corpus-list">{rows}</div>', unsafe_allow_html=True)


def _ensure_reports_consensus() -> float | None:
    cached = st.session_state.get("reports_consensus")
    if cached is not None or st.session_state.get("_reports_consensus_loaded"):
        return cached
    st.session_state.reports_consensus = report_consensus_price()
    st.session_state._reports_consensus_loaded = True
    return st.session_state.reports_consensus


def _render_kpi_corpus_row(
    chart_payload: dict | None,
    news_hits: list[SessionStartRailHit],
) -> None:
    kpis = dashboard_kpi_row(
        chart_payload,
        news_hits,
        report_consensus=_ensure_reports_consensus(),
    )
    c1, c2, c3, c4, c5 = st.columns([1, 1, 1, 1, 1.15], gap="small")
    with c1:
        st.caption("Brent, закрытие")
        close = kpis.get("close")
        st.metric("долл./барр.", f"{close:.2f}" if close is not None else "—")
    with c2:
        st.caption("Консенсус, отчёты")
        reports = kpis.get("reports_consensus")
        st.metric("долл./барр.", f"{reports:.2f}" if reports is not None else "—")
    with c3:
        st.caption("Консенсус, новости")
        news = kpis.get("news_consensus")
        st.metric("долл./барр.", f"{news:.2f}" if news is not None else "—")
    with c4:
        _render_forecast_consensus_pill(chart_payload)
    with c5:
        _render_corpus_pill()


def _render_forecast_consensus_pill(payload: dict | None) -> None:
    consensus = forecast_model_consensus(payload)
    average = consensus["average"]
    models: dict[str, float] = consensus["models"]  # type: ignore[assignment]
    st.caption("Прогноз моделей, 21 дн.")
    if average is None:
        st.metric("долл./барр.", "—")
        return
    side_lines = "".join(
        (
            f"<div>{html.escape(CHART_METHOD_SHORT_LABELS[name])} "
            f"{models[name]:.2f}</div>"
        )
        for name in FORECAST_METHOD_ORDER
        if name in models
    )
    st.markdown(
        (
            '<div class="kpi-metric-block">'
            '<div class="kpi-metric-main">'
            '<div class="kpi-metric-label">долл./барр.</div>'
            f'<div class="kpi-metric-value">{average:.2f}</div>'
            "</div>"
            f'<div class="kpi-metric-side">{side_lines}</div>'
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def _render_news_pills(
    hits: list[SessionStartRailHit],
    *,
    max_cards: int = 5,
    refreshing: bool = False,
) -> None:
    st.subheader(TOP_NEWS_RAIL_TITLE)
    if refreshing or _news_refresh_in_progress():
        st.caption(NEWS_REFRESH_COPY)

    if not hits:
        if refreshing or _news_refresh_in_progress():
            with st.spinner(NEWS_REFRESH_COPY):
                st.caption("Ищем свежие заголовки…")
            return
        if st.session_state.get("_session_start_web_from_cache"):
            st.caption(NEWS_REFRESH_COPY)
            return
        st.caption(RAIL_EMPTY_COPY)
        return

    visible = hits[:max_cards]
    cols = st.columns(max_cards, gap="small")
    for col, hit in zip(cols, visible, strict=True):
        with col:
            with st.container(border=True, height=100):
                title = html.escape(hit.title[:64] + ("…" if len(hit.title) > 64 else ""))
                url = html.escape(hit.url, quote=True)
                st.markdown(
                    f'<div class="news-pill"><div class="news-pill-title">'
                    f'<a href="{url}" target="_blank" rel="noopener">{title}</a></div></div>',
                    unsafe_allow_html=True,
                )
                snippet = hit.snippet.strip().replace("\n", " ")
                if snippet:
                    st.caption(snippet[:88] + ("…" if len(snippet) > 88 else ""))
                st.caption(hit.outlet)


def _render_chart_panel(payload: dict | None, *, refreshing: bool = False) -> None:
    with st.container(border=True, key="brent_chart_panel"):
        if payload is None:
            if refreshing or _chart_refresh_in_progress():
                with st.spinner(_CHART_LOADING_COPY):
                    st.caption("Считаем прогноз и подтягиваем котировки…")
                return
            st.warning(CHART_UNCERTAINTY_COPY)
            return

        horizon = payload.get("horizon_days", _DEFAULT_HORIZON)
        st.subheader(f"Brent · месяц и прогноз {horizon} дн.")
        if refreshing or _chart_refresh_in_progress():
            st.caption("Обновляем график…")
        frame = _chart_frame(payload)
        if frame is None:
            st.warning(CHART_UNCERTAINTY_COPY)
            if payload.get("unavailable_reason"):
                st.caption(str(payload["unavailable_reason"]))
            return
        toggle_row, _ = st.columns([3, 5])
        with toggle_row:
            t1, t2, t3 = st.columns(3)
            with t1:
                show_auto_arima = st.checkbox(
                    CHART_METHOD_LABELS["auto_arima"],
                    value=True,
                    key="chart_show_auto_arima",
                )
            with t2:
                show_ucm = st.checkbox(
                    CHART_METHOD_LABELS["unobserved_components"],
                    value=True,
                    key="chart_show_unobserved_components",
                )
            with t3:
                show_autoreg = st.checkbox(
                    CHART_METHOD_LABELS["autoreg"],
                    value=True,
                    key="chart_show_autoreg",
                )
        display_cols = ["Факт"]
        toggles = {
            "auto_arima": show_auto_arima,
            "unobserved_components": show_ucm,
            "autoreg": show_autoreg,
        }
        for name in FORECAST_METHOD_ORDER:
            if toggles[name]:
                display_cols.append(CHART_METHOD_LABELS[name])
        display_frame = chart_display_dataframe(frame)[display_cols]
        st.altair_chart(brent_chart_altair(display_frame, height=380), use_container_width=True)


def _render_topic_panel(payload: dict | None, *, refreshing: bool = False) -> None:
    title_col, btn_col = st.columns([8, 1])
    with title_col:
        st.subheader(TOPIC_PANEL_TITLE)
        if refreshing or _topics_refresh_in_progress():
            st.caption(TOPIC_REFRESH_COPY)
    with btn_col:
        if st.button(
            "Обновить темы",
            key="topics_refresh",
            use_container_width=True,
            disabled=refreshing or _topics_refresh_in_progress(),
        ):
            st.session_state._topics_refresh_future = _CHAT_EXECUTOR.submit(
                lambda: refresh_topic_dynamics_payload(force=True)
            )
            st.rerun()

    if payload is None:
        if refreshing or _topics_refresh_in_progress():
            with st.spinner(TOPIC_REFRESH_COPY):
                st.caption("Кластеризуем посты Reddit…")
            return
        st.caption(TOPIC_CHART_EMPTY_COPY)
        return

    frame = topic_chart_dataframe(payload)
    if frame is None:
        st.caption(TOPIC_CHART_EMPTY_COPY)
        if payload.get("unavailable_reason"):
            st.caption(str(payload["unavailable_reason"]))
        return

    chart = topic_streamgraph_altair(frame, height=280)
    st.altair_chart(chart, use_container_width=True)
    topics = payload.get("topics") or []
    other = next((row for row in topics if row.get("key") == OTHER_KEY), None)
    if other and int(other.get("size") or 0) > 0:
        st.caption(
            f"Река — топ-темы по комментариям. «{OTHER_LABEL}»: "
            f"{int(other['size'])} постов вне кластеров, на графике скрыты."
        )
    if not topics:
        return
    labels = [str(row.get("label") or row.get("key")) for row in topics]
    try:
        picked = st.pills("Тема", labels, key="topic_drill_label")
    except Exception:
        picked = st.radio("Тема", labels, index=None, horizontal=True, key="topic_drill_label")
    if not picked:
        st.caption("Выберите тему, чтобы увидеть посты за 30 дней.")
        return
    topic_key = next(
        (str(row["key"]) for row in topics if str(row.get("label")) == str(picked)),
        None,
    )
    if not topic_key:
        return
    label = next(
        (str(row["label"]) for row in (payload.get("topics") or []) if row.get("key") == topic_key),
        topic_key,
    )
    rows = posts_for_topic(payload, topic_key)
    st.caption(f"{label} · до {len(rows)} постов за окно")
    for row in rows:
        title = html.escape(str(row.get("title") or "")[:140])
        url = html.escape(str(row.get("url") or ""), quote=True)
        sub = html.escape(str(row.get("subreddit") or ""))
        n = int(row.get("num_comments") or 0)
        st.markdown(
            f'<div class="topic-post"><a href="{url}" target="_blank" rel="noopener">{title}</a>'
            f" · r/{sub} · {n} комм.</div>",
            unsafe_allow_html=True,
        )


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


def _render_chat_panel(*, busy: bool) -> None:
    messages = st.session_state.get("messages") or []
    pending = _chat_turn_pending()

    with st.container(border=True, key="chat_panel"):
        st.subheader("Вопрос аналитику")
        st.markdown(f'<p class="chat-hint">{_CHAT_HINT}</p>', unsafe_allow_html=True)
        if messages or pending:
            with st.container():
                _render_chat_messages()
                if pending:
                    _render_thinking_indicator()
        _poll_chat_future()

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

    _hydrate_from_disk_caches()

    if _render_header(show_logout=cfg.enabled):
        _logout_demo_session()
        st.rerun()

    _poll_dashboard_refresh()

    if "messages" not in st.session_state:
        st.session_state.messages = []

    if _finish_chat_turn_if_ready():
        st.rerun()

    _start_background_refreshes()
    _collect_background_refreshes()

    chart_payload = _ensure_chart_payload()
    news_hits = _ensure_session_start_web()
    topic_payload = st.session_state.get("topic_payload")
    chart_refreshing = _chart_refresh_in_progress()
    news_refreshing = _news_refresh_in_progress()
    topics_refreshing = _topics_refresh_in_progress()

    _render_kpi_corpus_row(chart_payload, news_hits)
    _render_news_pills(news_hits, max_cards=5, refreshing=news_refreshing)
    _render_topic_panel(topic_payload, refreshing=topics_refreshing)
    _render_chart_panel(chart_payload, refreshing=chart_refreshing)
    _render_chat_panel(busy=_chat_turn_pending())


if __name__ == "__main__":
    main()
