# 0002. Ouroboros is out of scope

## Status

Accepted

## Context

The assignment title asked where to use razzant/ouroboros. Questions 1–3 of the grilling session chose a runtime self-check with the Analyst living inside Ouroboros ([0001](0001-analyst-lives-inside-ouroboros.md)).

That topology fights the rest of the spec: LangChain/LangGraph, a shipped simple UI, and a one-command Docker run. The product owner then dropped Ouroboros as a condition and asked to build the Analyst as specified in the body of the task.

## Decision

Ouroboros is not a requirement, not a runtime, and not part of the demo path. The user talks to a LangGraph Analyst behind a simple UI we ship.

## Consequences

- ADR 0001 is superseded. Glossary terms Review-as-Ouroboros-gate and Analyst-as-Ouroboros-role are removed.
- Remaining choices are the assignment’s: models, vector store, web search, source waterfall, forecast methods, UI, Docker.
- Mentions of Ouroboros in `task.md`’s title are historical, not a build constraint.
