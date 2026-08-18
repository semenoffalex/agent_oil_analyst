# syntax=docker/dockerfile:1
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

ENV HF_HOME=/opt/hf-cache
ENV HF_HUB_CACHE=/opt/hf-cache/hub
ENV TRANSFORMERS_CACHE=/opt/hf-cache
ENV TRANSFORMERS_OFFLINE=0
ENV HF_HUB_DISABLE_TELEMETRY=1
ENV EMBEDDING_MODEL=intfloat/multilingual-e5-base

# Download once into BuildKit cache, then snapshot a local folder the app loads
# without contacting huggingface.co.
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

COPY config/ config/
COPY data/samples/ data/samples/
COPY oil_gas_analyst/ oil_gas_analyst/
COPY pyproject.toml .
COPY .env.example .env.example

ENV CHAINLIT_HOST=0.0.0.0
ENV CHAINLIT_PORT=8000
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV CHROMA_PATH=/app/data/chroma
ENV SAMPLES_PATH=/app/data/samples
ENV REPORTS_PATH=/app/data/reports
ENV HF_HUB_OFFLINE=1
ENV TRANSFORMERS_OFFLINE=1
ENV EMBEDDING_MODEL=/opt/models/multilingual-e5-base
ENV OUROBOROS_URL=http://ouroboros:8765

EXPOSE 8000

CMD ["chainlit", "run", "oil_gas_analyst/app.py", "--host", "0.0.0.0", "--port", "8000", "--headless"]
