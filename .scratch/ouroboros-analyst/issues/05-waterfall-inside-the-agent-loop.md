# How the TZ waterfall lives inside an agent loop

Type: grilling
Status: resolved

## Question

Inherited from [What the agent must decide each turn](03-what-the-agent-must-decide.md) / [0019](../../../docs/adr/0019-model-decides-the-loop.md): **hard tool policy is out.** The model may skip retrieve, search, or Forecast in any order. Forecast without a verb is allowed. Out-of-competence extra Web is a prompt fail, not a host block.

Still required in the **answer**: `[Отчёт …]` when the corpus covers the question.

The assignment still says: search Reports first; use them as the main source when they suffice; use the Web as a supplement or for freshness.

Remaining choice — how strong is that waterfall as **prompt policy**?

1. Quiet demand-outlook (no “today”): Web in the answer is **fail** unless the Report citation is also there? Or Web alongside Reports is **fine** (combined demo)?
2. May the Analyst skip retrieve entirely if it still produces a correct `[Отчёт …]` from memory — or must the citation be grounded in a tool result this turn?
3. Anything else the prompt must insist on (Reports before Web in the prose, not only in the tag set)?

## Answer

The TZ waterfall is prompt policy + Eval on **grounded citations**, not a host graph and not paragraph order ([0020](../../../docs/adr/0020-waterfall-grounded-citations.md)).

- Quiet demand outlook: Web **beside** a Report tag is fine (combined answer does not need “today”).
- `[Отчёт …]` without retrieve **this turn** fails, even if the figure matches a Sample Report.
- Corpus-covered question: retrieve this turn **and** cite that result. Host still does not force the call; skip-and-fake and skip-and-omit both fail as prompt failures.
- Prose may lead with Web; tags and grounding are what Eval scores.

## Comments

- Quiet demand + Reuters + MOMR: pass if `[Отчёт …]` is present.
- `[Отчёт …]` from memory, no RAG this turn: fail.
- Reuters first, then MOMR, both tagged, retrieve ran: pass.

