from __future__ import annotations

import uuid

import streamlit as st

from oil_gas_analyst.chat_ui import handle_chat_message, wait_loop
from oil_gas_analyst.corpus_strip import corpus_strip_entries
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


def _session_id() -> str:
    if "rate_key" not in st.session_state:
        st.session_state.rate_key = str(uuid.uuid4())
    return st.session_state.rate_key


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
    st.subheader("Session-start Web")
    if not hits:
        st.markdown(RAIL_EMPTY_COPY)
        return
    for hit in hits:
        st.markdown(f"**{hit.title}**")
        st.caption(hit.outlet)
        snippet = hit.snippet.strip().replace("\n", " ")
        if snippet:
            st.write(snippet[:320] + ("…" if len(snippet) > 320 else ""))


def _render_chart_panel(payload: dict) -> None:
    st.subheader(f"Brent · факт + Forecast {payload.get('horizon_days', _DEFAULT_HORIZON)}д")
    frame = chart_dataframe_from_payload(payload)
    if frame is None:
        st.warning(CHART_UNCERTAINTY_COPY)
        if payload.get("unavailable_reason"):
            st.caption(str(payload["unavailable_reason"]))
        return
    st.line_chart(frame, height=220)
    st.caption("Две методики, без среднего. Urals на графике нет.")


def main() -> None:
    st.set_page_config(page_title="Oil & Gas Analyst", layout="wide")
    st.title("Oil & Gas Analyst")
    st.caption("Streamlit Dashboard — the turn runs in Ouroboros.")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    try:
        wait_loop()
    except Exception as exc:
        st.error(f"Startup failed. I will not invent figures. ({exc})")
        return

    chart_payload = _ensure_chart_payload()
    _render_kpi_row(chart_payload)

    left, right = st.columns([1, 2], gap="large")
    with left:
        _render_session_start_column(_ensure_session_start_web())

    with right:
        chart_header, chart_btn = st.columns([4, 1])
        with chart_header:
            pass
        with chart_btn:
            if st.button("Обновить график", use_container_width=True):
                _reload_chart(horizon_days=st.session_state.get("brent_chart_horizon", _DEFAULT_HORIZON))
                st.rerun()

        _render_chart_panel(st.session_state.brent_chart_payload)

        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        if prompt := st.chat_input("Ask about the oil and gas market"):
            refresh_horizon = chart_refresh_horizon(prompt)
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            with st.chat_message("assistant"):
                with st.spinner("Analyst is thinking…"):
                    try:
                        content = handle_chat_message(
                            prompt,
                            session_id=_session_id(),
                            session_start_hits=_ensure_session_start_web(),
                        )
                    except Exception as exc:
                        content = _INFRA_MSG.format(exc=exc)
                st.markdown(content)
            st.session_state.messages.append({"role": "assistant", "content": content})
            if refresh_horizon is not None:
                _reload_chart(horizon_days=refresh_horizon)
                st.rerun()


if __name__ == "__main__":
    main()
