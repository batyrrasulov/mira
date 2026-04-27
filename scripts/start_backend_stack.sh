#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ROOT_DIR}/configs/stack.env"
COMPOSE_FILE="${ROOT_DIR}/deploy/compose/docker-compose.backend.yml"
START_MODE="${MIRA_START_MODE:-auto}"
PYTHON_BIN="${PYTHON_BIN:-}"

resolve_python() {
  if [[ -n "${PYTHON_BIN}" ]]; then
    return 0
  fi
  if command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
    return 0
  fi
  if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
    return 0
  fi
  echo "[mira] neither python nor python3 is available in PATH" >&2
  return 1
}

has_nvidia_runtime() {
  docker info --format '{{json .Runtimes}}' 2>/dev/null | grep -q '"nvidia"'
}

probe_api() {
  local host="$1"
  local port="$2"

  "${PYTHON_BIN}" - "$host" "$port" <<'PY'
import json
import sys
import time
import urllib.request

host = sys.argv[1]
port = sys.argv[2]

if host in {"0.0.0.0", "::"}:
    host = "127.0.0.1"

for _ in range(30):
    try:
        with urllib.request.urlopen(f"http://{host}:{port}/health", timeout=5) as resp:
            if int(resp.status) != 200:
                raise RuntimeError(f"/health status={resp.status}")
        with urllib.request.urlopen(f"http://{host}:{port}/ready", timeout=5) as resp:
            body = json.loads(resp.read().decode("utf-8") or "{}")
            if int(resp.status) == 200:
                print(json.dumps(body, ensure_ascii=True))
                raise SystemExit(0)
    except Exception:
        time.sleep(2)

print("API failed health/readiness probe", file=sys.stderr)
raise SystemExit(1)
PY
}

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Missing ${ENV_FILE}. Create it from configs/stack.env.example first." >&2
  exit 1
fi

resolve_python

if [[ "${START_MODE}" != "auto" && "${START_MODE}" != "gpu" && "${START_MODE}" != "fallback" ]]; then
  echo "Invalid MIRA_START_MODE=${START_MODE}. Use one of: auto, gpu, fallback" >&2
  exit 1
fi

echo "[mira] launching backend stack"

MODE="${START_MODE}"
if [[ "${MODE}" == "auto" ]]; then
  if has_nvidia_runtime; then
    MODE="gpu"
  else
    MODE="fallback"
  fi
fi

if [[ "${MODE}" == "gpu" ]] && ! has_nvidia_runtime; then
  echo "[mira] requested GPU mode but Docker nvidia runtime is unavailable." >&2
  echo "[mira] set MIRA_START_MODE=fallback to run API-only mode on non-GPU hosts." >&2
  exit 1
fi

cd "${ROOT_DIR}"
set -a
source "${ENV_FILE}"
set +a

if [[ "${MODE}" == "gpu" ]]; then
  docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" up -d --build

  echo "[mira] waiting for vLLM readiness"
  "${ROOT_DIR}/scripts/check_llm_readiness.py" \
    --base-url "http://${VLLM_BIND_ADDRESS}:${VLLM_PUBLIC_PORT}" \
    --model "${BASE_MODEL_NAME}" \
    --api-key "${VLLM_API_KEY:-}"

  probe_api "${MIRA_API_BIND_ADDRESS}" "${MIRA_API_PORT}"

  echo "[mira] stack ready (mode=gpu)"
  echo "  vLLM:   http://${VLLM_BIND_ADDRESS}:${VLLM_PUBLIC_PORT}"
  echo "  Proxy:  http://${CANARY_PROXY_BIND_ADDRESS}:${CANARY_PROXY_PUBLIC_PORT}"
  echo "  API:    http://${MIRA_API_BIND_ADDRESS}:${MIRA_API_PORT}"
  exit 0
fi

echo "[mira] nvidia runtime not found; starting API-only fallback mode"
MIRA_FORCE_FALLBACK=true \
MIRA_LLM_BASE_URL= \
MIRA_LLM_MODEL= \
docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" up -d --build --no-deps mira-api

probe_api "${MIRA_API_BIND_ADDRESS}" "${MIRA_API_PORT}"

echo "[mira] stack ready (mode=fallback)"
echo "  vLLM:   disabled"
echo "  Proxy:  disabled"
echo "  API:    http://${MIRA_API_BIND_ADDRESS}:${MIRA_API_PORT}"
