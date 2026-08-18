# Stubs versus product contracts

Criterion (from [02](../issues/02-stubs-versus-product-contracts.md)):

- **stub** — a hardcoded rule that *substitutes for a model decision* (papers over classify / Drop / compose / tool choice).
- **contract** — a named TZ / spec / ADR product rule that would still exist if the Analyst were a real agent (a tool, a list, a hard constraint, a citation format).
- **mixed** — a named product rule *implemented as* a mechanical substitute for a model/agent decision.

Sources: `oil_gas_analyst/` (current tree), `.scratch/oil-gas-analyst/spec.md`, ADRs 0003–0005, 0008–0009, 0012–0015. Glossary terms from `CONTEXT.md`.

This note does not say what to delete. That is [06](../issues/06-which-stubs-must-die.md).

---

## Customer-named examples

### `_ensure_report_tags` — **stub**

- **Where:** `oil_gas_analyst/turn.py` (`step_compose` → `_ensure_report_tags`)
- **Behavior:** After the composer returns, if any chunks were kept and the prose lacks `[Отчёт`, append truncated chunk text plus mechanical Report citation labels.
- **Why stub:** The compose model is supposed to tag claims (spec user stories 5–6; `COMPOSE_SYSTEM` in `llm.py`). This path fakes a Report-backed answer when the model did not cite. Tests lock it: `tests/test_turn.py` `test_compose_without_report_tag_appends_report_block`.
- **Adjacent contract (not this function):** the citation *format* `[Отчёт {title}, {date}, pp. …]` / excerpt marker is a product rule (`_report_citation`). The stub is the post-hoc insertion, not the label grammar.

### `_OUT_OF_SCOPE` / `is_out_of_scope_topic` — **stub**

- **Where:** `oil_gas_analyst/routes.py`; used from `step_classify` in `turn.py`
- **Behavior:** Closed phrase list (`weather`/`погод`, `python`, `world cup`/`чемпионат мира`, `uranium`/`уран`, `medicine`/`медицин`). Two live uses:
  1. Classifier *exception* fallback: infra error → dictionary decides in vs out (`test_classify_infra_error_still_answers_oil_question` / `…_still_refuses_weather`).
  2. Forecast-verb override gate: if classify says `out` but a Forecast verb is present, still continue *unless* the dictionary matches (`test_bare_forecast_request_runs_even_if_classifier_says_out` vs `test_forecast_verb_on_weather_still_refuses`).
- **Why stub:** ADR 0014 and spec user story 12 name Competence as **one in/out classify call, not a keyword list for this gate**. Spec Further Notes only *pin demos* to weather / Python / World Cup / uranium — they do not authorize a runtime dictionary. The dictionary papers over classify jitter and classify downtime.
- **Adjacent contract:** Out-of-competence → refuse, no retrieve / web / Forecast, no invented numbers (spec US9–11, ADR 0013/0014). That policy is a contract; the dictionary is not how v1 said to detect it.

---

## Requested inventory

### `_keep_or_restore` / `_REPORT_HEADING_MARKERS` / `_REPORT_TEXT_MARKERS` — **stub**

- **Where:** `oil_gas_analyst/turn.py` (`step_drop`)
- **Behavior:** If the Dropper returns a non-empty keep-set, trust it. If it returns empty, restore Retrieved chunks whose heading or body matches a closed oil-price/demand/supply marker list (and thereby skip the ADR 0013 “all Dropped → web” path).
- **Why stub:** ADR 0012: DeepSeek Drops; Dropped chunks must not be cited. Spec US25: Dropped chunks never cited. Restore un-drops by keyword when the model emptied the set. Tests: `test_overdrop_of_on_topic_chunks_stays_on_reports`, `test_overdrop_restores_demand_not_tanker`.
- **Adjacent contract:** “Do not cite Dropped chunks” and “in Competence + every chunk Dropped → one web call” (ADR 0013) remain product rules; this function is the override of the Drop decision.

### Closed Route lists (Forecast verbs, Time-sensitive markers, weak/outlook extras) — **mixed**

- **Where:** `config/route_lists.yaml`; matchers in `oil_gas_analyst/routes.py` (`is_forecast_request`, `is_time_sensitive`); consumed in `step_classify` / `needs_tools` / `step_tools`
- **Behavior:** Closed EN+RU lists. A miss is a miss. Extra lists `time_sensitive_weak` + `published_outlook` keep “now/latest + consensus/outlook/MOMR/STEO” off the web path.
- **Contract half:** Forecast only on explicit verbs, not a horizon or “headed” (ADR 0004, spec US14–16, 46). Time-sensitive in Competence opens DuckDuckGo (ADR 0003 remainder, spec US17). Lists live in config and are unit-tested without a model (ADR 0005, spec US46). Those *policies* would still exist as tool-gating rules for a real agent (never invent a strip when the Forecast module did not run — spec US49).
- **Stub half:** The detector is a regex/keyword substitute for an agent deciding “is this a Forecast request?” / “do I need the web?”. ADR 0005 and CONTEXT.md explicitly keep the model *out* of those two gates. Map notes these lists are the artefact under review, not sacred.

### Fixed LangGraph node order — **mixed**

- **Where:** `oil_gas_analyst/graph.py` (`classify → retrieve → drop → tools? → compose`); same order in `run_turn` (`turn.py`)
- **Behavior:** START always classify; `out` → END with refusal (no retrieve); else retrieve then drop; tools node only if `want_forecast` or `want_web`; then compose. `needs_tools` is a boolean, not a model.
- **Contract half:** Spec Implementation Decisions and ADR 0003/0012/0014 *name* this waterfall. Out of scope in the v1 spec: “a planner that may call web whenever it wants.” Reports-first, refuse-before-tools, Forecast-only-on-request, web-only-on-named-triggers are product constraints.
- **Stub half:** The graph itself is the deterministic pipeline the customer contrasted with an agent that chooses tool order and when to stop. Conditional edges encode those choices in code, not in the model.

### `REFUSAL_TEXT` — **mixed**

- **Where:** `oil_gas_analyst/turn.py` (`finish_refuse`)
- **Behavior:** Out-of-competence turns never call the composer. Reply text is a frozen English paragraph; tests assert it (`tests/test_graph.py`).
- **Contract half:** Refuse, no tools, no invented numbers (spec US8–11, ADR 0014).
- **Stub half:** The model does not write the refusal. A real agent would still refuse; it would not need this exact canned string.

### Retrieve `k=10` — **contract**; heading-rank — **stub**

Split; they are different kinds of rule.

**Retrieve k=10 — contract**

- **Where:** `AnalystDeps.retrieve_k` default 10; `deps.py` `RETRIEVE_K` env; `ChromaRetriever.retrieve`; spec US24; ADR 0012
- **Behavior:** Every in-Competence turn fetches ten Report chunks before Drop. Pool for re-rank is `min(max(k*3, 10), total)`.
- **Why contract:** Named product number (“Reports always consulted first”). A real agent still has a retrieve tool with a pool size; k=10 is the v1 contract for that tool, not a fake of a model decision.

**`_heading_rank` / `select_report_chunks` — stub**

- **Where:** `oil_gas_analyst/retrieve.py`
- **Behavior:** After vector search, re-rank: boost outlook headings (`crude oil price`, `world oil demand`, …), demote tanker/electricity/coal/appendix unless the question names them, prefer newer dates and full Reports over excerpts.
- **Why stub:** Not named in spec or ADRs (0012 is Drop-after-retrieve; 0015 is ingest chunking). Hardcoded heading keywords substitute for e5 ranking / the later Drop decision. Tests in `tests/test_ingest.py` lock the boost.

### Yellow-press denylist — **contract**

- **Where:** `config/yellow_press_denylist.yaml`; `oil_gas_analyst/denylist.py`; applied in `step_tools` and `web.fill_page_bodies`
- **Behavior:** After DuckDuckGo returns, drop URLs whose host is on the list (or a subdomain). Not an allowlist; unlisted tabloids can leak (spec US22–23, ADR 0008).
- **Why contract:** Explicit product list; ADR 0008 rejects an LLM journalism classifier. A real agent would still be forbidden to cite those domains. Map “Out of scope” already says not to replace this list in this effort.

---

## Other paths in the current tree

### Forecast-verb override of classify `out` — **stub**

- **Where:** `step_classify` in `turn.py` (`classified_out and not (want_forecast and not is_out_of_scope_topic(...))`)
- **Behavior:** If the classify model says `out` but Route lists hit a Forecast verb and the out-of-scope dictionary misses, the turn continues and Forecast runs.
- **Why stub:** Papers over a classify `out` on in-Competence Forecast phrasing (e.g. “Построй свой прогноз.”). ADR 0014: classify is the Competence gate; Route lists must not be decided by classify — this goes the other way and lets Route lists override classify.

### Dropper fail-open (keep all on exception) — **stub**

- **Where:** `DeepSeekDropper.keep` in `llm.py`
- **Behavior:** If the Drop structured call throws, return every Retrieved chunk.
- **Why stub:** Substitutes “keep all” for a Drop decision on infra error (symmetric to classify’s dictionary fallback).

### `FORECAST_UNAVAILABLE` and empty-web notices appended after compose — **mixed**

- **Where:** `step_compose` in `turn.py`
- **Behavior:** After compose, if Yahoo failed, append a canned uncertainty sentence (spec US38). If web ran with zero surviving hits, append “Web search returned no usable sources…”.
- **Contract half:** Blocked Yahoo / empty DuckDuckGo must look like uncertainty, not a crash or invented figures (spec Further Notes, ADR 0009).
- **Stub half:** The composer is not trusted to say so; code concatenates the sentence.

### Mechanical web triggers (`want_web`) — **mixed**

- **Where:** `step_classify` (Time-sensitive → `WEB_REASON_TIME_SENSITIVE`); `step_retrieve` exception → `WEB_REASON_RETRIEVE_ERROR`; `step_drop` empty kept → `WEB_REASON_NO_KEPT`
- **Contract half:** Spec US17–19 / ADR 0013: web if Time-sensitive and in Competence, or all Chunks Dropped and in Competence; never on Out-of-competence even with “today”.
- **Stub half:** The model is not asked whether to search. Retrieve-error → web is an extra infra shortcut not named in the spec.

### Citation label builders and Markdown linking — **contract**

- **Where:** `_report_citation`, `_web_citation`, `_forecast_citations`, `markdown_cite`, `apply_citation_links` in `turn.py`; Sources footer in `app.py`
- **Behavior:** Deterministic `[Отчёт …]` / `[Источник: host, web]` / `[Forecast method symbol …]` labels from metadata; optional URL links.
- **Why contract:** Spec US5–7. A real agent would still have to name origin; assembling labels from Chunk/WebHit/ForecastResult fields is product format, not a fake of compose (unless `_ensure_report_tags` stuffed the labels in).

### Forecast module (two methods, symbols, Urals, no CSV) — **contract**

- **Where:** `oil_gas_analyst/forecast.py`, `config/forecast.yaml`, ADR 0009, spec US33–38
- **Behavior:** Always SARIMA and Holt–Winters, never averaged; default Brent (`BZ=F`); WTI if named; Urals → no series; Yahoo failure → error, not a CSV.
- **Why contract:** Calculation tool rules. `detect_symbol` / `detect_horizon` are tool-argument parsers (config phrase lists), not substitutes for “should I forecast?” (that gate is Route lists, tagged mixed above).

### Ingest: heading regexes, 512-token cap, Sample Reports, e5 prefixes — **contract**

- **Where:** `ingest.py` + `config/ingest.yaml` (ADR 0015); Sample/Full Reports (ADR 0011, spec US27–30); `E5EmbeddingFunction` prefixes (spec US43, ADR 0007)
- **Why contract:** Corpus and retrieval plumbing. Heading regexes miss some STEO boxes on purpose (untitled leftovers). Not model-decision substitutes.

### `drop_redundant_excerpts` — **contract**

- **Where:** `retrieve.py`
- **Behavior:** Skip a Sample excerpt when a Full Report of the same agency+date is present.
- **Why contract:** Index hygiene so a sample cannot masquerade as a full edition (spec US6, 30).

### Competence classify node and Dropper/Composer LLM calls — **contract** (the model path)

- **Where:** `llm.py` `DeepSeekClassifier` / `DeepSeekDropper` / `DeepSeekComposer`; ADR 0014 / 0012
- **Why contract:** These *are* the model decisions. Prompts that say “prefer keeping a Crude Oil Price chunk over an empty list” or “MUST tag [Отчёт]” instruct the model; they are not code stubs. The stubs are the post-model enforcers (`_keep_or_restore`, `_ensure_report_tags`).

### Composer exception fallback sentence — **mixed**

- **Where:** `DeepSeekComposer.compose` except-path in `llm.py`
- **Behavior:** On compose failure, return “I could not compose a full answer. See citations. I will not invent figures.”
- **Why mixed:** Honest infra fallback (contract: do not invent figures) that also skips the model writing the answer.

---

## Contradictions with named ADRs (inventory only)

- `_OUT_OF_SCOPE` as a live Competence detector **contradicts ADR 0014** / spec US12 (classify is not a keyword list for this gate).
- `_keep_or_restore` **contradicts ADR 0012** when it un-drops after the model returned an empty keep-set.
- Forecast-verb override of classify `out` **narrows ADR 0014** the other way (lists override classify).
- Fixed waterfall **is** ADR 0003/0012/0014; the customer’s “agent chooses order” destination **reopens** those ADRs (map already flags 0005, 0012, 0014).

---

## Compact tagged list

| Item | File | Tag |
|---|---|---|
| `_ensure_report_tags` inserts Report chunks when prose lacks `[Отчёт` | `turn.py` | **stub** |
| `_OUT_OF_SCOPE` / `is_out_of_scope_topic` dictionary | `routes.py` (+ `turn.py`) | **stub** |
| `_keep_or_restore` + heading/text markers after Drop | `turn.py` | **stub** |
| Forecast-verb override of classify `out` | `turn.py` | **stub** |
| Dropper keep-all on exception | `llm.py` | **stub** |
| `_heading_rank` / `select_report_chunks` | `retrieve.py` | **stub** |
| Closed Route lists (Forecast verbs, Time-sensitive ± weak/outlook) | `routes.py`, `config/route_lists.yaml` | **mixed** |
| Fixed LangGraph / `run_turn` node order | `graph.py`, `turn.py` | **mixed** |
| Mechanical web triggers (time-sensitive / no-kept / retrieve-error) | `turn.py` | **mixed** |
| `REFUSAL_TEXT` canned refusal | `turn.py` | **mixed** |
| Post-compose `FORECAST_UNAVAILABLE` / empty-web append | `turn.py` | **mixed** |
| Composer exception fallback sentence | `llm.py` | **mixed** |
| Retrieve k=10 always on in-Competence | `deps.py`, `retrieve.py`, ADR 0012 | **contract** |
| Yellow-press denylist | `denylist.py`, `config/yellow_press_denylist.yaml`, ADR 0008 | **contract** |
| Citation label grammar + Sources links | `turn.py`, `app.py` | **contract** |
| Forecast module: two methods, Brent/WTI/Urals, no CSV | `forecast.py`, ADR 0009 | **contract** |
| Out-of-competence → no tools (the policy) | spec US9–11, ADR 0013/0014 | **contract** |
| Competence classify + model Drop + compose | `llm.py`, ADR 0012/0014 | **contract** |
| Ingest heading regexes, 512-token cap, Sample Reports, e5 prefixes | `ingest.py`, `retrieve.py` | **contract** |
| `drop_redundant_excerpts` | `retrieve.py` | **contract** |
