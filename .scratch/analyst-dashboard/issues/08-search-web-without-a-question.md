# search_web without a question

Type: research
Status: resolved
Blocked by:

## Question

Can `search_for_tool` / `oil_gas_web` run with a **host-chosen** query at session start (no Ouroboros task)? What JSON comes back (`denied` flag, snippets, empty list)? What timeouts and DuckDuckGo-in-Docker failure modes already exist?

This is a fact ticket, not permission to do it ([Host Session-start Web versus the agent loop](05-host-start-web-versus-loop.md)).

Findings file: [research/session-start-search-web.md](../research/session-start-search-web.md).

## Answer

The host **can** call `search_for_tool(query)` with no Ouroboros task. Return is `{hits: [{citation, url, title, snippet, denied}], count, note}` with `[Источник: …, web]` labels; denylist URLs stay in the list and are flagged `denied`. DuckDuckGo failure → **empty list**, not an exception. Page fetch timeout 8s; skill path 60s. This does **not** authorize bypassing the loop — that is [Host Session-start Web versus the agent loop](05-host-start-web-versus-loop.md).
