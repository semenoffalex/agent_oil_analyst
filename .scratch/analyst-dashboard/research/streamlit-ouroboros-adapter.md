# Streamlit as thin adapter over the same Analyst turn

Ticket: [07-how-streamlit-calls-ouroboros.md](../issues/07-how-streamlit-calls-ouroboros.md)  
Sources: `oil_gas_analyst/{app,deps,ouroboros,turn,rate_limit}.py`, `Dockerfile`, `docker-compose.yml`, ADRs [0010](../../../docs/adr/0010-chainlit-ui.md), [0021](../../../docs/adr/0021-chainlit-adapter-ouroboros-loop.md), glossary in `CONTEXT.md`.

## Verdict

Streamlit can be a **Chat UI** adapter over the **same** Analyst turn Chainlit uses today: warm once with `build_loop()` → per message `run_turn(question, loop)` → `OuroborosLoop.complete` → `POST /api/tasks` (poll until terminal). That is **not** a second agent loop. Reopening [0021](../../../docs/adr/0021-chainlit-adapter-ouroboros-loop.md) means Streamlit **becomes** the Chat UI; the Analyst stays inside Ouroboros; the Demo remains “one browser URL after one compose command” unless a later ticket splits Demo vs Dashboard.

---

## Exact Chainlit warm / attest / toggle path

### Process start (warm)

In `oil_gas_analyst/app.py`:

1. Module import starts a daemon thread `warm-ouroboros` that calls `_warm()`.
2. `_warm()` calls `build_loop()` from `deps.py`, stores the `OuroborosLoop` in module globals `_LOOP` / `_ERR`, then sets `_READY`.
3. `_wait_loop()` blocks up to **60s** on `_READY`; raises on timeout, warm error, or missing loop.
4. `@cl.on_chat_start` shows “Connecting…”, then `asyncio.to_thread(_wait_loop)`, then a ready message (or startup failure text). No Analyst turn runs at chat start.

### `build_loop()` (attest + toggle + client)

In `oil_gas_analyst/deps.py` → `build_loop()`:

1. `require_openrouter_key()` — missing key fails loudly.
2. Read `OUROBOROS_URL` (default `http://127.0.0.1:8765`) and `OUROBOROS_TURN_TIMEOUT_SEC` (default `900`).
3. `enable_domain_skills(url)` — **before** constructing the loop.
4. Return `OuroborosLoop(url, timeout_sec=timeout)`.

### Skill attest / toggle (exact HTTP)

`enable_domain_skills(base_url)` POSTs JSON for each of:

- `oil_gas_analyst`
- `oil_gas_retrieve`
- `oil_gas_web`
- `oil_gas_forecast`

For each name, in order:

| Step | Method | Path | Body |
|------|--------|------|------|
| Attest | `POST` | `{base}/api/owner/skills/{name}/attest-review` | `{}` |
| Enable | `POST` | `{api}/skills/{name}/toggle` | `{"enabled": true}` |

Failures print; HTTP **409** is treated as “already attested”. There is **no** silent LangGraph fallback if enable fails (ADR 0021 / deps docstring).

### Per-message Analyst turn

`@cl.on_message`:

1. Optional Demo rate limit (`load_rate_limit_config` / `RateLimiter` / `client_key`).
2. `_wait_loop()` again (reuse warmed loop).
3. `run_turn(message.content, loop)` in a thread.
4. Render with `format_reply` (citation links + Sources + `footer_flags`).

### Turn → gateway (the only agent loop)

`turn.run_turn` → `loop.complete(question)` (`AnalystLoop` protocol).

`OuroborosLoop.complete` (`ouroboros.py`):

1. `POST /api/tasks` with body roughly:
   - `description`: question
   - `metadata`: `{"source": "chainlit", "delegation_role": "chat"}`
   - `source`: `"chainlit"`
2. Poll `GET /api/tasks/{task_id}` until status ∈ `{completed, failed, cancelled, canceled, error, degraded}` or `timeout_sec` elapses.
3. Map result text + tool-ran heuristics + citation regexes into `LoopResult`.
4. `run_turn` wraps that in `Reply`; on `TimeoutError` / `LoopError` only, applies Safety-net `_safety_net` (out-of-scope refuse vs infra text). Live completions are not host-refused or citation-patched.

Compose sets `OUROBOROS_TASK_REVIEW_MODE=off` on the `ouroboros` service so queued tasks skip task-acceptance Review.

---

## What Streamlit should call (same Python vs HTTP-only)

### Recommended: same Python functions (thin adapter)

| Concern | Call | Notes |
|--------|------|--------|
| Warm / attest / toggle | `build_loop()` once | Same attest/toggle side effects; one shared `OuroborosLoop` |
| Analyst turn | `run_turn(question, loop)` | Public seam; Eval / Demo share this |
| Optional render | `apply_citation_links`, `markdown_cite`, `footer_flags` | Chainlit-specific today only in `format_reply` wrapping |
| Rate limit | `load_rate_limit_config`, `RateLimiter`, adapted `client_key` | See session section |

Do **not** import Ouroboros agent core; do **not** reintroduce LangGraph as conversation path (`graph.py` / `invoke_analyst` is not the Demo seam).

### HTTP-only alternative (worse for this repo)

A Streamlit process could POST/GET `/api/tasks` itself and reimplement skill enable. That duplicates `OuroborosLoop` + Safety nets and drifts from Eval (`build_eval_deps` → `build_loop`). Prefer in-process `build_loop` + `run_turn`.

### Metadata label

`OuroborosLoop.complete` hardcodes `source: "chainlit"`. If Streamlit becomes Chat UI, either leave the string (gateway metadata only) or parameterize later — **not** a second loop.

---

## Session, timeout, and rate-limit hooks

### Session

| | Chainlit today | Streamlit adapter |
|--|----------------|-------------------|
| Conversation store | Chainlit session / message history in the UI | `st.session_state` for chat history |
| Loop singleton | Process-global `_LOOP` after warm thread | Same pattern: warm once at import or first request; stash in `st.session_state` only if you need per-session loops (usually **not** — one gateway client per process is enough) |
| Rate-limit key | `client_key(session.environ, session.id)` — prefer IP, else `session:{id}` | No Socket.IO `environ`. Prefer request headers / Streamlit’s client IP helpers if available; else `session:{st.session_state id}` or a stable uuid in session state |
| Chat start | `@cl.on_chat_start` waits for warm only | Map “session start”: warm wait + optional Dashboard Session-start Web (ticket 02) — **host** fetch, not a second Analyst loop |

Ouroboros does **not** get Chainlit/Streamlit transcript as multi-turn memory via this adapter: each user message is one `description` on a new task. UI history is display-only unless a later ADR adds memory.

### Timeout

| Knob | Where | Default |
|------|-------|---------|
| Warm wait | `_wait_loop` | 60s |
| Skill enable HTTP | `urlopen(..., timeout=30)` | 30s |
| Turn + poll | `OUROBOROS_TURN_TIMEOUT_SEC` → `OuroborosLoop.timeout_sec` | 900s |
| Per-request urlopen | `max(30, timeout_sec)` | same as turn |
| 503 “supervisor starting” | retried until turn deadline | poll interval 1s |

Streamlit turns are **blocking** on `run_turn` (same as Chainlit’s `to_thread`). Long turns need UI feedback (`st.spinner` / status) so the browser does not look hung; do not shorten the gateway timeout without product agreement.

### Rate limit (Demo)

ADR 0017: Demo has no password; spend gate is rate limit. Implemented in `rate_limit.py`:

- Env: `DEMO_RATE_LIMIT_MAX`, `DEMO_RATE_LIMIT_WINDOW_SEC` (max `0` → disabled).
- In-memory sliding window **per process**.
- Chainlit hook: only in `@cl.on_message` before `run_turn`.

Streamlit Chat UI should call the same limiter before `run_turn`. Caveats: multi-worker / multi-replica does not share the deque; two UIs in one image → two processes → **separate** counters unless moved behind a shared store (out of scope here).

---

## Compose CMD / port 8000 if Streamlit replaces Chainlit

### Current shape

- **`ouroboros` service**: gateway, health on `:8765`, `expose` only (not the Demo URL).
- **`analyst` service**: build from root `Dockerfile`, `ports: "8000:8000"`, `OUROBOROS_URL=http://ouroboros:8765`, depends on healthy ouroboros.
- **`Dockerfile`**: `CMD ["chainlit", "run", "oil_gas_analyst/app.py", "--host", "0.0.0.0", "--port", "8000", "--headless"]`; `EXPOSE 8000`; `CHAINLIT_*` env.

### Implications of replace

Per map grilling and ticket 03: Streamlit **replaces** Chainlit as the click target; README / Demo URL stay **`localhost:8000`** (glossary Demo + Chat UI).

1. Change `CMD` to something like `streamlit run … --server.port 8000 --server.address 0.0.0.0` (exact entry module TBD by implementers — not this ticket).
2. Keep compose port mapping `8000:8000` so ADR 0021’s “reviewer opens `:8000`” still holds with a new Chat UI library.
3. `requirements-analyst.txt` today pins `chainlit` only — add `streamlit`, drop or keep Chainlit only if both stay (see risks).
4. Env: drop or ignore `CHAINLIT_*`; Streamlit uses its own server env. Keep `OUROBOROS_URL` / `OUROBOROS_TURN_TIMEOUT_SEC`.
5. Do **not** publish `:8765` as the Demo window; gateway stays internal.

If Streamlit were put on another host port while Chainlit kept 8000, that would violate “one command, one familiar chat URL” unless ticket 03 explicitly keeps Chainlit for Eval — map currently says replace.

---

## Risks of two UIs in one image

| Risk | Why it matters |
|------|----------------|
| Two click targets | Reviewer/exec ambiguity; README must name one Chat UI; ADR 0021 / CONTEXT “avoid Streamlit” conflict until ADRs reopen |
| Two processes vs one `CMD` | Docker `CMD` is single; running both needs a process manager or second service — compose today has one `analyst` container |
| Double rate-limit buckets | Separate processes → separate `RateLimiter` state; spend gate weaker |
| Double warm / attest | Two adapters each calling `enable_domain_skills` → redundant POSTs (409 OK) and more cold-start load on gateway |
| Dependency / image size | `requirements-analyst.txt` grows; Chainlit + Streamlit both chat shells for one Analyst |
| Eval / red-team target drift | Five README dialogues and Gemini pack must pin **which** Chat UI is Demo |
| Metadata / ops | `source: "chainlit"` vs Streamlit traffic mixed in gateway logs |
| Product glossary | Until 0021 reopens, Chainlit **is** Chat UI; shipping both without decision reopens ticket 03 |

**Recommendation for implementers (not decided here):** replace Chainlit in `CMD`/README; do not leave a second Chat UI listening “just in case.”

---

## Glossary (how this ticket maps)

| Term | Meaning here |
|------|----------------|
| **Analyst** | Ouroboros agent loop (skills + `POST /api/tasks`). Not Chainlit, not Streamlit. |
| **Chat UI** | Browser conversation window — today Chainlit on `:8000`; if 0021 is reopened for the Dashboard map, **Streamlit becomes Chat UI**. |
| **Demo** | Hosted Analyst a reviewer (or later public URL) opens after one command — adapter + Ouroboros, not a second app. Dashboard may or may not *be* Demo (ticket 04). |

Thin-adapter rule: Streamlit may frame Session-start Web and layout, but the question path must remain `run_turn` → `OuroborosLoop.complete`. Anything else is a second Analyst (map out of scope).

---

## Out of scope for this research

- Implementing Streamlit or changing ADRs / Dockerfile.
- Session-start Web contract (ticket 02) and Dashboard vs Demo (ticket 04).
- Whether Forecast charts live on the page (map “not yet specified”).
