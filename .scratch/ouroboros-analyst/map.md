# Map: Ouroboros Analyst

Label: wayfinder:map

## Destination

A spec the implementer can execute: the reviewer talks to an Analyst that **is** an Ouroboros agent — it chooses tool order and when to stop — with no **live-model** stubs that fake citations or Competence (infra safety nets allowed); the original assignment still holds for role, Reports, Web sources, Forecast, citations, UI, and one-command run, except where later tickets on this map explicitly change them.

## Notes

- Domain: oil-and-gas Analyst. Read `CONTEXT.md`, `docs/adr/`, `task.md`, and `.scratch/oil-gas-analyst/spec.md` before choosing a ticket. Use glossary terms (Analyst, Report, Sample Report, Web source, Forecast, Competence). “Agent” and Ouroboros are in-scope for this rebuild ([0019](../../docs/adr/0019-model-decides-the-loop.md)).
- Trigger: acceptance comments (pipeline is not an agent; Ouroboros was not waived; stubs such as citation patching and an out-of-scope dictionary). Ouroboros: https://github.com/razzant/ouroboros
- Skills: `/grilling` and `/domain-modeling` on every HITL ticket. Research tickets: `/research` subagent, findings on `research/<name>`.
- Plan, don’t build. This map ends when the spec (or an equivalent locked decision set) is ready to hand off — not when the rebuild ships.
- ADR 0001 (Analyst lives inside Ouroboros) was superseded by ADR 0002; the customer has now reversed that. Do not silently keep ADR 0002.
- v1 closed Route lists and the fixed LangGraph waterfall (classify → retrieve → drop → tools → compose) are the artefact under review, not sacred.

## Decisions so far

- [Chainlit talks to Ouroboros](issues/09-chainlit-talks-to-ouroboros.md) — compose publishes Chainlit `:8000`; the turn is `POST /api/tasks` on current-generation Ouroboros (Main GLM 5.2 free, thinking off, `light` / evolve off). LangGraph is not the conversation path.
- [Which trust surfaces the grader sees](issues/07-which-trust-surfaces-the-grader-sees.md) — README must name Ouroboros, reviewed skills, Chainlit adapter, `/evolve` off; other Review surfaces stay off Eval. ADR [0024](../../docs/adr/0024-readme-names-ouroboros-evolve-off.md).
- [Which model fills the Main slot](issues/08-which-model-fills-the-main-slot.md) — Main is OpenRouter `z-ai/glm-5.2:free`, thinking off; Heavy/Eval/review may differ via `.env`, else Main; no silent Grok/DeepSeek fallback. ADR [0023](../../docs/adr/0023-main-openrouter-glm52-free.md).
- [Which stubs must die for acceptance](issues/06-which-stubs-must-die.md) — live-model citation patch, Competence dictionary, Drop-restore, heading-rank, and Route lists as gates die; infra timeout/500 nets may stay; denylist list, two Forecast methods, tag grammar, Sample Reports stay. ADR [0022](../../docs/adr/0022-live-stubs-die-infra-nets.md).
- [Where the reviewer talks to the Analyst](issues/04-where-the-reviewer-talks.md) — click Chainlit `localhost:8000`; Ouroboros is the loop behind it; `:8765` and the desktop app are not the acceptance window; prove Ouroboros in the repo. ADR [0021](../../docs/adr/0021-chainlit-adapter-ouroboros-loop.md).
- [How Ouroboros can host the Analyst](issues/01-how-ouroboros-hosts-the-analyst.md) — reviewer talks to current-generation Ouroboros (desktop, `:8765` web, or CLI); the solve model picks tools and stop; domain body is reviewed extension tools plus `identity.md` and an instruction skill — not a LangGraph import, not a silent judge, not `BIBLE.md`. Stock web has no denylist. Detail: [ouroboros-host](research/ouroboros-host.md).
- [How the TZ waterfall lives inside an agent loop](issues/05-waterfall-inside-the-agent-loop.md) — extra Web next to a Report is fine even without “today”; `[Отчёт …]` must be grounded in retrieve this turn; paragraph order is not graded. ADR [0020](../../docs/adr/0020-waterfall-grounded-citations.md).
- [What the agent must decide each turn](issues/03-what-the-agent-must-decide.md) — model decides Competence, retrieve, Drop, Web, Forecast, stop, and order; host does not refuse calls. Answer must refuse out-of-scope, tag Forecast if used, not cite denylist, and include `[Отчёт …]` when the corpus covers the question. ADR [0019](../../docs/adr/0019-model-decides-the-loop.md).
- [Inventory of stubs versus product contracts](issues/02-stubs-versus-product-contracts.md) — citation patch, out-of-scope dictionary, Drop-restore, heading-rank, and classify/Drop fail-opens are stubs; denylist, k=10, citation grammar, Forecast module, and Competence-as-classify are contracts; Route lists and the fixed waterfall are mixed. Detail: [stubs-versus-contracts](research/stubs-versus-contracts.md).

## Not yet specified

- Exact README paragraph wording (identity.md vs instruction-skill playbook copy) — implementer follows [01](issues/01-how-ouroboros-hosts-the-analyst.md) and [0024](../../docs/adr/0024-readme-names-ouroboros-evolve-off.md).
- Whether compose publishes only `:8000` and keeps the Ouroboros gateway internal ([0021](../../docs/adr/0021-chainlit-adapter-ouroboros-loop.md) chose the click target).

Spec for implementation: [spec.md](spec.md) (`ready-for-agent`).

## Out of scope

- Executing the rebuild inside this map (implementation is a later handoff).
- Expanding Competence beyond oil and gas.
- Adding IEA, an Urals price series, Prophet, or LSTM unless a later ticket puts them back in.
- Replacing the Yellow-press denylist with an allowlist or an LLM journalism classifier (not raised by the customer).
