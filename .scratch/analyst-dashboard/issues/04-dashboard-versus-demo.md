# Dashboard versus Demo and Eval

Type: grilling
Status: resolved
Blocked by:

## Question

The Ouroboros rebuild Demo is a public-or-local **Chat UI** for a **reviewer**, no password, rate limit ([0017](../../../docs/adr/0017-next-cycle-is-public-demo.md)). This Dashboard is for a **senior bank executive**.

Are they the **same screen**, or two products?

- If **same**: do the five README dialogues still Eval on Streamlit? Does “no password” still hold for a bank exec? Rate limit vs bank SSO?
- If **two**: which is `localhost:8000`? Does the executive Dashboard ship without assignment Eval? What must not leak (keys, Full Reports, internal notes)?

Competence, denylist, Forecast module, and grounded `[Отчёт …]` either stay or this ticket must say what is waived for the exec screen.

## Answer

The Dashboard **is** the Demo: an **expanded** Demo for a senior bank executive, not a second product. `localhost:8000` is that Streamlit page. Five README dialogues still Eval on this screen. No password; Demo rate limit stays (no bank SSO in this map). Competence, denylist-in-answers, Forecast module, and `[Отчёт …]` grounding stay; Session-start Web grounding is the exception in [Session-start Web fetch contract](02-session-start-web-fetch.md).
