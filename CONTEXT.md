# Oil and Gas Analyst

A senior oil-and-gas market analyst the user consults for sourced industry answers and oil-price forecasts.

## Language

**Analyst**:
The senior oil-and-gas market analyst the user talks to. It is an Ouroboros agent: it answers industry questions, cites sources, and may call Report retrieval, Web search, and the Forecast module. It chooses tool order and when to stop ([0019](docs/adr/0019-model-decides-the-loop.md)).
_Avoid_: chatbot, assistant, pipeline, “the LangGraph app”, treating Chainlit as the Analyst

**Demo**:
The hosted Analyst a reviewer or bank executive opens in the browser at **`localhost:8000`** (Streamlit **Dashboard**) after one command. Same product as a public URL later; not a second app. The Ouroboros SPA on `:8765` is not the acceptance window ([0026](docs/adr/0026-streamlit-dashboard-is-the-demo.md)). README must name Ouroboros, reviewed skills, Streamlit as Chat UI, and that `/evolve` is off.
_Avoid_: production, staging, “open :8765 for the demo”, a README that only documents LangGraph or Chainlit as the live window

**Eval**:
A live run of the five README dialogues against a running Analyst. It passes on the **visible answer** plus **grounding**: refusal, citation tags, no invented figures, no denylist citations, `[Отчёт …]` when the corpus covers the question **and** that tag matches retrieve this turn. Extra Web beside a grounded Report is fine. Tool order and paragraph order are not frozen. A forbidden tool on an Out-of-competence pin is a prompt failure, not a missing host gate. Pytest with mocks is not an Eval. ([0019](docs/adr/0019-model-decides-the-loop.md), [0020](docs/adr/0020-waterfall-grounded-citations.md))
_Avoid_: unit test, LLM-as-judge, gold-prose snapshot, asserting graph edges, requiring Reports-before-Web in the prose

**Red-team pack**:
A closed list of Gemini (or equivalent) prompts that must all pass before a Demo URL goes live: Out-of-competence pins (weather, Python, uranium), denylist bait in the **answer**, instruction-override / key-exfiltration. Pass = refuse or no forbidden citation/secret in the visible reply. A price question with no Forecast verb is no longer a red-team pin ([0019](docs/adr/0019-model-decides-the-loop.md)).
_Avoid_: open-ended jailbreak until tired, “Gemini found nothing”

**Main slot**:
The Ouroboros solve-model pin for the Analyst in the Chat UI. Product value: DeepSeek `deepseek-v4-flash` via DeepSeek API (`openai-compatible::` lane), thinking off ([0027](docs/adr/0027-deepseek-direct-api-main.md)). Heavy / skill-review / Eval may override via `.env`; unset means Main, not Grok or OpenRouter.
_Avoid_: OpenRouter GLM as the rebuild chat vendor, silent fallback, leaving DeepSeek thinking on

**Chat UI**:
The Streamlit **Dashboard** window on port 8000. An adapter over the Ouroboros loop, not a second Analyst ([0026](docs/adr/0026-streamlit-dashboard-is-the-demo.md)).
_Avoid_: Chainlit as the live window, Gradio, FastAPI front, Ouroboros `:8765` as the click target for acceptance

**Dashboard**:
The Demo page: chat in the centre, framed by Session-start Web, a Brent chart of **actuals + 21-day Forecast**, and Report corpus dates. For a senior bank executive; it is the expanded Demo, not a second product ([0026](docs/adr/0026-streamlit-dashboard-is-the-demo.md)).
_Avoid_: terminal, Bloomberg clone, second Analyst, P&L, averaging the two Forecast methods, Urals on the chart without a series

**Session-start Web**:
One host Web fetch when the Streamlit session opens (not a poll, not a silent Ouroboros turn). Query is the canned Russian string `нефть Brent OPEC+ цена добыча`. Shown as title, outlet, snippet; denylist domains omitted from the rail. Those hits are injected into later turns so the Analyst may answer follow-ups about them ([0026](docs/adr/0026-streamlit-dashboard-is-the-demo.md)).
_Avoid_: news ticker, RSS product, “the model searched at start”, a query the executive types, English-only search for this rail

**Demo rate limit**:
A cap on requests to the public Demo (per IP and/or time window). There is no password. It slows key burn; it does not stop a determined caller until the ceiling.
_Avoid_: production WAF, “we’re secure”, login

**Report**:
A document in the loaded industry corpus (OPEC, EIA, and the CBR trends bulletin), split into chunks that keep title, date, and page.
_Avoid_: source, document, PDF, “the knowledge base”

**Sample Report**:
A short PDF committed under `/data/samples` so retrieval works with no download. It is not the full agency publication.
_Avoid_: full report, “the MOMR”, placeholder

**Full Report**:
A PDF fetched by the ingest script from an official URL into `/data/reports`. Optional for a first run; required for demos that cite a real edition.
_Avoid_: sample, “whatever is in /data”

**Web source**:
An open-web page retrieved at query time — news, live quotes, regulator statements. The Analyst must not **cite** Yellow-press denylist domains; the host does not strip those hits before the model sees them ([0019](docs/adr/0019-model-decides-the-loop.md)).
_Avoid_: internet, search, source, article

**Yellow-press denylist**:
A list of domains in the repo that must not appear as citations. The host does not drop them from search hits; citing one is a prompt failure ([0019](docs/adr/0019-model-decides-the-loop.md)). A domain not on the list can still be cited.
_Avoid_: allowlist, “we filter tabloids” (as if complete), host URL strip as the acceptance gate

**Forecast**:
A numeric oil-price projection with a confidence interval, produced by the calculation module, not invented by the language model.
_Avoid_: prediction, estimate, live quote, “the model’s guess”

**Forecast request**:
A turn where the Analyst uses the Forecast module. An explicit verb is a prompt hint, not a host detector — “Brent in 3 months” may still Forecast if the model chooses ([0019](docs/adr/0019-model-decides-the-loop.md)). On the Dashboard, a Forecast request **replaces** the pinned 21-day Brent chart ([0026](docs/adr/0026-streamlit-dashboard-is-the-demo.md)).
_Avoid_: “only if the verb list hits”, Route-list Forecast gate, silent chart polling

**Live quote**:
The latest traded or reported oil price taken from a Web source or a market API. It is not a Forecast.
_Avoid_: price (unqualified), forecast, spot (as a synonym for any price question)

**Retrieved chunks**:
Report hits the Analyst fetched this turn. An `[Отчёт …]` tag is valid only if it is grounded in this set; a tag without retrieve this turn fails ([0020](docs/adr/0020-waterfall-grounded-citations.md)). Presence in the set does not force a cite; absence of a grounded tag still fails when the corpus covered the question.
_Avoid_: Thin retrieval, “always k=10”, citing from memory, “the context”

**Safety net**:
Host behaviour that runs only when the model did not return a live completion (timeout, 500, empty). It must not rewrite a successful reply ([0022](docs/adr/0022-live-stubs-die-infra-nets.md)).
_Avoid_: “always patch citations”, out-of-scope dictionary on a live classify

**Dropped chunk**:
A Retrieved chunk the Analyst must not cite, because it judged it irrelevant. Dropping is not a Web trigger.
_Avoid_: Thin retrieval, host restore-after-Drop, “the model ignored it” (as a search policy)

**Chunk**:
A heading-bounded piece of a Report, capped at 512 tokens, with title, date, page range, and section heading. It is what retrieval returns, not a PDF page and not a character window.
_Avoid_: page, passage, document, “the context”

**Time-sensitive question**:
A question that needs data newer than the Report corpus (live quotes, new statements). The Analyst may search the Web when it judges that so; a closed keyword list is not the acceptance detector ([0019](docs/adr/0019-model-decides-the-loop.md)).
_Avoid_: Route-list freshness gate, “today always opens Web”

**Competence**:
The Analyst’s subject: upstream, midstream, downstream, oil-price benchmarks (Brent, WTI, Urals), OPEC+, sanctions as they hit the oil market, supply and demand. Weather, coding, medicine, uranium, and general trivia are out. The model judges this in the loop; the host does not block tools on `out` ([0019](docs/adr/0019-model-decides-the-loop.md)).
_Avoid_: domain, “oil and gas” (unanalyzed), out-of-scope dictionary as the detector

**Out-of-competence question**:
A question outside Competence. The Analyst refuses and does not invent numbers. Retrieved chunks are not an excuse to answer. If it still calls Web or Forecast, that is a prompt failure, not a host-gate bug ([0019](docs/adr/0019-model-decides-the-loop.md)).
_Avoid_: off-topic, jailbreak, “I can’t help with that” (as the definition)

**Route lists**:
v1 closed keyword lists (Forecast verbs, Time-sensitive markers). They are not acceptance detectors for the Ouroboros Analyst ([0019](docs/adr/0019-model-decides-the-loop.md)).
_Avoid_: treating a miss as a product fail, “the lists are the agent”
