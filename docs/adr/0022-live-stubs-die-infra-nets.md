# 0022. Live-model stubs die; infra safety nets may stay

## Status

Accepted

## Context

Acceptance called out hardcoded stubs (citation insert, out-of-scope dictionary). The inventory in [02](../../.scratch/ouroboros-analyst/issues/02-stubs-versus-product-contracts.md) listed more. The customer then chose **not** to delete every helper: code may catch a **dead** model, but must not rewrite a **live** one. That sits on [0019](0019-model-decides-the-loop.md) (model owns the loop) and [0020](0020-waterfall-grounded-citations.md) (no fake `[Отчёт …]`).

## Decision

**Kill on a live completion** (timeout / HTTP 500 / empty model output are not “live”):

- Inserting Report chunks or `[Отчёт …]` because the prose lacked the tag.
- The out-of-scope phrase dictionary as a Competence detector or Forecast override.
- Restoring Dropped chunks by heading/text markers (`_keep_or_restore`).
- Re-ranking Retrieved chunks with a heading dictionary after e5.
- Letting a Forecast-verb list override classify `out`.
- Route lists **driving** Forecast/Web. They may remain as **prompt/skill hints** only.

**Allowed only as infra safety nets** (classify/Drop/compose timed out, 500, empty): dictionary in/out, Drop keep-all, citation append if retrieve already ran this turn, canned uncertainty when Yahoo or Web returned nothing. A live answer that forgot `[Отчёт …]` is a prompt fail — do not patch it.

**Stay as product contracts:** Yellow-press domain **list** (Eval on citations, not a host strip); two Forecast methods never averaged; no Urals series; citation label grammar; Sample Reports; say uncertainty on Yahoo/empty Web instead of inventing a price.

## Consequences

- Tests that lock “compose without `[Отчёт` → host appends a block” on a successful model reply must go. Infra-path tests may remain.
- [0005](0005-closed-route-lists.md) as a runtime router is superseded; lists as playbook text are allowed.
- The destination “no stubs” means no **live-model** fakes, not “zero host fallbacks.”
