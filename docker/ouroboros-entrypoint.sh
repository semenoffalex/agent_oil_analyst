#!/bin/sh
set -e

if [ -z "${OPENROUTER_API_KEY}" ]; then
  echo "OPENROUTER_API_KEY is missing. Copy .env.example to .env and set the OpenRouter key." >&2
  echo "There is no silent fallback to DeepSeek or Grok." >&2
  exit 1
fi

DATA="${OUROBOROS_DATA_DIR:-/data}"
mkdir -p "${DATA}/memory" "${DATA}/skills/external" "${DATA}/chroma" "${DATA}/reports" "${DATA}/forecast_cache"
cp /seed/identity.md "${DATA}/memory/identity.md"
cp -a /seed/skills/oil_gas_analyst "${DATA}/skills/external/oil_gas_analyst"
cp -a /seed/skills/oil_gas_retrieve "${DATA}/skills/external/oil_gas_retrieve"
cp -a /seed/skills/oil_gas_web "${DATA}/skills/external/oil_gas_web"
cp -a /seed/skills/oil_gas_forecast "${DATA}/skills/external/oil_gas_forecast"

export OUROBOROS_SERVER_HOST="${OUROBOROS_SERVER_HOST:-0.0.0.0}"
export OUROBOROS_MODEL="${OUROBOROS_MODEL:-z-ai/glm-5.2:free}"
export OUROBOROS_RUNTIME_MODE="${OUROBOROS_RUNTIME_MODE:-light}"
export OUROBOROS_TASK_REVIEW_MODE="${OUROBOROS_TASK_REVIEW_MODE:-off}"
export OUROBOROS_POST_TASK_EVOLUTION="${OUROBOROS_POST_TASK_EVOLUTION:-false}"
export OUROBOROS_EFFORT_TASK="${OUROBOROS_EFFORT_TASK:-none}"
export OUROBOROS_RETURN_REASONING="${OUROBOROS_RETURN_REASONING:-false}"
export OUROBOROS_MODEL_FALLBACKS="${OUROBOROS_MODEL_FALLBACKS:-}"
export OUROBOROS_MODEL_LIGHT="${OUROBOROS_MODEL_LIGHT:-}"

exec python server.py
