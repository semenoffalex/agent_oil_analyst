# Map: Analyst Dashboard

Label: wayfinder:map

## Destination

A spec an implementer can execute: a **Dashboard** for a **senior bank executive** — one Streamlit page where **Chat UI** stays the centre, framed by current oil-market context. Context includes **one Session-start Web fetch** when the session opens (not a refresh loop). The turn still runs in the Ouroboros Analyst loop. This is not a second Analyst, Competence does not grow, and invented prices/volumes stay forbidden.

**Reached:** [spec.md](spec.md).

## Notes

- Domain: oil-and-gas Analyst. Read `CONTEXT.md`, `docs/adr/`, `.scratch/ouroboros-analyst/spec.md` before choosing a ticket. Use glossary terms (Analyst, Demo, Chat UI, Report, Web source, Live quote, Forecast, Competence). New names this map must pin: **Dashboard**, **Session-start Web**.
- Customer: high-ranking bank executive; the Dashboard **is** the expanded Demo ([Dashboard versus Demo and Eval](issues/04-dashboard-versus-demo.md)).
- Streamlit replaces Chainlit as Chat UI ([Streamlit is the click target](issues/03-streamlit-click-target.md), [0026](../../docs/adr/0026-streamlit-dashboard-is-the-demo.md)).
- This map **reopened** [0010](../../docs/adr/0010-chainlit-ui.md), [0021](../../docs/adr/0021-chainlit-adapter-ouroboros-loop.md), and Streamlit/charts clauses of [0017](../../docs/adr/0017-next-cycle-is-public-demo.md); they are superseded by [0026](../../docs/adr/0026-streamlit-dashboard-is-the-demo.md).
- Skills: grilling + domain-modeling on every HITL ticket. Research: findings under `research/`. Prototype: `/prototype` UI branch when layout is the question.
- Plan, don’t build. The map ends when the spec (or locked decision set) is ready to hand off.

## Decisions so far

- [What frames the chat for a bank executive](issues/01-what-frames-the-chat.md) — rail is Session-start Web + Live quote + Forecast chart + Report corpus dates; chat centre; no P&L.
- [Session-start Web fetch contract](issues/02-session-start-web-fetch.md) — host `search_for_tool` once with `нефть Brent OPEC+ цена добыча`; title/outlet/snippet; hide denylist on rail; Analyst may use those hits in follow-ups.
- [Streamlit is the click target](issues/03-streamlit-click-target.md) — Streamlit replaces Chainlit on `:8000`. ADR [0026](../../docs/adr/0026-streamlit-dashboard-is-the-demo.md).
- [Dashboard versus Demo and Eval](issues/04-dashboard-versus-demo.md) — expanded Demo, same Eval five dialogues, no password, rate limit stays.
- [Host Session-start Web versus the agent loop](issues/05-host-start-web-versus-loop.md) — host fetch, inject into later turns; not a silent Ouroboros task; loop Web still allowed.
- [Exec Dashboard layout](issues/09-exec-dashboard-layout.md) — **C брифинг KPI** (цифры сверху, новости слева, график+чат справа). Макет: [prototype/dashboard.html](prototype/dashboard.html)?variant=C.
- [May the Dashboard load price history without a Forecast request](issues/10-history-without-forecast-request.md) — on open: **actuals + 21d Forecast for Brent**; refresh on request.
- [What Forecast already plots](issues/06-what-forecast-already-plots.md) — tool JSON is two last-horizon points + intervals, not history or full paths. Detail: [forecast-plot-payload](research/forecast-plot-payload.md).
- [How Streamlit calls Ouroboros](issues/07-how-streamlit-calls-ouroboros.md) — same `build_loop` / `run_turn` / `POST /api/tasks` as Chainlit; replace CMD on `:8000`, don’t run two UIs. Detail: [streamlit-ouroboros-adapter](research/streamlit-ouroboros-adapter.md).
- [search_web without a question](issues/08-search-web-without-a-question.md) — host may call `search_for_tool`; empty list on DDG fail; `denied` flag; not permission to skip the loop. Detail: [session-start-search-web](research/session-start-search-web.md).
- [Where the Urals series comes from](issues/11-where-urals-series-comes-from.md) — **deferred**: Dashboard chart is Brent-only; Urals not on the rail; no Brent proxy.

## Not yet specified

None. Handoff: [spec.md](spec.md).

## Out of scope

- Implementing the Dashboard inside this map.
- Expanding Competence beyond oil and gas.
- IEA corpus, Urals series on the Dashboard chart, Prophet/LSTM, allowlist journalism classifier.
- A second Analyst or LangGraph as the conversation path.
- Turning `/evolve` on.
- A live rolling news ticker (customer allowed **one** fetch at session start, not a poll).
