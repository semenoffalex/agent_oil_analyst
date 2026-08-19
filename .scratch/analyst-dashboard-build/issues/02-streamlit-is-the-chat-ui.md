# 02 — Streamlit is the Chat UI

**What to build:** After one compose command the reviewer opens Streamlit at `localhost:8000` and chats with the same Analyst turn as today (`run_turn` → Ouroboros). Chainlit is not in the Demo image. Demo rate limit and Safety nets (timeout / 500 / empty only) stay. `:8765` is not the click target. Rails and chart may still be absent.

**Blocked by:** None — can start immediately.

**Status:** done

- [ ] One compose command serves Streamlit on port 8000; Chainlit is not the Demo process.
- [ ] A user message still completes via the Ouroboros loop; this is not a second Analyst.
- [ ] Demo rate limit still applies; no password.
- [ ] Safety nets fire only on timeout / 500 / empty completion, not on a live model reply.
- [ ] Frozen Analyst-turn tests still pass on the `question → reply` seam (not widgets).
