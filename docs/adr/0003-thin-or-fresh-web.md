# 0003. Web only on thin retrieval or time-sensitive questions

## Status

Partially superseded: the Thin trigger is replaced by [0012](0012-always-retrieve-model-drops.md). The Time-sensitive web trigger still stands.

## Context

The spec says: search Reports first; if they are enough, use them; use the web as a supplement or when freshness is required; mark origin in the answer.

“Enough” was undefined. Alternatives:

- Answer from Reports whenever any chunk clears a score threshold (stale but cited).
- Always retrieve Reports and the web; Reports win conflicts.
- Let a LangGraph planner pick tools per turn (report-first is not guaranteed).

## Decision

Reports first. The Analyst calls Web sources only when retrieval is Thin or the question is Time-sensitive. Otherwise the answer stays on Reports.

How Thin is measured, and how Time-sensitive is detected, are still open. Price questions are overloaded: a Live quote is Time-sensitive; a Forecast is a different tool.

## Consequences

- The graph is a waterfall, not “always search” and not an unconstrained planner.
- Demo scripts must include one thin-corpus question and one Time-sensitive question or the web path will not show up.
- A bare “what’s Brent?” is still ambiguous until Live quote vs Forecast is decided.
