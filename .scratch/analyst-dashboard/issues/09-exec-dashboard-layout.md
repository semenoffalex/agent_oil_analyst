# Exec Dashboard layout

Type: prototype
Status: resolved
Blocked by:

## Question

Given the block set and whether this screen is Demo or exec-only, **how should the page look** so chat stays visually central and context (Session-start Web, and any other agreed blocks) reads as framing — not a second product?

Throwaway Streamlit or HTML variants via `/prototype` (UI branch). Not production. Verdict belongs in the Answer; pixels are the asset.

## Comments

- Prototype (Brent only, no Urals): [prototype/dashboard.html](../prototype/dashboard.html) — open in a browser. `?variant=A` лента сверху, `B` чат-театр, `C` брифинг KPI. Bar / ← →. Fake data. Ticket stays open until a variant is chosen.

## Answer

**C — Брифинг KPI.** Top row: Brent close + SARIMA 21d + Holt–Winters 21d (two numbers, never averaged) + Report corpus. Below: Session-start Web on the left; Forecast chart stacked over chat on the right. Chat stays the conversation, not a second product. Throwaway: [prototype/dashboard.html](../prototype/dashboard.html)?variant=C. A and B stay in that file as rejected structure, not production.
