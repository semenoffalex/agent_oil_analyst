# Session-start `search_for_tool` / `oil_gas_web` (ticket 08)

**Scope:** facts about calling the Python search path with a host-chosen query, without an Ouroboros task.  
**Not in scope:** whether the Dashboard *should* do that ([05-host-start-web-versus-loop.md](../issues/05-host-start-web-versus-loop.md), [ADR 0019](../../../docs/adr/0019-model-decides-the-loop.md)).

**This document is a fact about calling the function. It is not permission to bypass the agent loop.**

Sources: `oil_gas_analyst/web.py`, `oil_gas_analyst/denylist.py`, `oil_gas_analyst/turn.py` (`web_citation`), `skills/oil_gas_web/`, `tests/test_denylist.py`, [ADR 0008](../../../docs/adr/0008-duckduckgo-denylist.md), README limits.

---

## Can the host call it at session start (no Ouroboros task)?

**Yes, as a pure function call.**

- `search_for_tool` lives in `oil_gas_analyst/web.py`. It imports denylist + `web_citation`, builds a DuckDuckGo (or injected) searcher, and returns a `dict`. It does **not** talk to the Ouroboros gateway, create a task, or require a user chat turn.
- The skill wrapper (`skills/oil_gas_web/plugin.py`) is only the Ouroboros tool surface: `register` → `search_web(ctx, query=...)` → `return search_for_tool(query)`.
- A Dashboard / Streamlit host can therefore `from oil_gas_analyst.web import search_for_tool` and pass any string, with no skill registration and no model tool-call.

Whether that is allowed as product behaviour is ticket **05** / ADR **0019** (model decides Web in the loop). Ticket **08** only answers: the function is callable that way and what it returns.

---

## Function signatures

### `search_for_tool`

```text
search_for_tool(query: str, searcher=None, k: int = 8) -> dict
```

| Param | Role |
|--------|------|
| `query` | Passed straight to `searcher.search(query)` (or `DuckDuckGoWeb().search`). |
| `searcher` | Optional injectable with `.search(str) -> list[WebHit]` (tests use this). Default: `DuckDuckGoWeb()`. |
| `k` | Cap on hits after search (`hits[:k]`). Default `8`. |

Decorated with `@maybe_traceable("analyst.search_web", run_type="retriever")` (LangSmith no-op unless tracing env is on). Does not change the return shape.

### Skill handler

```text
search_web(ctx, query: str = "") -> dict   # same dict as search_for_tool
```

- Tool name: `search_web`
- JSON schema: `properties.query` type `string`; **`required: ["query"]`**
- Handler default `query=""` is only a Python default; the schema still lists `query` as required for the model tool-call path
- `timeout_sec=60` on both `SKILL.md` and `api.register_tool(...)`

### Lower-level helpers (relevant failure modes)

```text
DuckDuckGoWeb.search(self, question: str) -> list[WebHit]
fetch_page_text(url: str, timeout: float = 8.0) -> str
fill_page_bodies(hits, *, fetch_page=None, limit=3, max_chars=2000, denied_domains=None) -> list[WebHit]
is_denied(url: str, domains) -> bool
web_citation(hit: WebHit) -> Citation   # label used in JSON
```

---

## Return dict shape

Top level:

| Key | Type | Meaning |
|-----|------|---------|
| `hits` | `list[dict]` | Ordered rows (capped by `k`) |
| `count` | `int` | `len(hits)` |
| `note` | `str` | Guidance string for the model (or any reader) |

Each hit row:

| Key | Type | Meaning |
|-----|------|---------|
| `citation` | `str` | Copy-ready label from `web_citation` |
| `url` | `str` | Hit URL |
| `title` | `str` | Hit title |
| `snippet` | `str` | DDG body/snippet, often replaced by fetched page text (first 3 hits, ≤2000 chars) |
| `denied` | `bool` | `is_denied(url, load_denylist())` — Yellow-press match |

Denied hits **stay in** `hits`. Denylist is a citation contract (`denied=true` → do not cite), not a host drop ([ADR 0019](../../../docs/adr/0019-model-decides-the-loop.md) vs older [ADR 0008](../../../docs/adr/0008-duckduckgo-denylist.md) “drop” wording). `fill_page_bodies` documents the same: denylist is not used to remove URLs.

### `note` variants

- Non-empty hits:  
  `"Do not cite hits with denied=true (Yellow-press). Citing them is a prompt failure, not something the host will strip."`
- Empty hits (`count == 0`):  
  `"No Web sources. Do not invent news, oil prices, or volumes."`

Covered by `tests/test_denylist.py::test_empty_web_search_asks_not_to_invent_news`.

---

## Citation labels `[Источник: …, web]`

From `web_citation` in `oil_gas_analyst/turn.py`:

- Host = URL hostname, with leading `www.` stripped; if no hostname, falls back to `hit.title`
- Label format: **`[Источник: {host}, web]`**
- That string is what appears in each row’s `citation` field
- Skill docs tell the model to copy `citation` fields into the answer

---

## Is a query string required? Empty query?

| Layer | Behaviour |
|--------|-----------|
| `search_for_tool` | Type-annotated `query: str` only. **No** empty-check, min-length, or raise on `""`. |
| Skill schema | `query` is **required** for the Ouroboros tool JSON schema (model must pass it). |
| Skill handler | Python default `query=""` if somehow omitted. |
| Live DDG | Empty/`""` is passed to `DDGS().text(question, max_results=8)` with no special branch. |

There is **no** dedicated “empty query → empty list” test. Practical outcomes for `query=""`:

1. Library returns rows → normal payload with `denied` flags, or  
2. Library raises / returns nothing → same path as any DDG failure (below).

Host-chosen non-empty queries (e.g. canned “OPEC oil prices”) are fully supported by the API surface; nothing in `search_for_tool` ties `query` to a user message.

---

## Empty list vs exception

**Failure of search itself does not raise out of `DuckDuckGoWeb.search`.**

```text
try:
    from ddgs import DDGS
    with DDGS() as client:
        rows = client.text(question, max_results=8)
except Exception:
    return []
```

Consequences:

- Import failure, network error, rate-limit, HTML/API change, unexpected `ddgs` error → **`[]`**, then `search_for_tool` returns  
  `{"hits": [], "count": 0, "note": "No Web sources. Do not invent news, oil prices, or volumes."}`
- Injected empty searcher in tests → same shape
- **No** exception bubbles to the caller for DDG/search failures

Page-fetch path (after hits exist):

- `fetch_page_text`: bad scheme, PDF path, non-HTML content-type, `URLError` / `TimeoutError` / `OSError` / `ValueError` → `""` (keep DDG snippet)
- `fill_page_bodies`: any exception from custom `fetch_page` → keep original snippet
- Fetches at most **3** hits (`_PAGE_LIMIT`), **8.0 s** timeout per URL (`fetch_page_text`), snippet capped at **2000** chars

So: empty JSON list + uncertainty note is the designed soft-fail; not an exception for “DDG down.”

---

## Timeouts

| Layer | Value | What it bounds |
|--------|--------|----------------|
| Page fetch | **8.0 s** per URL | `urllib` in `fetch_page_text` |
| Skill / tool | **60 s** | `skills/oil_gas_web` `timeout_sec` + `register_tool(..., timeout_sec=60)` — Ouroboros tool wall when called via the loop |
| Ouroboros turn (chat) | **900 s** default (`OUROBOROS_TURN_TIMEOUT_SEC`) | Whole Analyst turn via gateway — **not** used when the host imports `search_for_tool` directly |

Direct host call: only the 8 s page fetches (+ DDG client time inside `ddgs`) apply unless the host adds its own deadline. The 60 s skill timeout applies only when the tool runs inside Ouroboros.

---

## DuckDuckGo-in-Docker failure modes (already documented / encoded)

From [ADR 0008](../../../docs/adr/0008-duckduckgo-denylist.md) and README:

- Demos depend on DuckDuckGo staying **reachable from Docker** (no Tavily/SerpAPI key).
- Live quotes / search can fail when DDG HTML/API changes or rate-limits.
- README: **“DuckDuckGo и Yahoo в Docker периодически молчат.”** (periodic silence — soft-fail to empty, not a crash)

In code, that silence maps to:

1. Broad `except Exception` in `DuckDuckGoWeb.search` → empty list  
2. Empty `search_for_tool` payload + “Do not invent…” note  
3. Per-page fetch failures do not drop hits; snippets stay at DDG body text  

`ddgs` is installed in the image (`docker/ouroboros.Dockerfile`). Package presence does not guarantee outbound HTTPS / DDG availability from the container network.

---

## Summary for Dashboard session-start design

| Question | Answer |
|----------|--------|
| Callable without Ouroboros task? | **Yes** — import `search_for_tool` and pass a host query. |
| JSON? | `{hits[{citation,url,title,snippet,denied}], count, note}` |
| Empty / DDG down? | Empty `hits`, `count: 0`, invent-news note — **not** an exception. |
| Labels? | `[Источник: <host>, web]` in `citation`. |
| Denied? | Flag only; rows remain. |
| Permission to bypass loop? | **No** — see ticket 05 / ADR 0019. This file is callability + payload facts only. |
