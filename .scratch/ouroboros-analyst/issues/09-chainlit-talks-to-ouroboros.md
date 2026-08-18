# 09 — Chainlit talks to Ouroboros

**What to build:** After one Docker/compose command and an OpenRouter key in `.env`, the reviewer opens Chainlit at port 8000 and chats with an Ouroboros agent loop (Main `z-ai/glm-5.2:free`, thinking off, `/evolve` off). README names Ouroboros as the runtime, Chainlit as the adapter, and evolve off. A missing key fails loudly (no silent DeepSeek/Grok). The LangGraph waterfall is not the conversation path. Answers need not yet cite Reports or run Forecast.

**Blocked by:** None — can start immediately.

**Status:** resolved

- [x] One command brings Chainlit on port 8000; the turn runs in current-generation Ouroboros, not the old classify→retrieve→compose graph.
- [x] Main is OpenRouter `z-ai/glm-5.2:free` with thinking off; unset Heavy/Eval/review use Main; no silent vendor fallback.
- [x] `/evolve` is off for this Demo path; task-acceptance Review, P3, and `/review` do not run on ordinary chat.
- [x] README states Ouroboros runtime, reviewed skills (even if tools land later), Chainlit adapter, evolve off; demo URL is port 8000, not the Ouroboros SPA.
- [x] Analyst-turn tests that locked host tool gates are replaced or dropped so CI is green against the new seam (`question → reply`).
- [x] Secrets and model ids live only in `.env` / `.env.example`.

## Answer

Chainlit on `:8000` is an adapter: `run_turn(question, loop)` posts to the Ouroboros gateway (`POST /api/tasks`). Compose starts Ouroboros internally (not published) with Main `z-ai/glm-5.2:free`, `OUROBOROS_EFFORT_TASK=none`, `runtime_mode=light`, task review off. Missing `OPENROUTER_API_KEY` fails at entrypoint and at `build_loop`. LangGraph is no longer the conversation path. Report/Web/Forecast extension tools remain tickets 10–12.
