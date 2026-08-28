# syntax=docker/dockerfile:1
# Streamlit Dashboard adapter only. No Torch, no Hugging Face weights.

FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-analyst.txt .
# Wheels only for hdbscan/numba: compiling them in Docker Desktop can freeze the VM for an hour.
RUN pip install --no-cache-dir --default-timeout=300 --retries 5 \
    --only-binary=hdbscan,llvmlite,numba \
    -r requirements-analyst.txt

COPY config/ config/
COPY .streamlit/ .streamlit/
COPY data/samples/ data/samples/
COPY oil_gas_analyst/ oil_gas_analyst/
COPY pyproject.toml .
COPY .env.example .env.example

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV CHROMA_PATH=/app/data/chroma
ENV SAMPLES_PATH=/app/data/samples
ENV REPORTS_PATH=/app/data/reports
ENV TOP_NEWS_CACHE_PATH=/app/data/top_news_cache
ENV TOPICS_CACHE_PATH=/app/data/topics_cache
ENV OUROBOROS_URL=http://ouroboros:8765
ENV EMBEDDING_BASE_URL=https://openrouter.ai/api/v1
ENV EMBEDDING_MODEL=nvidia/nemotron-3-embed-1b:free

EXPOSE 8000

CMD ["streamlit", "run", "oil_gas_analyst/dashboard.py", "--server.port", "8000", "--server.address", "0.0.0.0", "--browser.gatherUsageStats", "false"]
