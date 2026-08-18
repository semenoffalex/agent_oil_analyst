---
name: oil_gas_web
description: Search the open Web (DuckDuckGo) for oil-and-gas freshness and live quotes.
version: 0.1.0
type: extension
runtime: python3
entry: plugin.py
permissions: [tool]
when_to_use: >
  The user asks for a latest statement, live quote, or other in-Competence fact
  that Reports may not have yet. Extra Web beside a grounded Report is allowed.
timeout_sec: 60
---

# Web search

Call this tool when freshness or a live quote matters, or when Reports do not cover the claim.
Copy `[Источник: …, web]` from returned `citation` fields.
Hits with `denied: true` (kp.ru, dailymail.co.uk, and the rest of the Yellow-press list) must not be cited.
Citing them is a prompt failure; the host will not strip those URLs from the hit list.
If `count` is 0, say you are uncertain. Do not invent news or prices.
Unlisted tabloids may still appear; cite them only if you use them.
