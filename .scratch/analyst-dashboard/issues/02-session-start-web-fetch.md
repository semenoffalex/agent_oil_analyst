# Session-start Web fetch contract

Type: grilling
Status: resolved
Blocked by:

## Question

The host may call Web **once** when the Streamlit session opens, so the executive sees current oil-market context before the first question.

What is the contract for that fetch?

- **Query**: fixed string (e.g. OPEC output / Brent) vs a small closed list vs something the exec types.
- **Implementation**: host calls `search_web` / `search_for_tool` itself vs a silent Ouroboros turn with a canned prompt.
- **Display**: titles + outlets as Web sources vs snippets vs “news cards.”
- **Denylist**: show denied hits greyed / hidden / still listed but uncited ([0019](../../../docs/adr/0019-model-decides-the-loop.md) — host does not strip hits for the **model**; the Dashboard is a different reader).
- **Empty / timeout**: uncertainty copy, no invented headlines (same as empty Web in chat).
- **Reuse**: may the Analyst cite Session-start hits in a later turn without retrieve/Web **this turn**, or must those tags still be grounded in the turn’s tools ([0020](../../../docs/adr/0020-waterfall-grounded-citations.md))?

This is not a polling ticker (out of scope on the map).

## Comments

- Language locked RU; canned query locked to `нефть Brent OPEC+ цена добыча` (customer, 2026-08-19).

## Answer

- **Query**: one canned host string, Russian, executive does not type it: `нефть Brent OPEC+ цена добыча`. Passed as `search_for_tool(query)`. Not a list, not typed, not a model-chosen query.
- **Implementation**: host calls `search_for_tool` once at Streamlit session start — not a silent Ouroboros turn ([Host Session-start Web versus the agent loop](05-host-start-web-versus-loop.md)).
- **Display**: title, outlet, snippet for each shown hit.
- **Denylist (exec rail)**: do **not** show denied domains on the Dashboard. Inject into the Analyst only the rows the executive can see. Citing a denylist domain remains a prompt failure.
- **Empty / timeout**: uncertainty copy; no invented headlines.
- **Reuse / grounding**: the Analyst **may** use these hits in answers, including the first turn and follow-ups about the rail. For Eval, `[Источник: …, web]` on a Session-start URL is grounded in **this session’s** fetch, not only `search_web` inside the current Ouroboros task. New facts not on the rail still need retrieve/Web **this turn** ([0020](../../../docs/adr/0020-waterfall-grounded-citations.md) narrowed for Session-start Web only).
