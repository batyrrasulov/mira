#!/usr/bin/env bash
set -euo pipefail

HOST="${MIRA_HOST:-0.0.0.0}"
PORT="${MIRA_PORT:-8080}"

uvicorn mira.api:app --app-dir src --host "$HOST" --port "$PORT"
