# 0027. Main chat is DeepSeek V4 Flash via DeepSeek API, thinking off

## Status

Accepted

## Context

[0023](0023-main-openrouter-glm52-free.md) pinned Main to OpenRouter `z-ai/glm-5.2:free`. Benchmarks showed DeepSeek direct API (~1.3 s TtFT) is faster than the same family through OpenRouter (~4 s). The customer wants Main back on `deepseek-v4-flash` at `https://api.deepseek.com` with thinking off ([0006](0006-deepseek-chat-llm.md)).

Ouroboros routes prefixed models through provider lanes. DeepSeek is not a built-in provider; the product uses the **openai-compatible** lane: `openai-compatible::deepseek-v4-flash` with `OPENAI_COMPATIBLE_BASE_URL` + `OPENAI_COMPATIBLE_API_KEY` (mapped from `DEEPSEEK_BASE_URL` / `DEEPSEEK_API_KEY`). The Ouroboros container must **not** receive `OPENROUTER_API_KEY`, or provider detection prefers OpenRouter for chat.

Embeddings stay on OpenRouter Nemotron ([0025](0025-openrouter-embeddings-no-local-torch.md)); the analyst service still needs `OPENROUTER_API_KEY` (or `EMBEDDING_API_KEY`).

## Decision

**Main** (Streamlit `:8000` / Ouroboros solve model) is `deepseek-v4-flash` via DeepSeek API. Ouroboros model id: `openai-compatible::deepseek-v4-flash`. Thinking is **off** (`OUROBOROS_RETURN_REASONING=false`).

**Heavy, skill-review, and live Eval** may use other ids from `.env`. Unset → Main. No silent fallback to OpenRouter GLM or Grok.

Missing `DEEPSEEK_API_KEY` or a dead DeepSeek endpoint is a loud failure, not a silent vendor swap.

## Consequences

- [0023](0023-main-openrouter-glm52-free.md) is superseded for chat.
- [0006](0006-deepseek-chat-llm.md) is reinstated for the product path, with Ouroboros `openai-compatible::` routing.
- Compose splits keys: `DEEPSEEK_API_KEY` → `ouroboros`; `OPENROUTER_API_KEY` → `analyst` (embeddings) and ingest.
- Demo cost is DeepSeek usage pricing, not OpenRouter `:free` queue risk for chat.
