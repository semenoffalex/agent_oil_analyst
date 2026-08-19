# How Streamlit calls Ouroboros

Type: research
Status: resolved
Blocked by:

## Question

How can Streamlit be a thin adapter over the same Analyst turn as Chainlit (`run_turn` → `OuroborosLoop.complete` / `POST /api/tasks`) without a second agent loop?

Need: current Chainlit warm/attest path (`build_loop`, skill toggle); Streamlit session vs Chainlit session; blocking vs timeout; compose `CMD`/port; what breaks if both UIs stay in the image.

Findings file: [research/streamlit-ouroboros-adapter.md](../research/streamlit-ouroboros-adapter.md).

## Answer

Streamlit can be the **Chat UI** by reusing Chainlit’s Python seam: `build_loop()` (attest + toggle) once, then `run_turn` → `OuroborosLoop.complete` → `POST /api/tasks`. That is not a second Analyst. Compose should replace Chainlit `CMD` on port **8000** rather than ship two UIs. Rate limit and Safety nets stay in `run_turn` / `app` equivalents. Product replace-vs-keep-Chainlit is [Streamlit is the click target](03-streamlit-click-target.md).
