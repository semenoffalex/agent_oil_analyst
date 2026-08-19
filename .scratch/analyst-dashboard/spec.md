Status: ready-for-agent

# Spec: Analyst Dashboard (Streamlit Demo)

Map: [map.md](map.md). Decisions live in the tickets; this file is the implementer handoff.

## Problem Statement

The reviewer Demo is still one browser URL after one compose command, still an adapter over the Ouroboros Analyst loop, still the five README Eval dialogues. The window must become a **Dashboard** for a **senior bank executive**: chat in the centre, framed by current oil-market context (Session-start Web, Brent actuals + 21-day Forecast, Report corpus dates). Chainlit is not that window. Competence does not grow. Invented prices stay forbidden. Urals is not on the chart until a real series exists.

## Solution

Replace Chainlit with Streamlit on `http://localhost:8000`. The Analyst turn is unchanged: `build_loop` → `run_turn` → `POST /api/tasks`. At Streamlit session start the **host** (not a silent Ouroboros task) calls `search_for_tool` once and draws a Brent chart (history + two method paths). Layout is prototype variant **C**. Five README dialogues Eval on this page. No password; Demo rate limit stays.

## User Stories

1. As a reviewer, I copy `.env.example` to `.env`, set the OpenRouter key, and run one compose command, so that Streamlit is on port 8000.
2. As a reviewer, I open `http://localhost:8000` and see the Dashboard, so that I do not use Chainlit or `:8765` for acceptance.
3. As a bank executive, I see Session-start Web, KPI figures, a Brent chart, Report corpus dates, and chat in one page (layout C), so that context frames the conversation and is not a second product.
4. As a bank executive, I do not type a search query; the host searches once with `нефть Brent OPEC+ цена добыча`, so that the rail is current oil-market context.
5. As a bank executive, I see title, outlet, and snippet for each shown hit, so that I can scan the rail.
6. As a bank executive, I do not see Yellow-press denylist domains on the rail, so that the Dashboard reader is not shown what we refuse to cite.
7. As a reviewer, I still fail a denylist **citation** in chat as a prompt failure; the host does not strip hits from the model’s search tool in the loop ([0019](../../docs/adr/0019-model-decides-the-loop.md)). Session-start injects into the Analyst only the rows the executive can see.
8. As a bank executive, if DuckDuckGo fails or returns nothing, I see uncertainty copy and no invented headlines.
9. As a user, I ask about a headline on the rail, so that the Analyst may answer from this session’s fetch without `search_web` this turn; `[Источник: …, web]` on those URLs is grounded for Eval in **this session’s** fetch ([0020](../../docs/adr/0020-waterfall-grounded-citations.md) narrowed for Session-start Web only).
10. As a user, I ask a fact that is not on the rail, so that retrieve/Web/Forecast this turn still apply as in the Ouroboros Analyst spec.
11. As a bank executive, on open I see actual Brent closes plus a 21 trading-day Forecast (SARIMA and Holt–Winters as two series, never averaged), so that I do not wait for a Forecast verb.
12. As a bank executive, the last history close on that chart is the Live quote; I do not need a second mystery tape.
13. As a bank executive, I ask to refresh the chart, so that the host recomputes and replaces it; there is no poll.
14. As a user, I ask for Urals Forecast in chat, so that the module still says there is no series and does not proxy Brent; the Dashboard chart stays Brent-only.
15. As a bank executive, I see OPEC / EIA / CBR titles and dates from Sample/Full Reports on the page, so that the corpus is visible without a second retrieve.
16. As a reviewer, I replay the five README dialogues on Streamlit, so that Eval did not move to a second screen.
17. As a reviewer, I have no password; Demo rate limit still applies.
18. As a reviewer, I prove Ouroboros in the repo (adapter wiring, skills, identity, compose), not by opening the `:8765` SPA.
19. As a user, I still get Safety nets only on timeout / 500 / empty completion, so that a live model reply is not host-patched.

## Implementation Decisions

- **Chat UI** is Streamlit on `:8000`. Chainlit is not in the Demo image. Compose `CMD` for the analyst service becomes Streamlit; do not run two UIs. Seam: [streamlit-ouroboros-adapter](research/streamlit-ouroboros-adapter.md). ADR [0026](../../docs/adr/0026-streamlit-dashboard-is-the-demo.md).
- Layout **C**: top KPI row (Brent close + SARIMA 21d + Holt–Winters 21d as two numbers + Report corpus); below, Session-start Web left; Forecast chart stacked over chat on the right. Pixels: [prototype/dashboard.html](prototype/dashboard.html)?variant=C. A and B are rejected structure.
- Session-start Web: host `search_for_tool("нефть Brent OPEC+ цена добыча")` once per Streamlit session. Not a canned Ouroboros turn. Inject visible hits into later `run_turn` prompts. Loop `search_web` remains allowed. Facts: [session-start-search-web](research/session-start-search-web.md).
- Chart: host may load Brent history and run the Forecast module at session start without a user Forecast request. Today `forecast_for_tool` is last-horizon scalars only — expose history + per-step SARIMA and Holt–Winters paths for Brent (21 trading days). Yahoo/loader fail → uncertainty, no fake CSV. Detail: [forecast-plot-payload](research/forecast-plot-payload.md). Ticket [10](issues/10-history-without-forecast-request.md) once said Brent and Urals; [11](issues/11-where-urals-series-comes-from.md) **supersedes** that for the chart: Brent only.
- Product rules from [ouroboros-analyst/spec.md](../ouroboros-analyst/spec.md) stay except the Chat UI shell and the Session-start Web grounding exception. `/evolve` stays off. Main remains OpenRouter `z-ai/glm-5.2:free` unless `.env` overrides.

## Testing Decisions

- Frozen pytest still targets the Analyst-turn seam (`question → reply`), not Streamlit widgets.
- Live Eval of the five README dialogues runs against Streamlit `:8000`, not Chainlit.
- Session-start: empty DDG → uncertainty copy, no invented rail headlines. Denied domains absent from the rail. Chat may cite a Session-start URL shown on the rail without `search_web` in that Ouroboros task.
- Chart: two method series visible, not one averaged line; Urals not drawn.

## Out of Scope

- IEA corpus, Urals series on the Dashboard, Prophet/LSTM, allowlist journalism classifier.
- A second Analyst or LangGraph as the conversation path.
- Turning `/evolve` on.
- A live rolling news ticker.
- Bank SSO / password.
- P&L or a second chatbot.
- Implementing inside the wayfinder map (this spec is the handoff).
