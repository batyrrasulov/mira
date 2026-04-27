#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

"${ROOT_DIR}/scripts/rollout_canary.sh" --percent 0

echo "[mira] rollback complete: all traffic routed to base model"
