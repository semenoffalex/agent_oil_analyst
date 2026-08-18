Status: ready-for-agent

# Spec: Ouroboros Analyst

## Problem Statement

A reviewer must accept a senior oil-and-gas market Analyst that is a **real agent**, not a LangGraph pipeline that runs a fixed sequence and stops. The assignment still requires industry answers, Report RAG, Web sources, a Forecast calculation module, cited origins, a simple browser UI, one-command Docker, and five demo dialogues. Acceptance rejected ADR 0002: Ouroboros was never waived. Live-model stubs that fake `[Отчёт …]` or Competence must not paper over a successful model reply.

## Solution

The reviewer opens Chainlit at `localhost:8000` after one command. That window is an adapter: the turn runs in **current-generation Ouroboros**. The solve model chooses tools and when to stop. Domain body is reviewed extension tools (Report retrieve, Web search, Forecast) plus `identity.md` and an instruction skill. The host does not refuse those calls. Acceptance grades the **visible answer** and **grounding** (an `[Отчёт …]` tag must match retrieve this turn when the corpus covers the question). `/evolve` is off. README names Ouroboros so the grader does not need the `:8765` SPA. Main chat is OpenRouter `z-ai/glm-5.2:free` with thinking off.

## User Stories

1. As a reviewer, I want to copy `.env.example` to `.env`, set the OpenRouter key, and run one Docker/compose command, so that Chainlit is on port 8000.
2. As a reviewer, I want to click `http://localhost:8000` and chat, so that I do not install `Ouroboros.app` or open `:8765` for acceptance.
3. As a reviewer, I want Chainlit to send my message into the Ouroboros loop, so that I am not talking to a LangGraph waterfall.
4. As a reviewer, I want to verify Ouroboros in this repository (adapter wiring, skills, identity, compose), so that I do not have to open Ouroboros Skills or Dashboard.
5. As a reviewer, I want the README to say the runtime is Ouroboros, domain tools are reviewed skills, Chainlit is an adapter, and `/evolve` is off, so that I do not mistake this for LangGraph-only.
6. As a reviewer, I do not want task-acceptance Review, P3 commit Review, or `/review` on the five Eval dialogues, so that oil questions are not graded by Ouroboros constitutional review.
7. As a reviewer, I want `/evolve` off (`light` or equivalent) for Demo and Eval, so that the Analyst cannot rewrite itself mid-demo.
8. As a user, I want the Analyst to speak as a senior oil-and-gas market analyst (upstream, midstream, downstream, Brent/WTI/Urals, OPEC+, sanctions as they hit the market, supply and demand), so that answers match Competence.
9. As a user, I want that role on Ouroboros `identity.md` plus an instruction skill, so that BIBLE/SYSTEM stay Ouroboros and are not rewritten as an oil constitution.
10. As a user, I want structured answers with figures, so that I can reuse them.
11. As a user, I want every material claim tagged `[Отчёт …]`, `[Источник: …, web]`, or `[Forecast …]`, so that I can tell origin.
12. As a user, I want Report citations to include title, date if known, page range, and “excerpt” when the Chunk is from a Sample Report, so that a sample is not sold as a Full Report.
13. As a user, I want Web citations to include outlet and that they are web, so that I can judge freshness.
14. As a user, I want the Analyst to say when it does not know, so that I never get invented figures.
15. As a user, I ask an Out-of-competence question (weather, Python, World Cup, uranium), so that I get a refusal and no invented numbers.
16. As a reviewer, I treat extra Web or Forecast on that Out-of-competence pin as a **prompt** failure, so that we do not “fix” it with a host tool block.
17. As a user, I ask an in-Competence question, so that the model may retrieve, search, Forecast, or stop as it chooses.
18. As a user, I want the model to decide tool order and when to stop, so that the turn is an agent loop, not classify→retrieve→drop→tools→compose.
19. As a reviewer, I do not want the host to refuse retrieve, Web, or Forecast calls, so that Ouroboros remains the one who sequences tools.
20. As a user, I ask “What is OPEC's 2026 world oil demand outlook?” when that figure is in Sample Reports, so that the answer contains a grounded `[Отчёт …]`.
21. As a reviewer, I fail that dialogue if `[Отчёт …]` is missing or not backed by retrieve **this turn**, so that memory or a host insert cannot fake a Report.
22. As a user, I may also see `[Источник: …, web]` on that quiet demand question, so that a combined answer is allowed without “today”.
23. As a user, I do not care whether the prose leads with Reuters or MOMR, so that paragraph order is not an acceptance gate.
24. As a user, I ask something with no overlap in Sample Reports, so that the Analyst may use Web sources and still must not invent volumes.
25. As a user, I ask “What's the latest OPEC statement on output?”, so that Web sources can carry the fresh bit, tagged as web.
26. As a user, I ask “What's Brent today given OPEC demand?”, so that I can get both Report and Web tags.
27. As a user, I say “спрогнозируй цену Brent на 3 месяца”, so that the Forecast module can run and the answer tags `[Forecast …]`.
28. As a user, I say “Brent in 3 months” or “What's Brent?” without a Forecast verb, so that the model may still call Forecast; a verb is a prompt hint, not a host detector.
29. As a user, I want a Forecast that ran to show SARIMA and Holt–Winters, two intervals, no silent average, so that I see both methods.
30. As a user, I want a short interpretation next to those numbers, so that I know what the path assumes.
31. As a user, I leave the crude unnamed, so that Forecast defaults to Brent.
32. As a user, I name WTI, so that Forecast uses WTI.
33. As a user, I ask for Urals Forecast, so that the module says there is no series and does not proxy Brent.
34. As a user, I want Live quotes to come from Web sources when the Analyst seeks a spot price, not from invented prose, so that a Forecast is only a Forecast when the module ran.
35. As a user, I want no oil prices or volumes in prose that did not come from Reports, Web sources, or Forecast, so that the language model cannot hallucinate a strip.
36. As a user, I do not want kp.ru, dailymail.co.uk, or other Yellow-press denylist domains as citations, so that tabloids do not appear as sources.
37. As a user, I accept that the host does not strip those URLs from search hits, so that citing one is a prompt failure, not a missing filter.
38. As a user, I accept that unlisted tabloids can leak, so that I understand the denylist is not an allowlist.
39. As a user, I want Dropped chunks never cited, so that an off-topic tanker footnote cannot masquerade as the answer.
40. As a user, I do not want the host to un-drop chunks by heading keywords when Drop returned empty on a **live** model, so that Drop remains the model’s.
41. As a user, I do not want heading-rank dictionaries to reshuffle retrieve after e5 on a live reply, so that retrieval is not a second keyword agent.
42. As a user, I do not want an out-of-scope phrase list to decide Competence on a live classify, so that Competence stays the model’s.
43. As a user, I do not want a live answer without `[Отчёт …]` to be patched with chunk dumps, so that forgetting to cite is a prompt fail.
44. As a reviewer, I allow those helpers only as Safety nets (timeout, 500, empty completion), so that a dead model does not invent figures or crash the chat.
45. As a reviewer, I allow Route lists only as prompt/skill hints, so that they do not turn Forecast or Web on in the host.
46. As a user, I want Chunk metadata (title, date, page range, heading) preserved, so that citations are precise.
47. As a reviewer, I want Sample Reports in git, so that RAG works without ingest.
48. As a reviewer, I want missing Sample Reports to be a broken install, so that we do not ship an empty corpus.
49. As a reviewer, I want ingest that can fetch configured Full Reports (EIA STEO, OPEC MOMR), so that I can cite a real edition when the network works.
50. As a reviewer, I want Full Report ingest failure loud but non-fatal, so that Sample Reports still serve.
51. As a user, I want OPEC, EIA, and the CBR trends bulletin in the corpus, so that IEA login is not required.
52. As a user, I ask in Russian about oil demand, so that retrieval can still hit English Report Chunks and the Analyst answers in my language without inventing figures.
53. As a reviewer, I want multilingual-e5-base and Chroma in-process, so that there is no second embedding API and no Qdrant container.
54. As a reviewer, I want e5 passage/query prefixes, so that retrieval is not garbage.
55. As a reviewer, I want heading-then-512-token Chunks with overlap, so that MOMR/STEO/CBR sections cite cleanly.
56. As a reviewer, I want leftover text without a heading stored as untitled, so that appendices are not dropped.
57. As a reviewer, I want the five assignment dialogues in the README (Report, Web, combined, Forecast, Out-of-competence), so that I can replay them.
58. As a reviewer, I want README to say why OpenRouter GLM 5.2 free, Chainlit, Ouroboros, e5+Chroma, DuckDuckGo or equivalent Web, and statsmodels, plus limits (`:free` rate limits, denylist lag, Yahoo, sample ≠ full MOMR).
59. As a reviewer, I want thinking off on every Main call, so that demos do not wait on GLM chain-of-thought.
60. As a reviewer, I want Main pinned to `z-ai/glm-5.2:free` via OpenRouter, so that DeepSeek Flash and stock Grok are not the product chat.
61. As a reviewer, I want Heavy, skill-review, and Eval chat to default to Main if unset, so that Grok does not sneak in.
62. As a reviewer, I want those slots overridable in `.env`, so that I can pin a different Eval or review model without a code change.
63. As a reviewer, I want a missing OpenRouter key or a dead `:free` id to fail loudly, so that there is no silent fallback to DeepSeek or Grok.
64. As a reviewer, I want secrets and model ids only in `.env`, so that nothing secret is in git.
65. As a reviewer, I want Docker to persist Chroma and Full Reports on volumes, so that re-ingest is not required every start.
66. As a reviewer, I want the Ouroboros gateway allowed to stay off the published demo port, so that `:8000` remains the only click target.
67. As a user, I want yfinance (or the Forecast loader) failure to surface as uncertainty, so that a blocked Yahoo is not a fake CSV.
68. As a user, I want empty Web results to be uncertainty, not invented news, so that a down DuckDuckGo does not look like a source.
69. As a user, I want sanctions discussed only as they hit the oil market, so that the Analyst stays inside Competence.
70. As a reviewer, I want pytest on the Analyst turn with frozen tools, so that I can lock grounding and Safety-net behaviour without OpenRouter.
71. As a reviewer, I want a live Eval of the five dialogues against the running stack, so that mocked pytest is not mistaken for acceptance.
72. As a reviewer, I want Python 3.10+, so that the assignment language bar is met.
73. As a reviewer, I want a short README section on decisions, limits, and what more time would buy, so that the assignment’s written report exists.

## Implementation Decisions

- Conversation runtime is current-generation Ouroboros (solve-model tool loop). LangGraph is not what the reviewer talks to. Chainlit on port 8000 is the only acceptance Chat UI; it is an adapter into that loop. Desktop Ouroboros is not required. The Ouroboros web port need not be the demo URL; compose may keep it internal.
- Domain Report retrieve, Web search, and Forecast are reviewed **extension** tools in the same loop (instruction skill for playbook; `identity.md` overlay for the Analyst job). Do not import Ouroboros as a library node inside the old waterfall. Do not use Ouroboros as a silent judge of Chainlit strings. Do not rewrite BIBLE/SYSTEM into an oil constitution.
- The host must not refuse retrieve, Web, or Forecast because of Route lists, Competence classify, or “always retrieve k”. The model decides Competence, retrieve, Drop, Web, Forecast, stop, and order.
- Acceptance / Eval grade the visible reply plus grounding: corpus-covered questions need `[Отчёт …]` backed by retrieve this turn; extra Web beside that tag is fine, including without a freshness marker; paragraph order is not graded; denylist domains must not appear as citations (host does not strip hits); Out-of-competence extra tools are prompt failures, not missing locks; Forecast needs no verb; if the module ran, tag it and show two methods.
- Live-model stubs die: citation insert when a live reply lacks `[Отчёт …]`; out-of-scope dictionary as detector; restore-after-Drop; heading-rank after e5; Forecast-verb override of classify; Route lists as tool gates. Route lists may remain as prompt/skill hints. Safety nets (timeout / 500 / empty) may keep dictionary, keep-all Drop, citation append only if retrieve already ran, and canned uncertainty.
- Product contracts that stay: Yellow-press domain list; SARIMA + Holt–Winters never averaged; no Urals series; citation label grammar; Sample Reports; uncertainty on Yahoo or empty Web; e5 + Chroma; heading-then-512 Chunks; OPEC/EIA/CBR corpus; IEA out.
- Main slot: OpenRouter `z-ai/glm-5.2:free`, thinking off. Heavy / skill-review / Eval may differ via env; unset means Main. No silent vendor fallback.
- `/evolve` off for Demo and Eval. Task-acceptance Review, P3, and `/review` stay off the five dialogues. README must name Ouroboros, reviewed skills, Chainlit adapter, evolve off.
- Docker: one-command path to Chainlit 8000; `.env` / `.env.example` for keys; volumes for Chroma and Full Reports. Web search may use DuckDuckGo or Ouroboros’s search tool; denylist remains a citation contract, not a required host drop.
- ADR 0002 is not in force for this rebuild. ADR 0001’s loop (Analyst inside Ouroboros) is in force; ADR 0021 chooses Chainlit as the window. ADRs 0019–0024 bind this spec. ADR 0006 (DeepSeek Flash) is superseded for chat. ADR 0010 “LangGraph behind Chainlit” is superseded; Chainlit-as-shell remains.

## Testing Decisions

Good tests observe **external** Analyst behaviour: given a question (with frozen retrieve / Web / Forecast / model where the network would jitter), assert the visible reply, citation tags, and whether retrieve ran this turn when scoring `[Отчёт …]`. Do not assert Ouroboros node names, prompt text, Chroma internals, or frozen tool order. Do not require Reports-before-Web in the prose.

**Seam (one):** the Analyst turn — `question → reply` (text + citation tags + which of retrieve / Web / Forecast actually ran). Chainlit is an adapter over this seam; tests call the seam directly, not the browser. A second seam is not added for the Ouroboros SPA.

- Corpus-covered demand outlook: grounded `[Отчёт …]` (retrieve this turn); extra Web tags allowed; missing tag or tag without retrieve fails.
- Out-of-competence pin (weather): refusal, no invented numbers. Host must still allow tools; a test that the host blocked Web is a spec fail.
- Forecast when the module ran: two methods, intervals, no average; Urals → no series. No test that a missing verb forbids the tool.
- Denylist: kp.ru / dailymail must not appear in citations. No test that the host stripped the URL from raw hits.
- Live reply without `[Отчёт …]` must not be host-patched. Infra empty/timeout paths may use Safety nets; those tests must label the completion as non-live.
- Ingest remains not a product seam: Sample Reports are fixtures. Optional ingest tests: PDF in → Chunks with heading and page metadata out, through the same ingest the app uses.
- Live Eval (five README dialogues on the running stack) is not mocked pytest. It uses the Eval chat model from env (default Main). Pytest without live flags must not call OpenRouter.

Prior art: the existing Analyst-turn tests with frozen tools; they must be rewritten where they lock host gates, citation inserts on live compose, Route-list detectors, or “no tools on weather” as a runtime lock.

## Out of Scope

- Expanding Competence beyond oil and gas.
- IEA corpus; committing Full Report PDFs; Urals price history; Prophet, LSTM, factor regression, CSV fallback for prices.
- Replacing the Yellow-press denylist with an allowlist or an LLM journalism classifier.
- Host URL-stripping of denylist hits (rejected in 0019).
- DeepSeek Flash as product chat; silent fallback to Grok or DeepSeek.
- Ouroboros desktop as the acceptance UI; grader required to open `:8765`.
- Task-acceptance Review, P3, `/review` as part of the five dialogues; `/evolve` on Demo/Eval.
- Importing Ouroboros into the old LangGraph graph; using Ouroboros as a silent judge of Chainlit strings.
- Streamlit, Gradio, FastAPI UI; Tavily/SerpAPI/Google CSE as required search.
- Multi-user auth, production observability, rewriting BIBLE.md into an oil constitution.
- Executing this rebuild as part of the wayfinder map (this spec is the handoff).

## Further Notes

- Assignment title and customer comments require Ouroboros. TZ still lists LangChain/LangGraph; this spec follows the customer: Ouroboros is the agent, Chainlit is the shell.
- `:free` GLM rate limits are an accepted Demo risk. Document them.
- Compose may publish only 8000; that layout was left to the implementer as long as the click target is Chainlit.
- Instruction-skill vs `identity.md` wording is implementer work within 0001/0024: Analyst job overlay, not a second soul.
- Five demo prompts stay in README; expected checks follow 0019–0020 (grounded Report, optional extra Web, Forecast tags if the module ran, Out-of-competence refusal), not v1 tool-flag Eval from 0017.

Implementation tickets (ready-for-agent): [09](issues/09-chainlit-talks-to-ouroboros.md) is the frontier; [10](issues/10-grounded-report-retrieve.md)–[13](issues/13-competence-playbook-and-safety-nets.md) wait on 09; [14](issues/14-five-readme-dialogues.md) waits on 10–13.
