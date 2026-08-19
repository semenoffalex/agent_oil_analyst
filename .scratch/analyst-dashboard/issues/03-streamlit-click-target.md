# Streamlit is the click target

Type: grilling
Status: resolved
Blocked by:

## Question

The customer chose **Streamlit** instead of Chainlit. Lock the consequences so implementers do not keep two UIs.

- Does Streamlit **replace** Chainlit in compose (`CMD`, README, port **8000** vs another port)?
- Does the assignment still require “one command, open a browser” — now Streamlit — or is Chainlit kept for the reviewer Eval?
- How is Ouroboros proven (repo wiring, not `:8765` SPA), same idea as [0021](../../../docs/adr/0021-chainlit-adapter-ouroboros-loop.md)?
- Which ADRs this ticket will supersede: [0010](../../../docs/adr/0010-chainlit-ui.md), [0021](../../../docs/adr/0021-chainlit-adapter-ouroboros-loop.md), Streamlit/charts clauses of [0017](../../../docs/adr/0017-next-cycle-is-public-demo.md)?

Related research: [How Streamlit calls Ouroboros](07-how-streamlit-calls-ouroboros.md). This ticket is the **product** choice; that one is the **seam**.

## Answer

Streamlit **fully replaces** Chainlit. One compose command, browser **`localhost:8000`**, no Chainlit in the Demo image. Ouroboros is still the loop (`run_turn` / `POST /api/tasks`); proof stays in the repo, not `:8765`.

Supersedes the click-target of [0010](../../../docs/adr/0010-chainlit-ui.md) and [0021](../../../docs/adr/0021-chainlit-adapter-ouroboros-loop.md), and the “Streamlit out / charts post-Demo” clauses of [0017](../../../docs/adr/0017-next-cycle-is-public-demo.md). ADR: [0026](../../../docs/adr/0026-streamlit-dashboard-is-the-demo.md). Seam: [How Streamlit calls Ouroboros](07-how-streamlit-calls-ouroboros.md).
