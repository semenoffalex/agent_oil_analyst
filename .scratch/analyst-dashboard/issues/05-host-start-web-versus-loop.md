# Host Session-start Web versus the agent loop

Type: grilling
Status: resolved
Blocked by: 02, 03

## Question

[0019](../../../docs/adr/0019-model-decides-the-loop.md): the model decides Web in the loop; the host does not refuse tools. A Session-start fetch is a **host** Web call with no user question.

Is that allowed as a Dashboard exception (context rail only, not a hidden Analyst turn), or must even the opening headlines go through Ouroboros so the model “chose” Web?

If the host fetches: may those hits enter the next turn’s prompt automatically (so the exec’s first question is already grounded), or must the rail stay **display-only** until the model calls `search_web` itself?

Facts: [Session-start Web fetch contract](02-session-start-web-fetch.md), [Streamlit is the click target](03-streamlit-click-target.md), [search_web without a question](08-search-web-without-a-question.md).

## Answer

**Dashboard exception:** the host fetches Session-start Web (no canned Ouroboros turn). That is not a second Analyst.

Hits on the rail are **injected into later turns’ prompt**, so follow-up questions about the headlines are in-competence and grounded in the session fetch. The rail is not display-only. The model may still call `search_web` in the loop for anything not on the rail. The host still does not refuse tools ([0019](../../../docs/adr/0019-model-decides-the-loop.md)).
