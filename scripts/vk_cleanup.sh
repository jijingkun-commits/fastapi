#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(git rev-parse --show-toplevel 2>/dev/null || pwd -P)"
cd "$ROOT_DIR"

eval "$(bash scripts/vk_ports.sh --export)"

RUN_DIR="$ROOT_DIR/.vibe/run"
BACKEND_PID_FILE="$RUN_DIR/backend.pid"
WEB_PID_FILE="$RUN_DIR/web.pid"

read_pid() {
  local pid_file="$1"
  if [[ -f "$pid_file" ]]; then
    cat "$pid_file"
  fi
}

wait_stop() {
  local pid="$1"
  local retry=0
  while kill -0 "$pid" >/dev/null 2>&1; do
    retry=$((retry + 1))
    if [[ "$retry" -gt 30 ]]; then
      return 1
    fi
    sleep 0.2
  done
  return 0
}

stop_service() {
  local name="$1"
  local pid_file="$2"
  local pid
  pid="$(read_pid "$pid_file")"

  if [[ -z "$pid" ]]; then
    echo "[vk_cleanup] ${name}: no pid file"
    return 0
  fi

  if ! kill -0 "$pid" >/dev/null 2>&1; then
    rm -f "$pid_file"
    echo "[vk_cleanup] ${name}: stale pid removed (${pid})"
    return 0
  fi

  kill "$pid" >/dev/null 2>&1 || true
  if wait_stop "$pid"; then
    rm -f "$pid_file"
    echo "[vk_cleanup] ${name}: stopped (pid=${pid})"
    return 0
  fi

  kill -9 "$pid" >/dev/null 2>&1 || true
  rm -f "$pid_file"
  echo "[vk_cleanup] ${name}: force stopped (pid=${pid})"
}

stop_service "web" "$WEB_PID_FILE"
stop_service "backend" "$BACKEND_PID_FILE"

echo "[vk_cleanup] done for branch=${VK_GIT_BRANCH}" 
