# 0014. Competence is an LLM classify node

## Status

Accepted

## Context

[0013](0013-web-if-dropped-and-in-competence.md) requires an in/out Competence gate. Alternatives were a third keyword allow-list, a deny-list (everything not banned is in), or lists then LLM.

[0005](0005-closed-route-lists.md) forbade a classify node so Forecast and freshness would stay deterministic. That reason still holds for those two Route lists. It does not hold for Competence if we accept jitter on the “out of competence” demo.

## Decision

Before any tool, `deepseek-v4-flash` (non-thinking) classifies the question `in` or `out` of Competence. Structured output, two values, nothing else.

- `out` → refuse immediately. No Report retrieval, no web, no Forecast.
- `in` → continue the waterfall (Route lists, retrieve k=10, Drop, web rules as in 0013).

Forecast verbs and Time-sensitive markers stay closed lists. The classify node must not decide those.

## Consequences

- Every in-scope turn pays an extra LLM call.
- The out-of-competence demo can flip if the model disagrees with itself; pin the script to obvious cases (weather, Python, World Cup, uranium).
- [0005](0005-closed-route-lists.md) is narrowed: lists for verbs and freshness only.
- Unit tests for Competence need a mocked classifier or frozen fixtures, not regex.
