# 0006. DeepSeek V4 Flash is the chat model

## Status

Accepted (reinstated for Ouroboros rebuild via `openai-compatible::` lane; supersedes [0023](0023-main-openrouter-glm52-free.md)).

## Context

The assignment allows any LLM if the README says why. Candidates on the table were OpenAI GPT-4o, GigaChat, Claude, a local Ollama model, and the older DeepSeek `deepseek-chat` / `deepseek-reasoner` pair. The product owner chose `deepseek-v4-flash` via API key.

`deepseek-v4-flash` (DeepSeek-V4-Flash-0731) is OpenAI- and Anthropic-compatible, supports tool calls, JSON, and a 1M context window. It is a hybrid: thinking and non-thinking modes. DeepSeek’s default is thinking. `deepseek-v4-pro` was not chosen.

Embeddings are still open: this API id is a chat model.

## Decision

The Analyst’s chat LLM is `deepseek-v4-flash` at `https://api.deepseek.com`, authenticated with `DEEPSEEK_API_KEY`. One primary chat vendor. No silent fallback to OpenAI, GigaChat, or `deepseek-v4-pro`.

Thinking mode is **off** for every graph node (non-thinking only). We do not leave DeepSeek’s default on.

## Consequences

- Docker and README assume outbound HTTPS to DeepSeek, not a local GPU.
- `.env` / LangChain model name is `deepseek-v4-flash`, not `deepseek-chat`.
- The client must explicitly disable thinking; omitting the flag would silently turn it back on.
- Tool-calling quality, cache pricing, and rate limits are Flash’s, not Pro’s.
- Embeddings, web search, and the Forecast module can use other libraries; they must not sneak in a second chat LLM on the product path.
- Live **Eval** chat is a documented exception: [0018](0018-eval-chat-openrouter-free.md). Docker and Chainlit still call only DeepSeek.
