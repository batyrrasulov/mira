#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ROOT_DIR}/configs/stack.env"
COMPOSE_FILE="${ROOT_DIR}/deploy/compose/docker-compose.backend.yml"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Missing ${ENV_FILE}." >&2
  exit 1
fi

echo "[mira] stopping backend stack"
cd "${ROOT_DIR}"
docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" down --remove-orphans
