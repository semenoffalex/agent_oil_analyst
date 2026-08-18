# Inventory of stubs versus product contracts

Type: research
Status: resolved

## Question

In the current `oil_gas_analyst` tree (and the v1 spec / ADRs it encodes), which code paths **substitute a hardcoded rule for a model decision** — the class of thing the customer called stubs — and which are **named product contracts** that would still exist even if the Analyst were a real agent?

The customer named two examples; do not stop there:

- inserting Report chunks when the answer text lacks «Отчёт» (`_ensure_report_tags`);
- a dictionary that filters out-of-scope questions (`_OUT_OF_SCOPE` / `is_out_of_scope_topic`).

Also inventory at least: `_keep_or_restore` / heading markers after Drop; closed Route lists for Forecast verbs and Time-sensitive markers; the fixed LangGraph node order; `REFUSAL_TEXT`; retrieve-k and heading-rank heuristics; Yellow-press denylist.

For each item: file + behavior in one line, then tag **stub** (papers over the model), **contract** (TZ/spec/ADR product rule), or **mixed**. Do not recommend what to delete — that is [Which stubs must die for acceptance](06-which-stubs-must-die.md).

## Answer

Full write-up: [stubs-versus-contracts](../research/stubs-versus-contracts.md).

**stub** (hardcoded rule papers over a model decision):

- `_ensure_report_tags` — `turn.py`: if kept chunks exist and the answer lacks `[Отчёт`, append chunk snippets plus Report labels.
- `_OUT_OF_SCOPE` / `is_out_of_scope_topic` — `routes.py` (used in `turn.py` `step_classify`): phrase dictionary substitutes for Competence classify on infra error and blocks Forecast-verb override on weather/Python/uranium/etc.
- `_keep_or_restore` + `_REPORT_HEADING_MARKERS` / `_REPORT_TEXT_MARKERS` — `turn.py`: if Drop returns empty, restore on-topic Report chunks by heading/text markers.
- Forecast-verb override of classify `out` — `turn.py`: Route-list Forecast hit continues the turn even when classify said `out` (unless the dictionary matches).
- Dropper keep-all on exception — `llm.py`: Drop failure keeps every Retrieved chunk.
- `_heading_rank` / `select_report_chunks` — `retrieve.py`: after e5, boost outlook headings / demote tanker-coal-appendix / prefer newer full Reports.

**mixed** (named product rule implemented as a mechanical substitute for an agent decision):

- Closed Route lists (Forecast verbs, Time-sensitive, plus weak/outlook extras) — `routes.py`, `config/route_lists.yaml`: miss-is-a-miss lists (ADR 0004/0005) instead of the model deciding Forecast vs web.
- Fixed LangGraph / `run_turn` order — `graph.py`, `turn.py`: classify → retrieve → drop → tools? → compose; tools only if `want_forecast` or `want_web`.
- Mechanical web triggers — `turn.py`: Time-sensitive, all-Dropped, or retrieve-error set `want_web` with no model ask.
- `REFUSAL_TEXT` — `turn.py`: canned English refusal; compose never runs on `out`.
- Post-compose `FORECAST_UNAVAILABLE` / empty-web append — `turn.py`: canned uncertainty concatenated after compose.
- Composer exception fallback sentence — `llm.py`: infra failure returns a stock “will not invent figures” line.

**contract** (would still exist for a real agent as a tool, list, format, or hard constraint):

- Retrieve k=10 on every in-Competence turn — `deps.py` / `retrieve.py`, spec US24, ADR 0012.
- Yellow-press denylist — `denylist.py`, `config/yellow_press_denylist.yaml`, ADR 0008 (not an LLM classifier).
- Citation label grammar + Sources links — `turn.py`, `app.py` (`[Отчёт …]` / `[Источник: …, web]` / Forecast labels).
- Forecast module: SARIMA + Holt–Winters, never averaged; Brent default; WTI if named; Urals no series; no CSV — `forecast.py`, ADR 0009.
- Out-of-competence → no tools, no invented numbers — spec US9–11, ADR 0013/0014 (the *policy*; detection is the classify contract, not the dictionary stub).
- Competence classify + model Drop + compose — `llm.py`, ADR 0012/0014 (these *are* the model decisions).
- Ingest heading regexes, 512-token cap, Sample Reports, e5 prefixes — `ingest.py` / `retrieve.py`, ADR 0015/0007/0011.
- `drop_redundant_excerpts` — `retrieve.py`: skip a Sample excerpt when the same-date Full Report is present.

No deletion recommendations here.
