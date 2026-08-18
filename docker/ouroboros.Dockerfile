# syntax=docker/dockerfile:1
# Current-generation Ouroboros (v6.103.0). Chainlit talks to this process; port 8765 stays internal.

FROM ghcr.io/astral-sh/uv:0.12.1 AS uv
FROM python:3.10-slim

COPY --from=uv /uv /uvx /bin/

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

ARG OUROBOROS_REF=v6.103.0
ENV APP_HOME=/app
WORKDIR ${APP_HOME}

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

RUN git clone --depth 1 --branch "${OUROBOROS_REF}" https://github.com/razzant/ouroboros.git . \
    && uv sync --locked --no-dev --no-install-project \
    && uv sync --locked --no-dev --no-editable

COPY docker/ouroboros-entrypoint.sh /entrypoint.sh
COPY data/ouroboros/identity.md /seed/identity.md
COPY skills/oil_gas_analyst /seed/skills/oil_gas_analyst

RUN chmod +x /entrypoint.sh

ENV OUROBOROS_SERVER_HOST=0.0.0.0 \
    OUROBOROS_SERVER_PORT=8765 \
    OUROBOROS_FILE_BROWSER_DEFAULT=${APP_HOME} \
    OUROBOROS_DATA_DIR=/data \
    OUROBOROS_RUNTIME_MODE=light \
    OUROBOROS_TASK_REVIEW_MODE=off \
    OUROBOROS_POST_TASK_EVOLUTION=false \
    OUROBOROS_EFFORT_TASK=none \
    OUROBOROS_RETURN_REASONING=false \
    OUROBOROS_MODEL_FALLBACKS= \
    OUROBOROS_MODEL_LIGHT= \
    OUROBOROS_TRUST_NONLOCAL_BIND_WITHOUT_PASSWORD=1 \
    OUROBOROS_SKILLS_REPO_PATH=/seed/skills

EXPOSE 8765

ENTRYPOINT ["/entrypoint.sh"]
