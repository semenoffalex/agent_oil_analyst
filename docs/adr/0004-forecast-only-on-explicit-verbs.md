# 0004. Forecast only on explicit verbs

## Status

Accepted

## Context

Thin-or-fresh routing ([0003](0003-thin-or-fresh-web.md)) used “price” as a Time-sensitive trigger. That word also names Forecasts. The two must not share a node.

Alternatives:

- Horizon rule (future window → Forecast; today/bare ticker → Live quote).
- Forecast module owns every numeric price question.
- Any price question always calls both Forecast and web.

## Decision

The Forecast module runs only on a Forecast request: an explicit verb. Anything else about price is a Live quote path (web, subject to 0003).

Implications already accepted:

- “What’s Brent?” → Live quote, not Forecast.
- “Where is Brent headed?” → Live quote, not Forecast (no verb).
- “Brent in 3 months” without a verb → Live quote, not Forecast.

How verbs are detected (closed list vs classifier) is still open.

## Consequences

- Demo “call the calculation module” must use a verb or it will not hit the tool.
- Users who speak in horizons without verbs will get news/quotes, not a projection.
- The verb list is now a product contract, not an NLP nicety.
