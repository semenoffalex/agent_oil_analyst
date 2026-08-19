# 04 — Layout C around chat

**What to build:** The Demo page matches prototype variant **C**: a top KPI row (Brent last close, SARIMA 21d, Holt–Winters 21d as two numbers, Report corpus titles/dates), Session-start Web on the left, Forecast chart stacked over chat on the right. Chat stays the conversation, not a second product. The chart is Brent actuals plus two method paths (from ticket 01), never averaged, never Urals. Last history close is the Live quote on that chart. A user request to refresh replaces the chart; there is no poll. Report strip is corpus metadata, not a second retrieve.

Prototype structure (throwaway HTML, variant C): KPI row; news column; chart-over-chat. A and B are rejected.

**Blocked by:** 01 — Forecast plot payload; 02 — Streamlit is the Chat UI; 03 — Session-start Web on the rail

**Status:** ready-for-agent

- [ ] Layout C is visible: KPIs on top, Session-start Web left, chart over chat on the right.
- [ ] Chart shows Brent actuals and two Forecast series (no average, no Urals).
- [ ] KPI row shows close plus both 21d method points plus OPEC/EIA/CBR corpus titles and dates.
- [ ] Refresh on request replaces the chart; no polling ticker.
- [ ] History/Forecast failure on the chart is uncertainty, not a fake strip.
