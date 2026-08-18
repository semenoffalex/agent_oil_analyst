# Which trust surfaces the grader sees

Type: grilling
Status: resolved
Blocked by: 04

## Question

Inherited from [Where the reviewer talks to the Analyst](04-where-the-reviewer-talks.md) / [0021](../../../docs/adr/0021-chainlit-adapter-ouroboros-loop.md): the grader **clicks Chainlit `:8000`**, not Ouroboros Skills/Dashboard. Ouroboros is proven **in the repo**. `:8765` may run internally.

Still open: which Ouroboros trust surfaces must be **named or linked in README** (even if the grader never opens them), and which stay off the Eval path?

[How Ouroboros can host the Analyst](01-how-ouroboros-hosts-the-analyst.md) splits several “Review” things:

- Skills-page review (trust gate before domain tools run).
- Task-acceptance Review (post-delivery coach; skips ordinary read-only chat).
- P3 commit Review (only if Ouroboros mutates its own repo).
- `/review` (constitutional self-review, not a grade of the oil question).
- `/evolve` (self-mod; hard-blocked in `runtime_mode=light`).

Which of these **must appear** in the demo / README so the grader believes this is Ouroboros, not a LangGraph clone? Which stay **off** the Eval path?

Facts, not a decision: `light` still runs reviewed skills and blocks evolve; Dashboard Logs already show tool/LLM cards; a domain-tool-only demo never shows commit Review unless someone opens Evolution.

## Answer

README **must** name Ouroboros as the runtime, domain tools as reviewed skills in the repo, Chainlit as the adapter, and `/evolve` off (`light`) for the Demo. The grader still clicks only `:8000`.

Task-acceptance Review, P3, and `/review` stay **out** of README and **off** the five Eval dialogues.

ADR: [0024](../../../docs/adr/0024-readme-names-ouroboros-evolve-off.md).

## Comments

- Customer: README is obliged to mention (not “code only”).
- Minimum set, not a catalogue of all five Review surfaces. Evolve off at runtime.
