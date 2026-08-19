# 0026. Streamlit Dashboard is the Demo Chat UI

## Status

Accepted

## Context

The reviewer Demo was Chainlit on `:8000` as an adapter over Ouroboros ([0021](0021-chainlit-adapter-ouroboros-loop.md), [0010](0010-chainlit-ui.md)). [0017](0017-next-cycle-is-public-demo.md) kept Streamlit and Forecast charts out of that cycle. The customer then asked for a **Dashboard** for a senior bank executive: chat in the centre, framed by current oil-market context, Streamlit instead of Chainlit. That screen **is** the Demo, expanded — not a second app.

## Decision

**Chat UI** is Streamlit at `http://localhost:8000` after one compose command. Chainlit is not in the Demo image. The Analyst turn is unchanged: Streamlit calls `run_turn` → Ouroboros `POST /api/tasks`. `:8765` is not the click target.

The Demo page always shows, around chat:

- **Session-start Web** — one host `search_for_tool` when the session opens, query `нефть Brent OPEC+ цена добыча` (titles, outlets, snippets; no poll). Denied domains are omitted from the rail. Those hits are injected into later turns so the Analyst may answer follow-ups about them.
- A **Forecast** chart at session start: **actuals + 21 trading-day Forecast** for **Brent** (two methods, no average). Last history close is the Live quote on that chart. Refresh on request. Urals is not on the chart ([Where the Urals series comes from](../../.scratch/analyst-dashboard/issues/11-where-urals-series-comes-from.md)).
- A **Report** corpus strip (OPEC / EIA / CBR titles and dates from Sample/Full Reports, not a second retrieve).

Layout for implementers: prototype variant **C** ([Exec Dashboard layout](../../.scratch/analyst-dashboard/issues/09-exec-dashboard-layout.md)). No password; Demo rate limit stays. Competence, denylist-in-answers, and `[Отчёт …]` grounding stay, except Session-start URLs count as grounded Web for that session.

## Consequences

- [0010](0010-chainlit-ui.md) and [0021](0021-chainlit-adapter-ouroboros-loop.md) are superseded **for the window**. The adapter-not-second-Analyst rule stays; the shell is Streamlit.
- [0017](0017-next-cycle-is-public-demo.md) “Streamlit out” and “Forecast charts do not block DNS” are superseded for this Demo. Postgres and chat-edited Route lists stay out.
- README names Streamlit as Chat UI, Ouroboros as the loop, `/evolve` off ([0024](0024-readme-names-ouroboros-evolve-off.md) still holds except “Chainlit adapter”).
- Chart implementation needs history and method **paths** for Brent. Urals is out of this Dashboard cut.
