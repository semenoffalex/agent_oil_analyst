# 0005. Closed lists for routing, not a classifier

## Status

Partially superseded: Forecast verbs and Time-sensitive markers stay closed lists. Competence is an LLM classify node — [0014](0014-competence-classify-node.md). The blanket “no classify node” does not apply to Competence.

## Context

Forecast requests ([0004](0004-forecast-only-on-explicit-verbs.md)) and Time-sensitive questions ([0003](0003-thin-or-fresh-web.md)) need a detector. Alternatives were an LLM classify node every turn, lists-then-LLM, or lists for verbs and LLM for freshness.

A classifier would treat horizon-without-verb questions as Forecasts and make demo traces non-deterministic.

## Decision

Routing uses two closed EN+RU keyword/regex lists: Forecast verbs and Time-sensitive markers. No classify node. A phrase not on a list does not match.

Thin retrieval stays a numeric bar on Report search, not a list and not an LLM.

## Consequences

- Routing is unit-testable without a model.
- Missed phrasings are list edits, not prompt tweaks.
- The lists themselves are now part of the product contract and belong in the repo, not in a system prompt.
