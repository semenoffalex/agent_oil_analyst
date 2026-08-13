# 0013. Web after all chunks Dropped only if still in Competence

## Status

Accepted

## Context

[0012](0012-always-retrieve-model-drops.md) removed the Thin web trigger. Time-sensitive Route lists still open the web. That left a hole: all chunks Dropped, no freshness word — refuse, search, or let the model decide.

An unconstrained web call after Drop ([0012](0012-always-retrieve-model-drops.md) option B in grilling) leaks out-of-scope questions onto DuckDuckGo. A planner that may search whenever it wants was already rejected.

## Decision

If every Retrieved chunk is Dropped:

- **In Competence** → one DuckDuckGo call, then answer from Web sources (denylist still applies).
- **Out of Competence** → refuse. No web, no Forecast, no citations from Dropped chunks.

Time-sensitive questions still open the web only when they are in Competence. “What’s the weather today?” is Time-sensitive and Out of Competence: refuse.

Competence detection and the out-of-competence short-circuit are in [0014](0014-competence-classify-node.md).

## Consequences

- The “Reports missed, use web” demo must be in-competence and must Drop all five oil chunks (e.g. a gas-pipeline question with no overlap with MOMR/STEO samples) **or** wait until Full Reports are ingested.
- The “out of competence” demo must not hit DuckDuckGo.
