FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

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
ENV DEEPSEEK_THINKING=0

EXPOSE 8000

CMD ["chainlit", "run", "oil_gas_analyst/app.py", "--host", "0.0.0.0", "--port", "8000", "--headless"]
