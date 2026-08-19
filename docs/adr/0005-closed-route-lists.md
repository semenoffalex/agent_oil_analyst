# 0005. Closed lists for routing, not a classifier

## Status

Partially superseded: lists do **not** drive the live Ouroboros loop ([0019](0019-model-decides-the-loop.md), [0022](0022-live-stubs-die-infra-nets.md)). Forecast verbs and Time-sensitive markers remain a closed-list **Eval harness** (`oil_gas_analyst/routes.py`, `config/route_lists.yaml`). Competence is not a keyword gate on a live reply; `_OUT_OF_SCOPE` is a Safety net only. [0014](0014-competence-classify-node.md) described an LLM classify node on the old waterfall.

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
