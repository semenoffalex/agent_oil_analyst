# 0023. Main chat is OpenRouter GLM 5.2 free, thinking off

## Status

Accepted

## Context

The assignment allows any LLM if README says why. v1 pinned [0006](0006-deepseek-chat-llm.md) `deepseek-v4-flash` with thinking off. Ouroboros Main is a **slot** (OpenRouter, OpenAI-compatible, GigaChat, GGUF); stock default is OpenRouter `x-ai/grok-4.5`. The customer chose a third pin: OpenRouter `z-ai/glm-5.2:free`. GLM thinking defaults toward on/max; v1 had required thinking off so demos do not wait on a chain-of-thought.

Live Eval was a **different** free OpenRouter slug while product stayed DeepSeek ([0018](0018-eval-chat-openrouter-free.md)). Product is now itself a `:free` OpenRouter id.

## Decision

**Main** (Chainlit `:8000` / Ouroboros solve model) is `z-ai/glm-5.2:free` via OpenRouter. Thinking is **off** on every Main call. README states this pin and why (customer choice; TZ allows any LLM).

**Heavy, skill-review, and live Eval** may use **other** ids from `.env`. If those vars are unset, they use the same Main slug — not Grok, not DeepSeek. Missing OpenRouter credentials or a dead `:free` id is a loud failure, not a silent vendor fallback.

## Consequences

- [0006](0006-deepseek-chat-llm.md) is superseded for the Ouroboros rebuild. `DEEPSEEK_API_KEY` is not the product chat key.
- [0018](0018-eval-chat-openrouter-free.md): Eval remains OpenRouter-from-env; it is no longer “DeepSeek in Docker, OpenRouter only in Eval.” Default Eval model is Main unless `EVAL_CHAT_MODEL` is set.
- `:free` rate limits and outages are OpenRouter’s. That is an accepted Demo risk; do not silently swap in a paid GLM or Grok.
- Ouroboros must be configured with OpenRouter base URL + key and an explicit thinking-disabled extra body (or equivalent) on Main.
