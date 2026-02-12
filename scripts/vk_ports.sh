#!/usr/bin/env bash
set -euo pipefail

MODE="plain"
if [[ "${1:-}" == "--export" ]]; then
  MODE="export"
fi

ROOT_DIR="$(git rev-parse --show-toplevel 2>/dev/null || pwd -P)"
WORKTREE_DIR="$(pwd -P)"
BRANCH="$(git -C "$ROOT_DIR" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")"

MAIN_BRANCHES="${VK_MAIN_BRANCHES:-main,master}"
MAIN_BACKEND_PORT="${VK_MAIN_BACKEND_PORT:-8000}"
MAIN_FRONTEND_PORT="${VK_MAIN_FRONTEND_PORT:-3000}"

is_main_branch=0
IFS=',' read -r -a _branches <<<"$MAIN_BRANCHES"
for raw_branch in "${_branches[@]}"; do
  branch_item="${raw_branch// /}"
  if [[ -n "$branch_item" && "$BRANCH" == "$branch_item" ]]; then
    is_main_branch=1
    break
  fi
done

if [[ -n "${VK_BACKEND_PORT:-}" ]]; then
  BACKEND_PORT="$VK_BACKEND_PORT"
elif [[ "$is_main_branch" -eq 1 ]]; then
  BACKEND_PORT="$MAIN_BACKEND_PORT"
else
  seed="${ROOT_DIR}|${WORKTREE_DIR}|${BRANCH}|backend"
  hash_value="$(printf '%s' "$seed" | cksum | awk '{print $1}')"
  BACKEND_PORT="$((8100 + hash_value % 800))"
fi

if [[ -n "${VK_FRONTEND_PORT:-}" ]]; then
  FRONTEND_PORT="$VK_FRONTEND_PORT"
elif [[ "$is_main_branch" -eq 1 ]]; then
  FRONTEND_PORT="$MAIN_FRONTEND_PORT"
else
  seed="${ROOT_DIR}|${WORKTREE_DIR}|${BRANCH}|frontend"
  hash_value="$(printf '%s' "$seed" | cksum | awk '{print $1}')"
  FRONTEND_PORT="$((3100 + hash_value % 800))"
fi

BACKEND_BASE_URL="http://127.0.0.1:${BACKEND_PORT}"
FRONTEND_BASE_URL="http://127.0.0.1:${FRONTEND_PORT}"
LIVE_API_BASE="${BACKEND_BASE_URL}/api/v1"

emit() {
  local key="$1"
  local value="$2"
  if [[ "$MODE" == "export" ]]; then
    printf 'export %s=%q\n' "$key" "$value"
  else
    printf '%s=%s\n' "$key" "$value"
  fi
}

emit "VK_ROOT_DIR" "$ROOT_DIR"
emit "VK_WORKTREE_DIR" "$WORKTREE_DIR"
emit "VK_GIT_BRANCH" "$BRANCH"
emit "VK_IS_MAIN_BRANCH" "$is_main_branch"
emit "VK_BACKEND_PORT" "$BACKEND_PORT"
emit "VK_FRONTEND_PORT" "$FRONTEND_PORT"
emit "VK_BACKEND_BASE_URL" "$BACKEND_BASE_URL"
emit "VK_FRONTEND_BASE_URL" "$FRONTEND_BASE_URL"
emit "LIVE_API_BASE" "$LIVE_API_BASE"
emit "E2E_API_BASE" "$BACKEND_BASE_URL"
