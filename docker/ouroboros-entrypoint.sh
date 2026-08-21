#!/bin/sh
set -e

if [ -z "${DEEPSEEK_API_KEY}" ]; then
  echo "DEEPSEEK_API_KEY is missing. Copy .env.example to .env and set the DeepSeek key." >&2
  echo "There is no silent fallback to OpenRouter or Grok." >&2
  exit 1
fi

export OPENAI_COMPATIBLE_API_KEY="${OPENAI_COMPATIBLE_API_KEY:-${DEEPSEEK_API_KEY}}"
export OPENAI_COMPATIBLE_BASE_URL="${OPENAI_COMPATIBLE_BASE_URL:-${DEEPSEEK_BASE_URL:-https://api.deepseek.com}}"
# ADR 0027: OpenRouter in this process makes Ouroboros prefer the wrong chat lane.
unset OPENROUTER_API_KEY OPENROUTER_BASE_URL

DATA="${OUROBOROS_DATA_DIR:-/data}"
mkdir -p "${DATA}/memory" "${DATA}/skills/external" "${DATA}/chroma" "${DATA}/reports" "${DATA}/forecast_cache"
cp /seed/identity.md "${DATA}/memory/identity.md"
cp -a /seed/skills/oil_gas_analyst "${DATA}/skills/external/oil_gas_analyst"
cp -a /seed/skills/oil_gas_retrieve "${DATA}/skills/external/oil_gas_retrieve"
cp -a /seed/skills/oil_gas_web "${DATA}/skills/external/oil_gas_web"
cp -a /seed/skills/oil_gas_forecast "${DATA}/skills/external/oil_gas_forecast"

export OUROBOROS_SERVER_HOST="${OUROBOROS_SERVER_HOST:-0.0.0.0}"
export OUROBOROS_MODEL="${OUROBOROS_MODEL:-openai-compatible::deepseek-v4-flash}"
export OUROBOROS_RUNTIME_MODE="${OUROBOROS_RUNTIME_MODE:-light}"
export OUROBOROS_TASK_REVIEW_MODE="${OUROBOROS_TASK_REVIEW_MODE:-off}"
export OUROBOROS_POST_TASK_EVOLUTION="${OUROBOROS_POST_TASK_EVOLUTION:-false}"
export OUROBOROS_EFFORT_TASK="${OUROBOROS_EFFORT_TASK:-none}"
export OUROBOROS_RETURN_REASONING="${OUROBOROS_RETURN_REASONING:-false}"
export OUROBOROS_MODEL_FALLBACKS="${OUROBOROS_MODEL_FALLBACKS:-}"
export OUROBOROS_MODEL_LIGHT="${OUROBOROS_MODEL_LIGHT:-}"

exec python server.py
