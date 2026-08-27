---
name: oil_gas_topics
description: Reddit oil-topic overview (30-day comment volume, Russian labels).
version: 0.1.0
type: extension
runtime: python3
entry: plugin.py
permissions: [tool]
when_to_use: >
  The user asks which oil narratives, Reddit themes, or discussion topics
  are rising or falling. Not for prices, Forecasts, or report figures.
timeout_sec: 30
---

# Reddit oil topics

Call this tool for a **narrative overview** of oil-related Reddit discussion over the last 30 Moscow days.

The tool returns topic labels, whether comment volume rose or fell, and 2–3 post titles per topic.
Copy labels verbatim. Do **not** invent extra topics or oil prices from this tool.
This is not a price series and not a substitute for Reports or `run_forecast`.
If the cache is empty, say you are uncertain.
