# 0024. README names Ouroboros; evolve stays off Eval

## Status

Accepted

## Context

The reviewer clicks Chainlit `:8000` and verifies Ouroboros in the repo ([0021](0021-chainlit-adapter-ouroboros-loop.md)). Ouroboros still has Skills review, task-acceptance Review, P3 commit Review, `/review`, and `/evolve`. The customer required the README to **mention** the harness so a grader does not mistake Chainlit+LangGraph, without opening `:8765`.

## Decision

README **must** state, in short:

- the conversation runtime is **Ouroboros** (not LangGraph);
- domain Report / denylist-web / Forecast tools are **reviewed skills** in this repo;
- Chainlit is an **adapter**;
- **`/evolve` is off** for the Demo (`runtime_mode=light`).

Task-acceptance Review, P3 commit Review, and `/review` are **not** required in README and **must not** run on the five Eval dialogues. The grader is not required to open Ouroboros Skills or Dashboard.

## Consequences

- A README that only documents Chainlit + DeepSeek/LangGraph fails this rebuild even if Ouroboros is in git.
- Eval must start Ouroboros in `light` (or equivalent) so evolve cannot rewrite the Analyst mid-demo.
- Linking `:8765` in README is optional; it is not the click target ([0021](0021-chainlit-adapter-ouroboros-loop.md)).
