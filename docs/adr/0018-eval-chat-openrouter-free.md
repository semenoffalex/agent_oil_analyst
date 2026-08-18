# 0018. Live Eval chat uses a free OpenRouter model

## Status

Partially superseded: Eval is still an OpenRouter id from `.env` ([0023](0023-main-openrouter-glm52-free.md)). Product chat is no longer DeepSeek; default Eval is Main (`z-ai/glm-5.2:free`) unless `EVAL_CHAT_MODEL` is set.

## Context

The product chat vendor is DeepSeek ([0006](0006-deepseek-chat-llm.md)). Live **Eval** still needs a real classify / Drop / compose LLM, but burning DeepSeek on five dialogues plus retries is unnecessary. OpenRouter exposes a rotating pool of `:free` models (and `openrouter/free`).

Alternatives: keep Eval on DeepSeek; pin a paid OpenRouter model; let `openrouter/free` pick a different slug each call.

## Decision

Live Eval (`LIVE_EVAL=1`) talks to OpenRouter. Endpoint, key, and model id come from `.env`: `OPENROUTER_BASE_URL`, `OPENROUTER_API_KEY`, `EVAL_CHAT_MODEL`. The example file ships a `:free` slug; the code does not bake a model id. The running Analyst (Chainlit, Docker, Demo) stays on DeepSeek. There is no silent fallback from DeepSeek to OpenRouter in the product path.

## Consequences

- `.env.example` documents OpenRouter keys as Eval-only.
- `pytest -q` without `LIVE_EVAL` and `OPENROUTER_API_KEY` does not call OpenRouter.
- Free-model availability and rate limits (RPM / daily) are OpenRouter’s; a missing `:free` slug is an env change, not a vendor switch for the Analyst.
- Classify / Drop quality on the Eval model can be weaker than Flash; Eval still scores flags, not gold prose.
