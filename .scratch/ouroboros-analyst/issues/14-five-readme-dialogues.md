# 14 — Five README dialogues

**What to build:** README documents the five assignment dialogues (Report, Web, combined, Forecast, Out-of-competence) with the spec’s pass rules: grounded `[Отчёт …]`, optional extra Web, Forecast tags if the module ran, refusal without invented numbers. README explains GLM free, Chainlit, Ouroboros, e5+Chroma, Web, statsmodels, and limits (`:free` rates, denylist lag, Yahoo, sample ≠ full). Ingest of Full Reports stays optional and non-fatal.

**Blocked by:** 10 — Grounded Report retrieve; 11 — Web sources without denylist citations; 12 — Forecast module in the loop; 13 — Competence playbook and Safety nets

**Status:** ready-for-agent

- [ ] Five demo prompts are in README; expected checks match ADRs 0019–0020, not v1 tool-flag Eval.
- [ ] Combined quiet demand + Web is allowed if the Report tag is grounded; paragraph order is not a gate.
- [ ] README names stack choices and limits, including OpenRouter `:free` risk and evolve off.
- [ ] Full Report ingest still exists, fails loud, does not empty Sample Reports.
- [ ] Docker volumes persist Chroma and Full Reports across restarts.
