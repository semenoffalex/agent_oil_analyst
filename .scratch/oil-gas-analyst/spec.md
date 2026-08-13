Status: ready-for-agent

# Spec: Oil and Gas Analyst

## Problem Statement

A reviewer (or any user) needs a senior oil-and-gas market Analyst they can open in a browser after one Docker command. The Analyst must answer industry questions with cited Reports first, reach Web sources only under the agreed waterfall, run a Forecast module on explicit Forecast requests, and refuse Out-of-competence questions without inventing numbers. The assignment also requires five scripted dialogues (Report-only, web, combined, Forecast, out of competence), a README that explains the stack, and no second runtime.

## Solution

The user talks to the Analyst in Chainlit. LangGraph runs the turn: Competence classify, Route lists, retrieve k=5 Chunks, Drop irrelevant Chunks, optionally DuckDuckGo behind the Yellow-press denylist, optionally the Forecast module. Every claim in the reply is tagged as Report, Web source, or Forecast. Sample Reports ship in git so retrieval works offline; an ingest step can pull Full Reports.

## User Stories

1. As a reviewer, I want to copy `.env.example` to `.env`, set `DEEPSEEK_API_KEY`, and run one Docker command, so that the Analyst UI is on port 8000.
2. As a reviewer, I want Chainlit chat, so that I do not need a custom frontend.
3. As a user, I want the Analyst to speak as a senior oil-and-gas market analyst (upstream, midstream, downstream, Brent/WTI/Urals, OPEC+, sanctions as they hit the market, supply and demand), so that answers match the role.
4. As a user, I want structured answers with figures, so that I can reuse them.
5. As a user, I want every material claim tagged with origin, so that I can tell Report from Web source from Forecast.
6. As a user, I want Report citations to include title, date if known, page range, and “excerpt” when the Chunk came from a Sample Report, so that I am not told a sample is a Full Report.
7. As a user, I want Web source citations to include outlet and that it is web, so that I can judge freshness and quality.
8. As a user, I want the Analyst to say when it does not know, so that I never get invented figures.
9. As a user, I ask an Out-of-competence question (weather, Python, World Cup, uranium), so that I get a refusal and no tools.
10. As a user, I ask an Out-of-competence question that also has a Time-sensitive marker (“what’s the weather today?”), so that Competence still wins and there is no web call.
11. As a user, I ask an in-Competence question, so that the turn continues past classify.
12. As a reviewer, I want Competence to be one in/out classify call on `deepseek-v4-flash` with thinking off, so that routing is not a keyword list for this gate.
13. As a reviewer, I want that classify call not to decide Forecast vs web, so that Route lists stay in charge of those two.
14. As a user, I say “спрогнозируй цену Brent на 3 месяца”, so that the Forecast module runs.
15. As a user, I say “predict WTI range” / “what if OPEC cuts” / “оцени диапазон”, so that those Forecast verbs hit the same module.
16. As a user, I say “What’s Brent?” or “Where is Brent headed?” or “Brent in 3 months” with no Forecast verb, so that Forecast does not run.
17. As a user, I ask a Time-sensitive in-Competence question (“Brent today”, “latest OPEC statement”), so that DuckDuckGo runs after Report retrieval.
18. As a user, I ask an in-Competence question with no Time-sensitive marker, so that web does not run unless every Retrieved chunk is Dropped.
19. As a user, I ask something in Competence that does not overlap Sample Reports, so that all Chunks are Dropped and one web call fills the gap.
20. As a user, I ask a Report-covered question (world oil demand 2026 from the MOMR excerpt), so that the answer cites that Report and need not use web.
21. As a user, I ask a Time-sensitive question that also has Report overlap, so that I get a combined answer: Reports for the structural claim, Web sources for the fresh bit, each tagged.
22. As a user, I do not want tabloid domains from the Yellow-press denylist in citations, so that kp.ru / dailymail.co.uk and the rest of the list never appear as Web sources.
23. As a user, I accept that unlisted tabloids can leak, so that I understand the denylist is not an allowlist.
24. As a user, I want Retrieved chunks always k=5 on in-Competence turns, so that Reports are always consulted first.
25. As a user, I want Dropped chunks never cited, so that a MOMR footnote cannot masquerade as an answer.
26. As a user, I want Chunk metadata (title, date, page range, heading) preserved, so that citations are precise.
27. As a reviewer, I want Sample Reports present without ingest, so that Docker on a dark network still has RAG.
28. As a reviewer, I want an ingest command that fetches the latest EIA STEO and the configured OPEC MOMR PDF into Full Reports, so that I can cite a real edition when the network works.
29. As a reviewer, I want ingest failure on Full Reports to be loud but non-fatal, so that Sample Reports still serve.
30. As a reviewer, I want missing Sample Reports to be a broken install, so that we do not ship an empty corpus.
31. As a user, I want OPEC + EIA English only in v1, so that I do not depend on IEA login.
32. As a user, I ask in Russian about oil demand, so that e5 still retrieves English Report Chunks or web, and the Analyst can answer in the user’s language without inventing figures.
33. As a user, I want a Forecast on Brent by default, so that an unspecified crude is BZ=F.
34. As a user, I name WTI, so that the Forecast uses CL=F.
35. As a user, I ask for an Urals Forecast, so that the module says there is no series and does not proxy.
36. As a user, I want both SARIMA and Holt–Winters on a Forecast request, so that I see two methods and two intervals, not a silent average.
37. As a user, I want a short interpretation next to the Forecast numbers, so that I know what the path assumes.
38. As a user, I want yfinance failure to surface as uncertainty, so that a blocked Yahoo is not replaced by a fake CSV.
39. As a user, I want Live quotes to come from Web sources on Time-sensitive price questions, not from the Forecast module.
40. As a reviewer, I want thinking mode off on every Flash call, so that demos do not wait on chain-of-thought.
41. As a reviewer, I want one chat vendor (DeepSeek), so that OpenAI/GigaChat are not silent fallbacks.
42. As a reviewer, I want embeddings via multilingual-e5-base and Chroma in-process, so that there is no second embedding API and no Qdrant container.
43. As a reviewer, I want E5 passage/query prefixes applied, so that retrieval is not garbage.
44. As a reviewer, I want heading-then-512-token Chunks, so that MOMR/STEO sections cite cleanly.
45. As a reviewer, I want leftover text without a heading stored as untitled, so that appendices are not dropped on the floor.
46. As a reviewer, I want Route lists in config, unit-testable without a model, so that “прогноз” hits Forecast and “headed” does not.
47. As a reviewer, I want the five assignment dialogues documented, so that I can replay Report-only, web, combined, Forecast, and out of competence.
48. As a reviewer, I want a README that says why DeepSeek Flash, Chainlit, e5+Chroma, DuckDuckGo, and statsmodels, plus limits (denylist lag, Yahoo, classify jitter, sample ≠ full MOMR).
49. As a user, I want no invented oil prices in prose when the Forecast module did not run, so that the language model cannot hallucinate a strip.
50. As a reviewer, I want Docker to persist Chroma and Full Reports on volumes, so that re-ingest is not required every start.
51. As a user, I want sanctions discussed only as they affect the oil market, so that the Analyst stays inside Competence.
52. As a reviewer, I want keys and model id only in `.env`, so that nothing secret is in git.

## Implementation Decisions

- One user-facing surface: Chainlit. LangGraph is the Analyst runtime behind it. No Streamlit, Gradio, or parallel HTTP UI.
- Chat LLM: `deepseek-v4-flash` at DeepSeek’s OpenAI-compatible API. Thinking disabled on every call. No fallback vendor. No `deepseek-v4-pro`.
- Turn order: Competence classify (`in`/`out`, structured) → if `out`, refuse and stop → Route lists (Forecast verbs, Time-sensitive markers) → retrieve k=5 Chunks → model may Drop Chunks → Forecast tool only on Forecast request → web only if (Time-sensitive and in Competence) or (all Chunks Dropped and in Competence) → compose tagged answer.
- Route lists stay closed EN+RU lists in config. A miss is a miss. Classify must not override them.
- Report store: multilingual-e5-base + Chroma in-process, persisted on a volume. Ingest: heading regexes per agency, then 512-token cap with 50-token overlap on the e5 tokenizer. Metadata: title, date, page range, heading.
- Sample Reports: OPEC MOMR March 2026 World Oil Demand excerpt; EIA STEO August 2026 Global Oil Markets excerpt. Full Reports: ingest fetches EIA STEO latest PDF and the configured OPEC MOMR URL. IEA out of v1.
- Web: DuckDuckGo, then drop URLs whose domain is on the Yellow-press denylist. No Tavily/SerpAPI. No LLM journalism classifier.
- Forecast module: yfinance history; SARIMA and Holt–Winters (statsmodels); both always run; do not average; default Brent; WTI if named; Urals = no series; on Yahoo failure, error and the Analyst reports uncertainty.
- Citations in the composed answer must distinguish Report vs Web source vs Forecast in the spirit of `[Отчёт OPEC MOMR, …]` vs `[Источник: …, web]`.
- Docker: one compose service, Chainlit on 8000, `.env` for secrets. First working `CMD` is Chainlit once the app exists.
- Ouroboros is out of scope for build and demo (ADR 0002). ADR 0001 is superseded.

## Testing Decisions

Good tests observe only the Analyst turn: given a question (and a frozen retriever / web / Forecast / classifier where the network would jitter), assert the visible reply and which tools were allowed to run. Do not assert graph node names, prompt text, or Chroma internals.

**Seam (one):** the Analyst turn — `question → reply` (text + citation tags + which of retrieve / web / Forecast ran). Chainlit is an adapter over this seam; tests call the seam directly, not the browser.

- Competence `out`: no retrieve, no web, no Forecast; refusal; no invented numbers. Include “what’s the weather today?”.
- Forecast verbs vs near-misses: “спрогнозируй Brent” runs Forecast; “What’s Brent?” and “Brent in 3 months” do not.
- Time-sensitive in Competence: web runs; denylist domains absent from citations.
- All Chunks Dropped + in Competence: exactly one web call.
- Report-covered demand question: at least one Report citation; sample citations say excerpt.
- Combined Time-sensitive + Report overlap: both Report and Web source tags present.
- Forecast request: reply contains two methods, intervals, and no silent average; Urals request does not invent a series.
- Route lists: pure tests on the matcher with no LLM (phrases from config).
- Ingest is not a second product seam: Sample Reports are fixtures for Analyst tests. Optional ingest tests only if they stay at “PDF in → Chunks with heading and page metadata out,” still through the same ingest function the app uses.

No prior test suite exists in this repo.

## Out of Scope

- Ouroboros (any generation, Colab, desktop, review-before-commit).
- IEA corpus; Russian Sample Reports; committing Full Report PDFs.
- Prophet, LSTM, factor regression, CSV fallback for prices.
- OpenAI/GigaChat/Claude/Ollama chat; thinking mode; `deepseek-v4-pro`.
- Tavily, SerpAPI, Google CSE; domain allowlist; LLM yellow-press classifier.
- Qdrant, FAISS, OpenAI embeddings.
- Streamlit, Gradio, FastAPI UI, curl as a first-class demo.
- Urals price history; averaging the two Forecast methods.
- A planner that may call web whenever it wants.
- Using Competence classify to detect Forecast requests or Time-sensitive questions.
- Multi-user auth, persistence of chat beyond Chainlit session, production observability.

## Further Notes

- Assignment title mentioned Ouroboros; ADR 0002 drops it. README should say that in one line so graders are not surprised.
- Competence classify can jitter: pin out-of-competence demos to weather, Python, World Cup, uranium.
- DuckDuckGo and yfinance can fail in Docker; those paths must look like uncertainty, not crashes with stack traces in chat.
- Heading regexes will miss some STEO boxes; untitled Chunks are expected.
- Five demo scripts should live in the README and must use a Forecast verb for the Forecast dialogue.
