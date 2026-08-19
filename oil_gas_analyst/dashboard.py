from __future__ import annotations

import uuid

import streamlit as st

from oil_gas_analyst.chat_ui import handle_chat_message, wait_loop
from oil_gas_analyst.session_start_web import (
    RAIL_EMPTY_COPY,
    fetch_session_start_web,
    visible_rail_hits,
)

_INFRA_MSG = "I hit an infrastructure error and will not invent figures. ({exc})"


def _session_id() -> str:
    if "rate_key" not in st.session_state:
        st.session_state.rate_key = str(uuid.uuid4())
    return st.session_state.rate_key


def _ensure_session_start_web():
    if "session_start_web_hits" not in st.session_state:
        payload = fetch_session_start_web()
        st.session_state.session_start_web_hits = visible_rail_hits(payload)
    return st.session_state.session_start_web_hits


def _render_session_start_rail() -> None:
    with st.sidebar:
        st.subheader("Session-start Web")
        hits = _ensure_session_start_web()
        if not hits:
            st.markdown(RAIL_EMPTY_COPY)
            return
        for hit in hits:
            st.markdown(f"**{hit.title}**")
            st.caption(f"{hit.outlet}")
            snippet = hit.snippet.strip().replace("\n", " ")
            if snippet:
                st.write(snippet[:320] + ("…" if len(snippet) > 320 else ""))


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

    _render_session_start_rail()

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Ask about the oil and gas market"):
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


if __name__ == "__main__":
    main()
