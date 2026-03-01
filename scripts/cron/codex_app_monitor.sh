#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

BASE_URL="${CODEX_APP_BASE_URL:-http://127.0.0.1:8000/api/v1}"
ALERT_THRESHOLD="${CODEX_MONITOR_ALERT_THRESHOLD:-2}"
TIMEOUT_SEC="${CODEX_MONITOR_TIMEOUT_SEC:-8}"
BEARER_TOKEN="${CODEX_APP_BEARER_TOKEN:-}"

PYTHON_BIN="${PYTHON_BIN:-python3}"

ARGS=(
  --base-url "$BASE_URL"
  --timeout "$TIMEOUT_SEC"
  --alert-threshold "$ALERT_THRESHOLD"
)

if [[ -n "$BEARER_TOKEN" ]]; then
  ARGS+=(--bearer-token "$BEARER_TOKEN")
fi

exec "$PYTHON_BIN" scripts/codex_app_monitor.py \
  "${ARGS[@]}" \
  "$@"
