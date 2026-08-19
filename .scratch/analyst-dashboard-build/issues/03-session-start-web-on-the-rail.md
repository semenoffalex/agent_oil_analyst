# 03 — Session-start Web on the rail

**What to build:** When the Streamlit session opens, the host runs one Web fetch with the canned query `нефть Brent OPEC+ цена добыча` (the executive does not type it). The rail shows title, outlet, and snippet. Yellow-press denylist domains are omitted from the rail. Those visible hits are injected into later turns so the Analyst may answer follow-ups; `[Источник: …, web]` on those URLs is grounded in this session’s fetch. Empty or failed search shows uncertainty copy, not invented headlines. The model may still call Web in the loop for facts not on the rail. This is not a silent Ouroboros turn and not a news ticker.

**Blocked by:** 02 — Streamlit is the Chat UI

**Status:** done

- [ ] Session open triggers exactly one host search with the canned Russian query.
- [ ] Shown hits have title, outlet, snippet; denylist domains are not on the rail.
- [ ] Visible hits are injected into later chat turns; loop Web remains allowed for new facts.
- [ ] Empty / failed search shows uncertainty; no invented headlines.
- [ ] Tests cover hidden denylist on the rail, empty-search copy, and inject-without-search_web-this-turn grounding for Session-start URLs.
