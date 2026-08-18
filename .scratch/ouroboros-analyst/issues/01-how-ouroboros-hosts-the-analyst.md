# How Ouroboros can host the Analyst

Type: research
Status: resolved

## Question

What is the supported way, in [razzant/ouroboros](https://github.com/razzant/ouroboros) (current generation, not the Colab archive), to ship a domain Analyst that:

- runs an LLM/tool loop where **the model** chooses which tools to call and when to stop,
- can be given domain tools (Report retrieval, Web search behind a denylist, a Forecast calculation module),
- presents a reviewer-facing conversation (desktop, headless CLI, Docker web runtime, or other),
- and can be started in a grader-friendly way (ideally one command, keys in `.env`)?

Answer with facts from Ouroboros docs (README, `docs/ARCHITECTURE.md`, skills/extensions, Docker, CLI), not a redesign of this repo. Call out what is **not** supported: treating Ouroboros as a pip library imported into the current LangGraph graph; hiding it as a silent judge of chat strings.

Also record: how skills vs built-in tools vs MCP differ; whether the agent already has web search (three paths in ARCHITECTURE); what Review / evolve would look like in a demo; and what a “role” or system prompt for a senior oil-and-gas Analyst would attach to (BIBLE/identity/skill/project room).

## Answer

Supported hosting shape: the reviewer talks to **current-generation Ouroboros itself** (v6.103.0 runtime — desktop, `:8765` web without PyWebView, or gateway CLI). A user message hits `OuroborosAgent`’s LLM/tool loop; **the solve model** picks tools and when to stop. Domain body is reviewed **extension** tools (`register_tool` → `ext_…` names in that same loop), not a second graph.

Facts that matter:

- **Surfaces:** native desktop (PyWebView); `ouroboros server` / Docker `ENTRYPOINT python server.py` (web SPA, no PyWebView); `ouroboros run --start` / `chat send` over the same gateway. Chat is the conversation; Projects are rooms of **one** identity.
- **Skills vs tools vs MCP:** built-ins are ToolRegistry (incl. `web_search`, browser). Skills are `instruction` (playbook, never executes), `script` (`skill_exec` subprocess), or `extension` (in-loop tools + optional widgets/routes). MCP is optional HTTP/SSE (`MCP_ENABLED` default off), names `mcp_<server>__<tool>`. Hub install still goes through review → grants → enable.
- **Web already exists, three paths:** (1) opt-in OpenRouter **main-loop** native search, default off; (2) `web_search` cascade OpenAI → OpenRouter → Anthropic → `ddgs` (can introduce a second LLM unless pinned `ddgs`); (3) Playwright browser tools. Hub `duckduckgo` is a fourth extension. **None carry a Yellow-press denylist.**
- **Role slot:** attach Analyst job to `data/memory/identity.md` (living manifesto, always in context) plus an `instruction` skill playbook. Project rooms hold corpus/thread, **not** a second soul. Settings “cognitive roles” are **model slots** (Main/Heavy/Light/…). Do **not** rewrite `BIBLE.md` / `SYSTEM.md` into an oil-and-gas constitution.
- **Review / evolve in a demo:** Skills-page review is the trust gate for domain tools. Task-acceptance Review is a post-delivery coach (skips ordinary read-only chat). `/review` is constitutional self-review. `/evolve` is self-mod, **hard-blocked in `runtime_mode=light`**, which still runs reviewed skills. Leave evolve off for a frozen Eval.
- **Grader start:** `docker run -p 8765:8765` (plus network password / trusted ingress) or `ouroboros server`. Keys live in `settings.json` or process env (`OPENROUTER_API_KEY`, OpenAI-compatible, GigaChat, …). Ouroboros has **no** documented `.env`+compose Analyst image — that would be a wrapper around this runtime.

**Not supported:** importing Ouroboros as a pip library into LangGraph; using it as a silent judge of Chainlit strings; commit-Review-on-a-file as a substitute for the loop; stock RAG/Forecast/Competence; stock denylisted web; a per-project Analyst identity; Colab-generation Telegram as the product.

Context: `.scratch/ouroboros-analyst/research/ouroboros-host.md`
