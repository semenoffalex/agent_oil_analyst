# How current-generation Ouroboros can host a domain Analyst

Context pointer for ticket `01-how-ouroboros-hosts-the-analyst`. Facts only, from razzant/ouroboros **current generation** (v6.103.0 on `main` / working branch `ouroboros`), not the Colab archive (`legacy-google-colab`).

Primary sources: [README](https://github.com/razzant/ouroboros/blob/main/README.md), [docs/ARCHITECTURE.md](https://github.com/razzant/ouroboros/blob/main/docs/ARCHITECTURE.md), [docs/CREATING_SKILLS.md](https://github.com/razzant/ouroboros/blob/main/docs/CREATING_SKILLS.md), [docs/DEPLOYMENT.md](https://github.com/razzant/ouroboros/blob/main/docs/DEPLOYMENT.md), [BIBLE.md](https://github.com/razzant/ouroboros/blob/main/BIBLE.md), [prompts/SYSTEM.md](https://github.com/razzant/ouroboros/blob/main/prompts/SYSTEM.md), [Dockerfile](https://github.com/razzant/ouroboros/blob/main/Dockerfile), [ouroboros/cli.py](https://github.com/razzant/ouroboros/blob/main/ouroboros/cli.py), [pyproject.toml](https://github.com/razzant/ouroboros/blob/main/pyproject.toml), [OuroborosHub README](https://github.com/razzant/OuroborosHub/blob/main/README.md).

This note does not redesign this repo.

---

## What Ouroboros is (and is not)

Ouroboros is a **self-hosted agent runtime**, not a library you drop into another graph.

- One identity continues across tasks and restarts. Durable data lives under `~/Ouroboros/data/` (settings, memory, skills, logs, task results). The self-modifying git checkout is `~/Ouroboros/repo/`.
- The agent core is `ouroboros/`, the reviewer-facing UI is `web/` (vanilla JS SPA), the process plane is `supervisor/`. A user message enters `server.py`, is queued by the supervisor, and runs inside `OuroborosAgent`.
- The public product surfaces are: **native desktop app**, **headless CLI over the same gateway**, and **Docker/source web runtime** (HTTP+WebSocket, default `127.0.0.1:8765`).
- `pyproject.toml` publishes console scripts `ouroboros` and `ouroboros-web`. `uv tool install "git+https://github.com/razzant/ouroboros.git@ouroboros"` installs those commands. That is a **CLI/server install**, not an embeddable `OuroborosAgent.invoke()` API for LangGraph.
- Frozen contracts (`ouroboros/contracts/`, `gateway/contracts.py`) exist so the host can evolve internally. They are not a documented “import me as a node” SDK.
- First generation (Colab + Telegram) is archived on `legacy-google-colab`. Do not use it.

**Not supported as a hosting shape:** `import ouroboros` into the current LangGraph waterfall; wrapping Ouroboros as a silent judge of Chainlit strings; writing each answer as a file and running only commit Review on that file.

---

## The model-driven loop (tool choice and stop)

ARCHITECTURE §6:

- The task pipeline builds context, runs the **LLM/tool loop**, stores results, emits progress, reflects, consolidates memory, and records review evidence.
- Public Tool API v2 names (`read_file`, `web_search`, `run_command`, extension tools, MCP tools, …) are offered as schemas. The **solve model** chooses which to call. There is no documented host waterfall that orders RAG → web → forecast.
- The loop stops when the model produces a final answer (no further tool calls), or when host rails fire: round cap (`OUROBOROS_MAX_ROUNDS`, default 200), idle timeout, absolute ceiling, deadline, budget, owner Cancel/Wrap-up, or (when enabled) task-acceptance Review iterating until clean/dialogue-terminal/lifecycle rail.
- `FINAL ANSWER:` latching exists for grader/benchmark contracts (`task_contract.answer_protocol="final_answer_line"`). Ordinary chat does **not** force that marker in the prompt; the web UI shows a `FINAL ANSWER:` line as ordinary text if the model emits one.
- Direct chat vs queued/headless: ordinary conversation and read-only tool use can skip task-acceptance Review. Queued/headless/scheduled substantive roots are reviewed when `task_review_mode` is `auto` or `required`.

Implication for a domain Analyst: tool **order** and **whether to stop** are model decisions inside this loop. A hardcoded classify→retrieve→drop→web→forecast graph is the opposite of this harness.

---

## Reviewer-facing conversation surfaces

All three talk to the **same** gateway (`POST /api/tasks`, chat history, WebSocket). There is not a second product UI.

| Surface | What the reviewer sees | How it starts |
|---|---|---|
| Native desktop | PyWebView window around the web runtime. Chat, Projects, Files, Skills, Widgets, Dashboard, Settings. First-run wizard. | Platform download (`.dmg` / `.zip` / `.deb` / `.rpm` / AppImage). Optional CLI installer from the same package. |
| Source / Docker **web runtime** | Same SPA in a browser at `:8765`. **No PyWebView.** Wizard is a blocking web overlay. | `ouroboros server` or `docker run … ouroboros-web`. Dockerfile `ENTRYPOINT ["python", "server.py"]`. |
| Headless CLI | Same managed tasks; progress on stderr; final answer (or JSON/JSONL) on stdout. Also `ouroboros chat send` / `chat history`. | `ouroboros run --start "…"` (starts a local server if attach fails). Packaged `run --start` launches the desktop launcher, not a bare `server.py`. |

Chat (`web/modules/chat.js`) is the owner conversation: history, attachments, live task cards (tools/progress collapsed, not transcript spam), Swarm / Low-Max / Send. Projects are **focused rooms** of the **same** identity (split panel), not a second agent.

Transport skills (bundled Telegram) can replace the local UI after review + grants. That is a first-class control surface, not a demo toy — usually wrong for a grader who expects a browser.

---

## Skills vs built-in tools vs MCP

### Built-in tools (ToolRegistry)

Canonical core tools live in `tool_capabilities.py` / Tool API v2. Always part of the parent envelope (subject to `disabled_tools`, resource policy, runtime mode, workspace allowlists). Examples: filesystem, shell, `web_search`, browser (`browse_page` / `browser_action`), `commit_reviewed`, `schedule_subagent`, `verify_and_record`, skill lifecycle tools (`list_skills`, `skill_exec`, `skill_review`, `toggle_skill`).

### Skills (three types)

Documented in CREATING_SKILLS.md. A skill is a reviewed package under `data/skills/{native,clawhub,ouroboroshub,external}/`.

| Type | Ships | Agent sees it as |
|---|---|---|
| `instruction` | Markdown-only `SKILL.md`. Never executes. | Playbook / prompt. `when_to_use` + body. Discovered via `list_skills`; not a callable tool. |
| `script` | `scripts/` + manifest. | `skill_exec` subprocess (cwd confinement, env scrub, timeout, runtime allowlist). |
| `extension` | `plugin.py` via PluginAPI. | `register_tool` → namespaced `ext_<len>_<token>_<name>` in the **same** tool loop; optional HTTP routes `/api/extensions/<skill>/…`, Widgets, Settings sections, companion processes. |

Lifecycle (every executable skill, including self-authored and Hub): `install → skill_review → isolated deps → owner enable → execute`. Review PASS alone is not enough: content hash, grants, enablement, deps, and extension load are separate gates. Owner may **attest** (skip LLM review) for external/self-authored or hash-verified official Hub payloads; deterministic preflight still runs; attested skills cannot be published to a public hub.

OuroborosHub is the official catalog ([razzant/OuroborosHub](https://github.com/razzant/OuroborosHub)). Desktop **Skills → OuroborosHub**, or CLI `ouroboros marketplace ouroboroshub install <slug>`. Current Hub examples: `weather`, `nanobanana`, `music_gen`, `video_gen`, `duckduckgo`, `perplexity`. Hub membership does **not** bypass review.

`OUROBOROS_SKILLS_REPO_PATH` can point at an extra on-disk skills repo (Settings). Dropping payloads into `data/skills/external/<name>/` is the user-authored path.

### MCP

Optional (`MCP_ENABLED` default false). HTTP/SSE servers from Settings (`MCP_SERVERS`). Discovered tools join the initial capability envelope as `mcp_<server>__<tool>`. Failures are reported as an omission manifest, not silent hide. Still go through safety. This is for **already-running MCP servers**, not for in-process Python modules.

**Where domain Analyst tools belong (supported, not a redesign):**

- Report retrieval, denylisted web, Forecast calculator: **`type: extension` tools** (same loop, model-chosen), or **script** skills if they are batch/subprocess work. Isolated `pip` deps are supported after review.
- A Competence / Analyst **playbook**: `type: instruction` skill and/or `identity.md` (see Role).
- An existing MCP server wrapping the same modules: possible, extra process, Settings-configured, off by default.
- Folding them into Ouroboros **core** ToolRegistry: possible only by modifying Ouroboros itself (reviewed self-mod / fork). That is self-creation, not the extension seam.

---

## Web search: three paths (do not conflate)

ARCHITECTURE §6 “Web access mechanisms”:

1. **Main-loop native search** (`OUROBOROS_MAIN_WEB_SEARCH=openrouter`, default **off**). Injects OpenRouter’s server tool into the **solve** request. Same model decides when to search. No second LLM. Citations harvested into usage; reviewer sees a host-attested retrieval fact. Must be disclosed on fixed-model benches.
2. **`web_search` function tool** (ToolRegistry). Backend cascade: official OpenAI Responses → OpenRouter `openrouter:web_search` → Anthropic `web_search_20250305` → `ddgs`. First three call a **separate** model (`OUROBOROS_WEBSEARCH_MODEL`, default `gpt-5.2`) unless pinned. `ddgs` is keyless, no second LLM, weaker. `OUROBOROS_WEBSEARCH_BACKEND=ddgs` pins pure retrieval. Missing credentials → explicit unavailable-backends JSON, not fake success.
3. **Browser tools** (`browse_page` / `browser_action`, Playwright). Fetch arbitrary URLs locally. Chromium default; WebKit bundled on Linux/Docker/Windows.

Hub skill `duckduckgo` is a **fourth** surface: an **extension** tool `ext_…_duckduckgo_search` plus a Widgets form. Manifest `when_to_use`: “no OpenAI key is available for web_search”. Connects to DuckDuckGo only. **No domain denylist.**

**None of these implement a Yellow-press denylist.** Stock `web_search` / Hub `duckduckgo` / browser fetch can cite any domain they return. A denylist is domain product logic: it has to live in a **custom** extension (or a wrapper around `ddgs`/browser that drops listed hosts before the model sees URLs). Using path (1) or unfiltered path (2)/(3) as the Analyst’s Web source **cannot** enforce that list.

`ddgs` is already a runtime dependency of Ouroboros (`pyproject.toml`). Pinning `OUROBOROS_WEBSEARCH_BACKEND=ddgs` avoids a second search LLM; it still has no denylist.

---

## Role / system prompt: where a senior oil-and-gas Analyst attaches

Ouroboros is **one** awareness, one constitution, one evolution (BIBLE P1; SYSTEM.md “Projects”). There is **no per-project identity**.

| Slot | What it is | Fit for Analyst role |
|---|---|---|
| `BIBLE.md` | Constitutional SSOT. “Who Ouroboros is.” Never truncated. Changes only via reviewed release. | **Do not replace** with an oil-and-gas constitution. Fights Principle 0 (becoming personality, not a useful bot) and Ship-of-Theseus protection. |
| `prompts/SYSTEM.md` | In-loop “I Am Ouroboros” doctrine, tool/delegation teaching. | Core harness prompt. Editing it is self-mod of Ouroboros, not a domain overlay. |
| `data/memory/identity.md` | Living self-description. Always in context, never truncated. Mutable via `update_identity`. File must exist; content may be rewritten. Reflection may propose identity updates but does **not** auto-write them. | **Supported overlay** for “I work as a senior oil-and-gas market Analyst …” **on top of** still being Ouroboros. Not a second soul. |
| Instruction skill | Markdown playbook, `when_to_use`, never executes. | **Supported** Competence/citation/Forecast-verb playbook the model can load. Does not by itself register tools. |
| Project room | Focused thread + journal/workpad/knowledge + optional working folder. One writer per project. | **Supported working context** (corpus path, Eval dialogues, Reports folder). Does **not** carry a separate Analyst identity. |
| Settings “cognitive roles” | **Model slots**: Main / Heavy / Light / Vision / Consciousness (`OUROBOROS_MODEL*`). | Provider/lane routing. **Not** a job title. |
| Subagent `role=` | Optional string on `schedule_subagent`. | Swarm specialist label. Child is still Ouroboros under a capability envelope. |
| Task contract | `objective`, `expected_output`, `disabled_tools`, `answer_protocol`, resource policy. | Per-task constraints (Eval/grader), not the standing persona. |

A domain Analyst that **is** the Ouroboros instance: reviewer talks to Chat; identity.md + instruction skill state the Analyst job; extension tools are the domain body; BIBLE/SYSTEM stay Ouroboros.

---

## Review and `/evolve` on a demo path

These are distinct systems. Do not collapse them.

**Skill review** — trust gate before domain tools run. Reviewer can see Skills cards, PASS/owner-attested badges, grants. For a demo, owner attestation or `OUROBOROS_AUTO_GRANT_REVIEWED_SKILLS` (default on) plus a pre-reviewed payload avoids a multi-model skill-review bill at first click.

**Task-acceptance Review** — post-delivery coach on queued/headless work (and effectful chat). Independent reviewer slots, adaptive quorum. `off` / `auto` / `required`. Blocking mode can iterate the agent. Ordinary read-only research chat is skipped. Useful if a grader wants a visible “did it actually answer?” panel; expensive and not the assignment’s five dialogues.

**P3 commit Review** (advisory + triad + scope on `commit_reviewed`) — immune system for **self-mod**. Only fires if Ouroboros commits to its own repo. A domain-tool-only demo that never mutates Ouroboros will not show this unless you deliberately open Evolution or edit the harness.

**`/review`** (slash command) — queues a deep constitutional/architectural **self-review** (`deep_self_review.py`), not a grade of the user’s oil question.

**`/evolve`** — autonomous Evolution Campaigns that rewrite Ouroboros (code, prompts, tools). Default owner-gated; **hard-blocked in `runtime_mode=light`**. Post-task self-evolution is default **OFF**. A grader demo that leaves evolve on can rewrite the Analyst away.

**Demo-shaped defaults (facts, not a spec):** `OUROBOROS_RUNTIME_MODE=light` still runs reviewed skills and user-file work, and blocks self-repo mutation / evolve. Task acceptance can stay `off` or `auto`. Dashboard Logs still show tool/LLM cards so a reviewer can see the model chose tools. Skills page shows the domain extensions. Chat is the conversation.

---

## Grader-friendly start

Stock Ouroboros **does** have one-command shapes. It does **not** ship a `.env` convention as the settings SSOT.

**Keys / models**

- SSOT is `~/Ouroboros/data/settings.json` (file-locked). `load_settings` / `apply_settings_to_env` copy keys into the process env.
- First-run wizard appears when settings have **no** supported remote key and no `LOCAL_MODEL_SOURCE`. Desktop and web share the same wizard. Closing it is non-fatal; Settings can finish later.
- Supported providers include OpenRouter, official OpenAI, OpenAI-compatible (base URL + key, **no guessed model IDs**), Anthropic, Cloud.ru, GigaChat, local GGUF. Default Main model is `x-ai/grok-4.5` (OpenRouter). A DeepSeek-only product would be an OpenAI-compatible (or OpenRouter) **slot pin**, not a built-in DeepSeek product.
- Docker/K8s non-loopback bind: `OUROBOROS_SERVER_HOST=0.0.0.0` (Dockerfile default). Saving that via Settings UI requires `OUROBOROS_NETWORK_PASSWORD` unless `OUROBOROS_TRUST_NONLOCAL_BIND_WITHOUT_PASSWORD=1` (DEPLOYMENT.md; only behind ingress/VPN). Dockerfile does not set a password; README’s `docker run` example does.

**Documented one-command starts**

```bash
# Source (browser UI, no desktop shell)
ouroboros server
# then http://127.0.0.1:8765

# Headless task (CI / another agent)
ouroboros run --start "2+2?"

# Docker web runtime (no PyWebView)
docker build -t ouroboros-web .
docker run --rm -p 8765:8765 \
  -e OUROBOROS_NETWORK_PASSWORD='choose-a-password' \
  -e OUROBOROS_FILE_BROWSER_DEFAULT=/workspace \
  -v "$PWD:/workspace" \
  ouroboros-web
```

Passing provider keys as `-e OPENROUTER_API_KEY=…` (or writing `settings.json` on a mounted data volume) is how a grader avoids the wizard. There is **no** documented `docker compose` + `.env` file in the Ouroboros repo; that would be **this** product’s wrapper around the image, not an Ouroboros built-in.

`OUROBOROS_FILE_BROWSER_DEFAULT` is required for Docker/non-localhost Files tab. Host Service port `8767` must **not** be published.

A grader-friendly Analyst demo that is still “inside Ouroboros” is: one Docker (or `ouroboros server`) command, keys in the process environment or a mounted settings file, browser to `:8765` Chat, domain extensions already in `data/skills/external` and enabled. Stock image alone is a **general** Ouroboros, not an oil-and-gas Analyst.

---

## Runtime mode vs product sandbox

`OUROBOROS_RUNTIME_MODE` is a **self-modification boundary**, not an OS sandbox (`light` / `advanced` / `pro`). Light blocks Ouroboros repo/control-plane mutation; user-file writes, task drive, artifacts, and **reviewed skills still run**. Workspace mode is a tool-routing / blast-radius guard; absolute host paths are not a hard security boundary unless an executor (`docker_exec`) is added.

For a domain Analyst that must not rewrite the harness during Eval: `light` is the documented mode.

---

## Mapping domain tools (facts for later tickets)

Not a design. Just what the host actually offers:

| Domain need | Stock Ouroboros | Supported attachment |
|---|---|---|
| Model chooses tools / stop | Yes — main loop | Do not reintroduce a LangGraph waterfall as the user-facing runtime |
| Report retrieval | No RAG/Chroma built-in | Extension `register_tool` (or script) over a corpus the skill can see (`user_files`, project working folder, or skill state) |
| Web + Yellow-press denylist | Three web paths; **no denylist** | Custom extension that searches then drops listed domains; do not call stock `web_search` if the list must hold |
| Forecast module | No statsmodels/yfinance tool | Extension or script with isolated deps; model chooses when to call it (instruction skill can *advise* Forecast verbs; the host will not enforce them unless the tool itself refuses) |
| Reviewer chat | Desktop / `:8765` / CLI | Same gateway; Chainlit is not an Ouroboros surface |
| One-command + keys | Docker / `ouroboros server` / `run --start` | Env or `settings.json`; `.env` is this repo’s convention, not Ouroboros’s |
| Visible Review | Skills review, optional task acceptance, `/review`, Dashboard | Evolve is optional and blocked in light |
| Analyst persona | One identity | `identity.md` + instruction skill; not BIBLE; not a project-only soul |

Host-enforced Forecast-verb / Competence gates would be **tool implementation or task-contract `disabled_tools`**, not a second graph. The loop will still let the model *attempt* other tools unless those tools refuse or are disabled.

---

## What is not supported

- Treating current-generation Ouroboros as a pip library imported into LangGraph.
- Hiding it as a silent judge of chat strings (or of a Chainlit transcript).
- Using only P3 commit Review on an answer file as a substitute for the agent loop.
- A second isolated Analyst mind (no per-project identity; BIBLE/SYSTEM stay Ouroboros).
- Replacing `BIBLE.md` / `SYSTEM.md` with a domain constitution as the “supported role slot”.
- Stock web search that honors a Yellow-press denylist.
- Stock RAG / Forecast / Competence classify.
- A documented `.env` + compose one-liner that boots an oil-and-gas Analyst (stock Docker boots **Ouroboros**).
- Turning off the model’s tool choice while still claiming “this is an Ouroboros agent loop”.
- Expecting `/evolve` to be part of a frozen grader demo (`light` blocks it; leaving `advanced`+evolve on is self-mod).
- Publishing Host Service (`8767`) or running Docker without a network password / trusted ingress.
- Colab/Telegram first generation as the product runtime.

---

## Source pins

- Generation: README v6.103.0 (2026-08-16). ARCHITECTURE header still says “v6.87.5” in places; treat README/VERSION as the release pin. Working branch for `uv tool install` is `ouroboros`; `main` is protected from self-mod.
- Default bind: `OUROBOROS_SERVER_HOST=127.0.0.1` in settings; Dockerfile overrides to `0.0.0.0`.
- Desktop extra: `pywebview` is an optional `[desktop]` extra. Docker/web path does not use it.
