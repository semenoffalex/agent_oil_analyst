# 0010. Chainlit is the user interface

## Status

Superseded for the **window** by [0026](0026-streamlit-dashboard-is-the-demo.md) (Streamlit Chat UI). The “not a second Analyst / not FastAPI product” rule remains.

## Context

The spec asked for a simple UI: Streamlit, Gradio, or FastAPI plus a minimal front end. Candidates in grilling were those three. The product owner chose Chainlit instead.

Chainlit is a Python chat shell aimed at LLM apps. It is not a second Analyst and not a FastAPI product.

## Decision

v1 is a Chainlit app. The reviewer opens one chat in the browser after Docker starts. LangGraph runs behind Chainlit. No Streamlit, no Gradio, no parallel FastAPI UI.

## Consequences

- `CMD` is `chainlit run …` (or equivalent) on one port.
- README must say why Chainlit instead of the three names in the spec: chat-native, Python-only, one process with LangGraph.
- Curl is not a first-class demo unless we add a side path later.
- Chainlit version pinning matters; UI lock-in is the library, not our HTML.
