# What the agent must decide each turn

Type: grilling
Status: resolved

## Question

The customer said: there is no agent today, only a deterministic pipeline that runs a sequence of functions and turns off; an agent itself decides when to finish and in what order to call tools.

Which of these must be **the model’s decision** on every turn for the work to pass acceptance?

1. Whether the question is in Competence (refuse vs continue).
2. Whether to retrieve Reports, and how many times.
3. Whether to Drop a Retrieved chunk.
4. Whether to search the Web, and when.
5. Whether to run the Forecast module.
6. When to stop and compose the final answer.
7. Order of the above.

Which remain **hard constraints the agent cannot waive**, even if it “decides” the loop — e.g. never invent oil prices, never cite denylist domains, never proxy Urals, always name sources, Reports as primary evidence when they exist?

The v1 spec made Route lists and the waterfall mechanical so demos were deterministic. The customer is now rejecting that shape. This ticket must say how much determinism the grader still requires.

## Answer

The **solve model** decides all seven: Competence, retrieve (whether and how often), Drop, Web, Forecast, stop, and order. The host must not refuse those calls.

Acceptance grades the **visible answer**. A bad tool trace is a **prompt** failure, not a missing runtime lock.

Hard constraints the Analyst cannot waive in the answer:

- Out-of-competence → refuse, no invented figures. Extra Web on weather = prompt fail, not a host block.
- Forecast needs no verb. If the module ran, tag `[Forecast …]`. No prices/volumes except from Reports, Web sources, or Forecast.
- Denylist domains must not appear as citations. Host does **not** strip hits before the model sees them.
- If the Report corpus supports the question, the answer **must** include `[Отчёт …]`. Web-only on a covered demand outlook fails.
- Urals: the Forecast tool still has no series; do not invent one.

Grader determinism: do not freeze tool order. ADR: [0019](../../../docs/adr/0019-model-decides-the-loop.md).

## Comments

- Weather + tools: customer chose host does not block; extra Web is prompt fail.
- Forecast without a verb: allowed if tagged `[Forecast …]`.
- Denylist: model sees kp.ru; citing it fails the prompt, not the runtime.
- Corpus-covered OPEC demand without `[Отчёт …]`: acceptance fail.
