#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ROOT_DIR}/configs/stack.env"
COMPOSE_FILE="${ROOT_DIR}/deploy/compose/docker-compose.backend.yml"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Missing ${ENV_FILE}. Create it from configs/stack.env.example first." >&2
  exit 1
fi

echo "[mira] launching backend stack"
cd "${ROOT_DIR}"
docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" up -d --build

echo "[mira] waiting for vLLM readiness"
set -a
source "${ENV_FILE}"
set +a

python "${ROOT_DIR}/scripts/check_llm_readiness.py" \
  --base-url "http://${VLLM_BIND_ADDRESS}:${VLLM_PUBLIC_PORT}" \
  --model "${BASE_MODEL_NAME}" \
  --api-key "${VLLM_API_KEY:-}"

echo "[mira] stack ready"
echo "  vLLM:   http://${VLLM_BIND_ADDRESS}:${VLLM_PUBLIC_PORT}"
echo "  Proxy:  http://${CANARY_PROXY_BIND_ADDRESS}:${CANARY_PROXY_PUBLIC_PORT}"
echo "  API:    http://${MIRA_API_BIND_ADDRESS}:${MIRA_API_PORT}"
