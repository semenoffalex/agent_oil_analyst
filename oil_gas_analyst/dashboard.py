from __future__ import annotations

import uuid

import streamlit as st

from oil_gas_analyst.chat_ui import handle_chat_message, wait_loop

_INFRA_MSG = "I hit an infrastructure error and will not invent figures. ({exc})"


def _session_id() -> str:
    if "rate_key" not in st.session_state:
        st.session_state.rate_key = str(uuid.uuid4())
    return st.session_state.rate_key


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
                    content = handle_chat_message(prompt, session_id=_session_id())
                except Exception as exc:
                    content = _INFRA_MSG.format(exc=exc)
            st.markdown(content)
        st.session_state.messages.append({"role": "assistant", "content": content})


if __name__ == "__main__":
    main()
