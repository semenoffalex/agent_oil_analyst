## Agent skills

### Issue tracker

Issues live as markdown under `.scratch/<feature>/`. See `docs/agents/issue-tracker.md`.

### Domain docs

Single-context: root `CONTEXT.md` and `docs/adr/`. See `docs/agents/domain.md`.

## Learned User Preferences

- Do not commit or push unless the user explicitly asks.
- Do not deploy to production unless the user explicitly asks.
- Talk to the user in Russian; keep tickets, ADRs, specs, and git commit messages in English.
- Exclude `uv.lock` and `oil_gas_analyst.egg-info/` from commits.
- Prefer external APIs for embeddings and compute; do not add CUDA, Torch, or in-process embedding stacks unless the user asks.
- Document Docker as the preferred way to run the app (README Start).
- Keep README human-readable in Russian.
- Do not mention Cursor as a contributor in docs or git history.

## Learned Workspace Facts

- Main working branch is `dev`; production deploys track `origin/dev`.
- Production: `root@194.87.76.94`, app at `/opt/agent_oil_analyst`, Dashboard on port 8000 (`http://194.87.76.94:8000`). Typical deploy: `git fetch && git checkout dev && git pull origin dev && docker compose build analyst && docker compose up -d analyst`.
- Local dev: `docker compose up --build` serves Streamlit on `http://localhost:8000`; rebuild the `analyst` image when code changes are not reflected.
- Demo UI is Streamlit (not Chainlit); Ouroboros runs internally on `:8765`.
- Brent chart (`oil_gas_analyst/dashboard_chart.py`): `chart_display_dataframe` shows ~22 trading days of actuals plus the forecast window; AutoARIMA, UnobservedComponents, and AutoReg lines toggle via checkboxes in `dashboard.py`; Y-axis minimum is `CHART_Y_AXIS_MIN` via Altair `brent_chart_altair`.
- After cloning `agent_oil_analyst` from GitHub, check out `dev` (`origin/dev` is not necessarily the default clone branch).
- Embeddings go through the local API at `192.168.0.55:1234`. `MAIN_CHAT_MODEL`, `OUROBOROS_MODEL`, and `EVAL_CHAT_MODEL` are separate env vars (OpenRouter ids; `:free` slugs rotate).
- LangSmith traces use project `pr-drab-realization-91`.
- GitHub remote is `semenoffalex/agent_oil_analyst`.
- RAG searches the report corpus before the web; answers should include source hyperlinks.
