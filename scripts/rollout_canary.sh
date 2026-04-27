#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: scripts/rollout_canary.sh --percent <0-100>

Examples:
  scripts/rollout_canary.sh --percent 25
  scripts/rollout_canary.sh --percent 100
EOF
}

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ROOT_DIR}/configs/stack.env"
COMPOSE_FILE="${ROOT_DIR}/deploy/compose/docker-compose.backend.yml"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Missing ${ENV_FILE}." >&2
  exit 1
fi

PERCENT=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --percent)
      shift
      PERCENT="${1:-}"
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
  shift

done

if [[ -z "${PERCENT}" ]]; then
  echo "--percent is required" >&2
  usage
  exit 1
fi

if ! [[ "${PERCENT}" =~ ^[0-9]+(\.[0-9]+)?$ ]]; then
  echo "Invalid percent: ${PERCENT}" >&2
  exit 1
fi

if awk "BEGIN {exit !(${PERCENT} >= 0 && ${PERCENT} <= 100)}"; then
  :
else
  echo "Percent must be between 0 and 100" >&2
  exit 1
fi

TMP_ENV="$(mktemp)"
trap 'rm -f "${TMP_ENV}"' EXIT

awk -v p="${PERCENT}" '
  BEGIN { updated=0 }
  /^CANARY_PERCENT=/ { print "CANARY_PERCENT=" p; updated=1; next }
  { print }
  END { if (!updated) print "CANARY_PERCENT=" p }
' "${ENV_FILE}" > "${TMP_ENV}"

cp "${TMP_ENV}" "${ENV_FILE}"

echo "[mira] updated CANARY_PERCENT=${PERCENT}"
cd "${ROOT_DIR}"
docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" up -d --force-recreate llm-canary-proxy

echo "[mira] canary rollout applied"
