# Where the reviewer talks to the Analyst

Type: grilling
Status: resolved
Blocked by: 01

## Question

Once we know how Ouroboros can host a domain Analyst, where does the **reviewer** actually talk?

Facts from [How Ouroboros can host the Analyst](01-how-ouroboros-hosts-the-analyst.md): Chat is always the Ouroboros SPA (desktop PyWebView, browser `:8765` with no PyWebView, or CLI over the same gateway). Importing Ouroboros into LangGraph, or using it as a silent judge of Chainlit strings, is **not** a supported host. Stock start is `ouroboros server` / `docker run -p 8765:8765`, keys in env or `settings.json` — not a documented Analyst `.env` image. Port 8000 is this repo’s Chainlit habit, not Ouroboros.

Options the customer must choose among (or reject):

- Native desktop as the only conversation surface.
- Docker / `ouroboros server` web at `:8765` as the grader demo (closest to TZ “one command + browser”).
- CLI (`ouroboros run` / `chat send`) as a first-class demo, with or without the browser.
- Chainlit (or another TZ UI) as a thin skin that **POSTs into** the Ouroboros gateway — not a second agent loop.

What happens to the current Chainlit app and to LangGraph as the thing the user talks to? This ticket picks the reviewer-facing surface, not the internal tool wiring.

## Answer

The reviewer clicks **Chainlit at `http://localhost:8000`**. That UI is an adapter: the turn runs in the **Ouroboros loop** (gateway may stay on `:8765` and stay off the demo URL). Desktop app is not required for acceptance. The grader verifies Ouroboros **in this repository**, not by opening Ouroboros Chat/Skills. LangGraph is not the conversation runtime.

ADR: [0021](../../../docs/adr/0021-chainlit-adapter-ouroboros-loop.md).

## Comments

- Browser vs desktop: acceptance is browser; desktop not required.
- `:8765` vs `:8000`: customer chose `:8000` so the click is familiar; Ouroboros is proven in code.
- Wiring: Chainlit → Ouroboros loop, not LangGraph with a decorative Ouroboros checkout.
