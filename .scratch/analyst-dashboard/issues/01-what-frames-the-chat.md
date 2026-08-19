# What frames the chat for a bank executive

Type: grilling
Status: resolved
Blocked by:

## Question

Chat stays the **centre**. One Session-start Web fetch is already allowed. For a **senior bank executive**, which **other** existing product data become persistent blocks on the Dashboard (always visible, not only after a question)?

Options to accept, mix, or reject:

- A Live quote block (Yahoo/Web, labelled as quote not Forecast).
- A Forecast chart (history + SARIMA and Holt–Winters, never an average) always on screen vs only after a Forecast request.
- Report corpus headlines / last Sample Report dates (OPEC, EIA, CBR) — not a second retrieve.
- Nothing else: only chat + Session-start Web.

What must **not** appear (P&L, bank book, non-oil news, a second chatbot)?

This ticket picks the **set of blocks**, not pixel layout ([Exec Dashboard layout](09-exec-dashboard-layout.md)).

## Answer

All listed context blocks are in, always on the Dashboard (not only after a question):

- Session-start Web (titles, outlets, snippets — contract in [Session-start Web fetch contract](02-session-start-web-fetch.md)).
- Live quote (spot; not a Forecast).
- Forecast chart (history + two methods, never an average). Chart payload gap: [What Forecast already plots](06-what-forecast-already-plots.md) / [May the Dashboard load price history without a Forecast request](10-history-without-forecast-request.md).
- Report corpus strip: Sample/Full Report titles and dates for OPEC, EIA, CBR — not a second retrieve.

Chat stays the centre. No P&L, bank book, non-oil news, or second chatbot. Pixel layout is [Exec Dashboard layout](09-exec-dashboard-layout.md).
