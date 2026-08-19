# syntax=docker/dockerfile:1
# Streamlit Dashboard adapter only. No Torch, no Hugging Face weights.

FROM python:3.11-slim

WORKDIR /app

COPY requirements-analyst.txt .
RUN pip install --no-cache-dir --default-timeout=300 --retries 5 -r requirements-analyst.txt

COPY config/ config/
COPY data/samples/ data/samples/
COPY oil_gas_analyst/ oil_gas_analyst/
COPY pyproject.toml .
COPY .env.example .env.example

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV CHROMA_PATH=/app/data/chroma
ENV SAMPLES_PATH=/app/data/samples
ENV REPORTS_PATH=/app/data/reports
ENV OUROBOROS_URL=http://ouroboros:8765
ENV EMBEDDING_BASE_URL=http://192.168.0.55:1234/v1
ENV EMBEDDING_MODEL=text-embedding-multilingual-e5-base
ENV EMBEDDING_API_KEY=lm-studio

EXPOSE 8000

CMD ["streamlit", "run", "oil_gas_analyst/dashboard.py", "--server.port", "8000", "--server.address", "0.0.0.0", "--browser.gatherUsageStats", "false"]
