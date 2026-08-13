# Oil and Gas Analyst

A senior oil-and-gas market analyst the user consults for sourced industry answers and oil-price forecasts.

## Language

**Analyst**:
The senior oil-and-gas market analyst the user talks to. It answers industry questions, cites sources, and can request a price forecast.
_Avoid_: agent, chatbot, assistant, Ouroboros

**Report**:
A document in the loaded industry corpus (for example OPEC, IEA, EIA), split into chunks that keep title, date, and page.
_Avoid_: source, document, PDF, “the knowledge base”

**Sample Report**:
A short PDF committed under `/data/samples` so retrieval works with no download. It is not the full agency publication.
_Avoid_: full report, “the MOMR”, placeholder

**Full Report**:
A PDF fetched by the ingest script from an official URL into `/data/reports`. Optional for a first run; required for demos that cite a real edition.
_Avoid_: sample, “whatever is in /data”

**Web source**:
An open-web page retrieved at query time — news, live quotes, regulator statements — after the Yellow-press denylist.
_Avoid_: internet, search, source, article

**Yellow-press denylist**:
A list of domains in the repo that must not be used as Web sources. A domain not on the list can still enter the prompt.
_Avoid_: allowlist, “we filter tabloids” (as if complete), LLM journalism classifier

**Forecast**:
A numeric oil-price projection with a confidence interval, produced by the calculation module, not invented by the language model.
_Avoid_: prediction, estimate, live quote, “the model’s guess”

**Forecast request**:
A user question that contains an explicit forecast verb (English or Russian): forecast, predict, range, estimate, what-if, спрогнозируй, прогноз, оцени диапазон, что если. A horizon without such a verb is not a Forecast request.
_Avoid_: price question, “anything about the future”

**Live quote**:
The latest traded or reported oil price taken from a Web source or a market API. It is not a Forecast.
_Avoid_: price (unqualified), forecast, spot (as a synonym for any price question)

**Retrieved chunks**:
The top-5 Report hits always fetched for a question. Presence in this set does not mean the Analyst may cite them.
_Avoid_: Thin retrieval, “the context”, relevant chunks

**Dropped chunk**:
A Retrieved chunk the Analyst must not cite, because DeepSeek judged it irrelevant to the question. Dropping is not a web trigger by itself.
_Avoid_: Thin retrieval, filter, “the model ignored it” (as a search policy)

**Chunk**:
A heading-bounded piece of a Report, capped at 512 tokens, with title, date, page range, and section heading. It is what retrieval returns, not a PDF page and not a character window.
_Avoid_: page, passage, document, “the context”

**Time-sensitive question**:
A question that needs data newer than the Report corpus. In the first version this is a closed EN+RU keyword list (today, spot, now, latest, statement, сегодня, сейчас, спот, заявление, …), not a classifier.
_Avoid_: fresh, latest, current (as unanalyzed adjectives)

**Competence**:
The Analyst’s subject: upstream, midstream, downstream, oil-price benchmarks (Brent, WTI, Urals), OPEC+, sanctions as they hit the oil market, supply and demand. Weather, coding, medicine, uranium, and general trivia are out. v1 detects this with one in/out classify call, not a keyword list.
_Avoid_: domain, “oil and gas” (unanalyzed), “relevant”, third Route list

**Out-of-competence question**:
A question outside Competence. The Analyst refuses: no web, no Forecast, no invented numbers. Retrieved chunks are not used as an excuse to answer.
_Avoid_: off-topic, jailbreak, “I can’t help with that” (as the definition)

**Route lists**:
Two closed keyword/regex lists (Forecast verbs, Time-sensitive markers) in English and Russian. A miss is a miss; the Analyst does not infer intent.
_Avoid_: router, classifier, planner, “the agent decides”
