# syntax=docker/dockerfile:1
# Current-generation Ouroboros (v6.103.0). Chainlit talks to this process; port 8765 stays internal.

FROM ghcr.io/astral-sh/uv:0.12.1 AS uv
FROM python:3.10-slim

COPY --from=uv /uv /uvx /bin/

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

ARG OUROBOROS_REF=v6.103.0
ENV APP_HOME=/app
WORKDIR ${APP_HOME}

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

RUN git clone --depth 1 --branch "${OUROBOROS_REF}" https://github.com/razzant/ouroboros.git . \
    && uv sync --locked --no-dev --no-install-project \
    && uv sync --locked --no-dev --no-editable \
    && pip install --no-cache-dir chromadb sentence-transformers pypdf pyyaml python-dotenv ddgs \
        statsmodels pandas numpy yfinance

ENV HF_HOME=/opt/hf-cache \
    HF_HUB_CACHE=/opt/hf-cache/hub \
    TRANSFORMERS_CACHE=/opt/hf-cache \
    HF_HUB_DISABLE_TELEMETRY=1 \
    EMBEDDING_MODEL=intfloat/multilingual-e5-base

RUN --mount=type=cache,id=sber-hf,target=/root/.cache/huggingface \
    HF_HOME=/root/.cache/huggingface \
    python -c "\
from sentence_transformers import SentenceTransformer;\
import os, shutil;\
m=os.environ['EMBEDDING_MODEL'];\
model=SentenceTransformer(m);\
shutil.rmtree('/opt/models/multilingual-e5-base', ignore_errors=True);\
model.save('/opt/models/multilingual-e5-base');\
" \
    && mkdir -p /opt/hf-cache \
    && cp -a /root/.cache/huggingface/. /opt/hf-cache/

COPY docker/ouroboros-entrypoint.sh /entrypoint.sh
COPY data/ouroboros/identity.md /seed/identity.md
COPY skills/oil_gas_analyst /seed/skills/oil_gas_analyst
COPY skills/oil_gas_retrieve /seed/skills/oil_gas_retrieve
COPY skills/oil_gas_web /seed/skills/oil_gas_web
COPY skills/oil_gas_forecast /seed/skills/oil_gas_forecast
COPY oil_gas_analyst /opt/analyst/oil_gas_analyst
COPY config /opt/analyst/config
COPY data/samples /opt/analyst/data/samples

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
    OUROBOROS_SKILLS_REPO_PATH=/seed/skills \
    PYTHONPATH=/opt/analyst \
    CHROMA_PATH=/data/chroma \
    SAMPLES_PATH=/opt/analyst/data/samples \
    REPORTS_PATH=/data/reports \
    FORECAST_CACHE_PATH=/data/forecast_cache \
    HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1 \
    EMBEDDING_MODEL=/opt/models/multilingual-e5-base

EXPOSE 8765

ENTRYPOINT ["/entrypoint.sh"]
