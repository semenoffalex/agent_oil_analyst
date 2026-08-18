# 0019. The model decides the loop; the answer is graded

## Status

Accepted

## Context

Acceptance rejected the v1 LangGraph waterfall: a deterministic pipeline is not an Analyst. The customer chose that **the model** picks tools and when to stop. Host gates (Route lists, classify-then-block-tools, always-retrieve) were the artefact under review.

This **contradicts** [0004](0004-forecast-only-on-explicit-verbs.md) (Forecast only on a verb), [0005](0005-closed-route-lists.md) (lists decide Forecast vs web), [0008](0008-duckduckgo-denylist.md) as a **host drop** of denylist URLs, [0012](0012-always-retrieve-model-drops.md) (always retrieve k), [0013](0013-web-if-dropped-and-in-competence.md) / [0014](0014-competence-classify-node.md) (classify `out` stops tools), and the Eval pass rules in [0017](0017-next-cycle-is-public-demo.md) that assert tool flags.

## Decision

On every turn the **solve model** decides: Competence, whether to retrieve Reports, whether to Drop, whether to search the Web, whether to run Forecast, when to stop, and in what order. The host **must not** refuse those calls.

Acceptance grades the **visible answer** (and treats a bad tool trace as a **prompt** failure, not a missing runtime lock):

- Out-of-competence (weather, Python, …): refuse; no invented figures. If the model still searched the Web, the prompt failed — do not add a host block to “fix” it.
- Forecast: no verb required. If the module ran, tag `[Forecast …]`. A number that did not come from Reports, Web sources, or Forecast is a fail.
- Yellow-press domains: must not appear as citations. The host does **not** strip them from search hits before the model sees them.
- If the Report corpus supports the question, the answer **must** contain an `[Отчёт …]` citation grounded in retrieve **this turn** ([0020](0020-waterfall-grounded-citations.md)). Web-only on a corpus-covered demand outlook fails, even with honest web tags. Extra Web **with** a grounded Report tag is fine, including on quiet demand questions. Prose order is not graded.

Tool-level honesty stays (Forecast still has no Urals series; do not invent one). That is the calculator, not a loop gate.

## Consequences

- Route lists and a classify node that blocks tools are not acceptance detectors. Route lists may exist only as prompt/skill hints ([0022](0022-live-stubs-die-infra-nets.md)).
- [0008](0008-duckduckgo-denylist.md): the **list** remains a product contract; applying it as a host filter is no longer required.
- Live Eval / red-team in [0017](0017-next-cycle-is-public-demo.md) that pass on “no tools” / “Forecast ran because of a verb” must be rewritten around answer citations, retrieve-grounding for `[Отчёт …]`, and prompt failures ([0020](0020-waterfall-grounded-citations.md)).
