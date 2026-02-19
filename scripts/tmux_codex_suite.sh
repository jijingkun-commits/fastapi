#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(git rev-parse --show-toplevel 2>/dev/null || pwd -P)"
PROJECT_DIR="${PROJECT_DIR:-$ROOT_DIR}"
WEB_DIR="${WEB_DIR:-$PROJECT_DIR/web}"

DEV_SESSION="${TMUX_CODEX_DEV_SESSION:-dev-hub}"
BUG_SESSION="${TMUX_CODEX_BUG_SESSION:-bug-room}"
CODEX_CMD="${TMUX_CODEX_CMD:-codex}"
SHELL_CMD="${TMUX_CODEX_SHELL_CMD:-${SHELL:-zsh} -l}"

ACTION="${1:-up}"

usage() {
  cat <<'EOF'
用法:
  bash scripts/tmux_codex_suite.sh up
  bash scripts/tmux_codex_suite.sh up-no-attach
  bash scripts/tmux_codex_suite.sh status
  bash scripts/tmux_codex_suite.sh attach [dev|bug|<session>]
  bash scripts/tmux_codex_suite.sh send <session:window> <text>
  bash scripts/tmux_codex_suite.sh tail <session:window> [lines]
  bash scripts/tmux_codex_suite.sh stop [all|dev|bug|<session>]

环境变量（可选）:
  PROJECT_DIR                项目目录（默认 git 根目录）
  WEB_DIR                    前端目录（默认 PROJECT_DIR/web）
  TMUX_CODEX_DEV_SESSION     开发会话名（默认 dev-hub）
  TMUX_CODEX_BUG_SESSION     Bug 会话名（默认 bug-room）
  TMUX_CODEX_CMD             codex 启动命令（默认 codex）
  TMUX_CODEX_SHELL_CMD       回退 shell 命令（默认 "$SHELL -l"）
EOF
}

require_tmux() {
  if ! command -v tmux >/dev/null 2>&1; then
    echo "[tmux-codex] 未找到 tmux，请先安装 tmux。" >&2
    exit 1
  fi
}

resolve_worker_cmd() {
  local codex_bin
  codex_bin="${CODEX_CMD%% *}"
  if command -v "$codex_bin" >/dev/null 2>&1; then
    printf '%s\n' "$CODEX_CMD"
    return 0
  fi
  echo "[tmux-codex] 警告: 未找到 codex 命令（$codex_bin），窗口将使用 shell 回退。" >&2
  printf '%s\n' "$SHELL_CMD"
}

window_exists() {
  local session="$1"
  local window_name="$2"
  tmux list-windows -t "$session" -F '#W' 2>/dev/null | grep -Fxq "$window_name"
}

ensure_session() {
  local session="$1"
  local start_dir="$2"
  local start_cmd="$3"

  if ! tmux has-session -t "$session" 2>/dev/null; then
    tmux new-session -d -s "$session" -n orchestrator -c "$start_dir" "$start_cmd"
    return 0
  fi

  if ! window_exists "$session" "orchestrator"; then
    tmux new-window -d -t "$session" -n orchestrator -c "$start_dir" "$start_cmd"
  fi
}

ensure_window() {
  local session="$1"
  local window_name="$2"
  local start_dir="$3"
  local start_cmd="$4"

  if window_exists "$session" "$window_name"; then
    return 0
  fi
  tmux new-window -d -t "$session" -n "$window_name" -c "$start_dir" "$start_cmd"
}

setup_dev_session() {
  local worker_cmd="$1"
  local ops_cmd="$2"

  ensure_session "$DEV_SESSION" "$PROJECT_DIR" "$worker_cmd"
  ensure_window "$DEV_SESSION" "api-codex" "$PROJECT_DIR" "$worker_cmd"
  ensure_window "$DEV_SESSION" "web-codex" "$WEB_DIR" "$worker_cmd"
  ensure_window "$DEV_SESSION" "test-codex" "$PROJECT_DIR" "$worker_cmd"
  ensure_window "$DEV_SESSION" "ops-log" "$PROJECT_DIR" "$ops_cmd"
  ensure_window "$DEV_SESSION" "browser-codex" "$PROJECT_DIR" "$worker_cmd"
}

setup_bug_session() {
  local worker_cmd="$1"
  local ops_cmd="$2"

  ensure_session "$BUG_SESSION" "$PROJECT_DIR" "$worker_cmd"
  ensure_window "$BUG_SESSION" "repro-codex" "$PROJECT_DIR" "$worker_cmd"
  ensure_window "$BUG_SESSION" "log-codex" "$PROJECT_DIR" "$worker_cmd"
  ensure_window "$BUG_SESSION" "fix-codex" "$PROJECT_DIR" "$worker_cmd"
  ensure_window "$BUG_SESSION" "verify-codex" "$PROJECT_DIR" "$worker_cmd"
  ensure_window "$BUG_SESSION" "ops-log" "$PROJECT_DIR" "$ops_cmd"
  ensure_window "$BUG_SESSION" "browser-codex" "$PROJECT_DIR" "$worker_cmd"
}

resolve_session_name() {
  local raw="${1:-dev}"
  case "$raw" in
    dev)
      printf '%s\n' "$DEV_SESSION"
      ;;
    bug)
      printf '%s\n' "$BUG_SESSION"
      ;;
    *)
      printf '%s\n' "$raw"
      ;;
  esac
}

attach_session() {
  local session
  session="$(resolve_session_name "${1:-dev}")"

  if ! tmux has-session -t "$session" 2>/dev/null; then
    echo "[tmux-codex] 会话不存在: $session" >&2
    exit 1
  fi

  if [[ -n "${TMUX:-}" ]]; then
    tmux switch-client -t "$session"
  else
    tmux attach-session -t "$session"
  fi
}

show_status() {
  local session
  for session in "$DEV_SESSION" "$BUG_SESSION"; do
    if tmux has-session -t "$session" 2>/dev/null; then
      echo "=== $session ==="
      tmux list-windows -t "$session"
    else
      echo "=== $session ==="
      echo "(not created)"
    fi
    echo
  done
}

send_text() {
  local target="$1"
  local text="$2"

  tmux send-keys -t "$target" -l -- "$text"
  tmux send-keys -t "$target" Enter
}

tail_pane() {
  local target="$1"
  local lines="${2:-50}"
  tmux capture-pane -t "$target" -p | tail -n "$lines"
}

stop_sessions() {
  local target="${1:-all}"

  case "$target" in
    all)
      tmux kill-session -t "$DEV_SESSION" 2>/dev/null || true
      tmux kill-session -t "$BUG_SESSION" 2>/dev/null || true
      ;;
    dev|bug)
      tmux kill-session -t "$(resolve_session_name "$target")" 2>/dev/null || true
      ;;
    *)
      tmux kill-session -t "$target" 2>/dev/null || true
      ;;
  esac
}

main() {
  require_tmux

  case "$ACTION" in
    up)
      local worker_cmd
      worker_cmd="$(resolve_worker_cmd)"
      setup_dev_session "$worker_cmd" "$SHELL_CMD"
      setup_bug_session "$worker_cmd" "$SHELL_CMD"
      show_status
      attach_session dev
      ;;
    up-no-attach)
      local worker_cmd
      worker_cmd="$(resolve_worker_cmd)"
      setup_dev_session "$worker_cmd" "$SHELL_CMD"
      setup_bug_session "$worker_cmd" "$SHELL_CMD"
      show_status
      ;;
    status)
      show_status
      ;;
    attach)
      attach_session "${2:-dev}"
      ;;
    send)
      if [[ $# -lt 3 ]]; then
        echo "[tmux-codex] send 需要参数: <session:window> <text>" >&2
        exit 1
      fi
      send_text "$2" "${*:3}"
      ;;
    tail)
      if [[ $# -lt 2 ]]; then
        echo "[tmux-codex] tail 需要参数: <session:window> [lines]" >&2
        exit 1
      fi
      tail_pane "$2" "${3:-50}"
      ;;
    stop)
      stop_sessions "${2:-all}"
      ;;
    -h|--help|help)
      usage
      ;;
    *)
      echo "[tmux-codex] 未知动作: $ACTION" >&2
      usage
      exit 1
      ;;
  esac
}

main "$@"
