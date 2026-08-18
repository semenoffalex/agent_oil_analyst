# Which stubs must die for acceptance

Type: grilling
Status: resolved
Blocked by: 02

## Question

Given the inventory in [Inventory of stubs versus product contracts](02-stubs-versus-product-contracts.md), which items **must be removed** before the customer will accept, which **may stay as safety nets** (with the model still in charge), and which **stay as legitimate product lists** (Yellow-press denylist, Sample Report corpus, two Forecast methods)?

The customer already named citation patching when «Отчёт» is missing, and the out-of-scope dictionary. Confirm those two are fatal. Then walk the rest of the inventory so the spec does not delete the denylist while leaving `_keep_or_restore` in place — or the reverse.

## Answer

Live-model stubs **die**. Infra **safety nets** may stay. Product lists/module rules **stay**. ADR: [0022](../../../docs/adr/0022-live-stubs-die-infra-nets.md).

**Remove when the model returned a live reply:** `_ensure_report_tags`; out-of-scope dictionary as detector; `_keep_or_restore`; heading-rank after e5; Forecast-verb override of classify `out`; Route lists as tool gates (hints in the skill are OK).

**Safety net only** (timeout / 500 / empty): those same helpers, Drop keep-all, uncertainty lines on Yahoo/empty Web. Forgetting `[Отчёт …]` on a live reply is a prompt fail — do not patch.

**Keep:** denylist as a citation contract (not host strip); two Forecast methods, no average, no Urals series; tag grammar; Sample Reports.

## Comments

- Named stubs: keep only as infra nets, not always-on.
- “Сбой” = infra, not a forgetful live answer.
- Restore / heading-rank / verb-override: kill on live model.
- Route lists: prompt hints, not runtime.
- Denylist, two methods, tags, samples, Yahoo uncertainty: keep.
