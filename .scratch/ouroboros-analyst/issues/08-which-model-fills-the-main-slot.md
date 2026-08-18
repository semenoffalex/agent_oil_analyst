# Which model fills the Main slot

Type: grilling
Status: resolved

## Question

v1 locked chat to `deepseek-v4-flash` with thinking off (ADR 0006). Ouroboros does not have a DeepSeek product: Main / Heavy / Light are **model slots** in `settings.json` / process env (OpenRouter, OpenAI-compatible base URL, GigaChat, local GGUF). Default Main on stock Ouroboros is OpenRouter `x-ai/grok-4.5`. A DeepSeek-only Analyst would be a **pin** of the Main slot to an OpenAI-compatible DeepSeek endpoint, not a built-in.

TZ allows any LLM if README says why. Keep DeepSeek Flash as Main? Switch to Ouroboros’s default (or another slot)? Must thinking stay off? Is a second model for skill-review / Heavy allowed, or is one vendor still the product rule?

## Answer

Main is OpenRouter **`z-ai/glm-5.2:free`**, thinking **off**. Heavy / skill-review / live Eval **may** be other `.env` ids; unset → Main. No silent fallback to Grok or DeepSeek. README must say why this pin.

ADR: [0023](../../../docs/adr/0023-main-openrouter-glm52-free.md).

## Comments

- Not Flash, not stock Grok: customer named `z-ai/glm-5.2:free`.
- Thinking off (same product rule as v1 Flash).
- Other slots optional via env; default same slug.
