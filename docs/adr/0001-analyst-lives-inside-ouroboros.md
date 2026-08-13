# 0001. Analyst lives inside Ouroboros

## Status

Superseded by [0002](0002-ouroboros-out-of-scope.md)

## Context

The product is a senior oil-and-gas market Analyst. The assignment also requires using razzant/ouroboros. Ouroboros is a full harness with its own UI, identity, and blocking Review — not a library to import into LangGraph.

Alternatives considered:

- Treat Ouroboros as a build-time generator of a LangGraph app.
- Keep LangGraph as the user-facing app and use Ouroboros as a sidecar judge of chat strings.
- Write each answer as a workspace artifact and run Ouroboros’s commit Review on that file.
- Imitate Review with a LangGraph critique node and keep the real harness off the demo path.

Those either hide Ouroboros from the user, or use it as an expensive judge instead of its actual Review pipeline.

## Decision

The user talks to Ouroboros. The Analyst is a role of that instance. RAG, web search, and the price-forecast module are tools or skills that instance calls. Native Review is the runtime self-check.

## Consequences

- There is one user-facing conversation surface: Ouroboros (desktop, CLI, or headless — install flavor not yet chosen).
- A separate Streamlit/Gradio Analyst app is not the product unless a later decision makes it a thin skin or a rubric adapter.
- LangGraph, if it remains, is a tool the Analyst calls, not the thing the user talks to.
- Self-development (`/evolve`) is still an open decision: the same instance can rewrite itself while answering market questions unless that is later forbidden.
