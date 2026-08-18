# 0020. Waterfall is grounded citations, not paragraph order

## Status

Accepted

## Context

[0019](0019-model-decides-the-loop.md) put tool order in the model and required `[Отчёт …]` when the corpus covers the question. The assignment still says Reports first, Web as supplement. Open: whether extra Web on a quiet demand outlook fails; whether a Report tag may be remembered without retrieve this turn; whether prose must lead with the Report.

## Decision

The TZ waterfall is **prompt policy plus Eval on citations**, not a host graph and not a prose template.

- On a quiet demand outlook (no freshness marker), a **combined** answer is fine: `[Отчёт …]` plus `[Источник: …, web]`. Extra Web does not fail if the Report tag is present.
- An `[Отчёт …]` tag is valid only if retrieve ran **this turn** and the citation is grounded in that result. A matching figure from memory or the system prompt without retrieve is a fail (hallucinated source).
- Paragraph order is not graded. Reports before Web in the prose is a style hint, not an acceptance gate.

Together with 0019: a corpus-covered question passes only if retrieve ran this turn **and** the answer cites that result as `[Отчёт …]`. The host still does not force the call; skipping retrieve and then omitting or faking the tag both fail Eval as prompt failures.

## Consequences

- Demo 1 (Report) may also contain Web tags. Demo 3 (combined) is not restricted to “today”.
- Eval must see a retrieve tool result when scoring `[Отчёт …]`, not only the string in the reply.
- `_ensure_report_tags` (insert labels without a model cite) remains a stub to kill: it would fake grounding.
