#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(git rev-parse --show-toplevel 2>/dev/null || pwd -P)"
cd "$ROOT_DIR"

eval "$(bash scripts/vk_ports.sh --export)"

PRIMARY_WORKTREE="$(git worktree list --porcelain | awk '/^worktree /{print $2; exit}')"

RUN_DIR="$ROOT_DIR/.vibe/run"
BACKEND_PID_FILE="$RUN_DIR/backend.pid"
WEB_PID_FILE="$RUN_DIR/web.pid"
BACKEND_LOG_FILE="$RUN_DIR/backend.log"
WEB_LOG_FILE="$RUN_DIR/web.log"

mkdir -p "$RUN_DIR"

ACTION="${1:-up}"

load_env_file() {
  local env_file="$1"
  if [[ -f "$env_file" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "$env_file"
    set +a
  fi
}

read_pid() {
  local pid_file="$1"
  if [[ -f "$pid_file" ]]; then
    cat "$pid_file"
  fi
}

is_pid_running() {
  local pid="$1"
  if [[ -z "$pid" ]]; then
    return 1
  fi
  kill -0 "$pid" >/dev/null 2>&1
}

is_port_listening() {
  local port="$1"
  lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1
}

ensure_port_available() {
  local service_name="$1"
  local port="$2"
  if is_port_listening "$port"; then
    echo "[vk_dev] ${service_name} 端口 ${port} 已被占用，请先释放或改用 VK_BACKEND_PORT/VK_FRONTEND_PORT" >&2
    return 1
  fi
}

resolve_uvicorn_cmd() {
  local candidate
  local runtime_venv
  runtime_venv="${VK_RUNTIME_VENV:-$ROOT_DIR/.vibe/venv}"

  local -a candidates=(
    "$ROOT_DIR/venv/bin/uvicorn"
    "$ROOT_DIR/.venv/bin/uvicorn"
    "${runtime_venv}/bin/uvicorn"
  )

  if [[ -n "${VK_SHARED_VENV_PATH:-}" ]]; then
    candidates+=("${VK_SHARED_VENV_PATH}/bin/uvicorn")
  fi
  if [[ -n "$PRIMARY_WORKTREE" ]]; then
    candidates+=("${PRIMARY_WORKTREE}/venv/bin/uvicorn")
  fi

  for candidate in "${candidates[@]}"; do
    if [[ -x "$candidate" ]]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done

  if command -v uvicorn >/dev/null 2>&1; then
    command -v uvicorn
    return 0
  fi

  return 1
}

start_backend() {
  local current_pid
  current_pid="$(read_pid "$BACKEND_PID_FILE")"
  if is_pid_running "$current_pid"; then
    echo "[vk_dev] backend already running (pid=${current_pid})"
    return 0
  fi

  ensure_port_available "backend" "$VK_BACKEND_PORT"

  load_env_file "$ROOT_DIR/.env.dev"
  load_env_file "$ROOT_DIR/.env.vk.local"

  local uvicorn_cmd
  if ! uvicorn_cmd="$(resolve_uvicorn_cmd)"; then
    echo "[vk_dev] 未找到 uvicorn，请先准备共享或本地 venv（建议先执行 bash scripts/vk_setup.sh）。" >&2
    return 1
  fi

  export ENV="${ENV:-dev}"
  export API_PUBLIC_URL="http://127.0.0.1:${VK_BACKEND_PORT}/public"
  export TEST_BACKEND_PORT="$VK_BACKEND_PORT"
  export TEST_FRONTEND_PORT="$VK_FRONTEND_PORT"
  export LIVE_API_BASE="http://127.0.0.1:${VK_BACKEND_PORT}/api/v1"
  export E2E_API_BASE="http://127.0.0.1:${VK_BACKEND_PORT}"

  nohup "$uvicorn_cmd" app.main:app --reload --host 127.0.0.1 --port "$VK_BACKEND_PORT" >"$BACKEND_LOG_FILE" 2>&1 &
  echo $! > "$BACKEND_PID_FILE"

  echo "[vk_dev] backend started: http://127.0.0.1:${VK_BACKEND_PORT} (pid=$(cat "$BACKEND_PID_FILE"))"
}

start_web() {
  local current_pid
  current_pid="$(read_pid "$WEB_PID_FILE")"
  if is_pid_running "$current_pid"; then
    echo "[vk_dev] web already running (pid=${current_pid})"
    return 0
  fi

  ensure_port_available "web" "$VK_FRONTEND_PORT"

  local web_cmd=( )
  if command -v pnpm >/dev/null 2>&1; then
    web_cmd=(pnpm dev -p "$VK_FRONTEND_PORT")
  elif command -v npm >/dev/null 2>&1; then
    web_cmd=(npm run dev -- -p "$VK_FRONTEND_PORT")
  else
    echo "[vk_dev] 未找到 pnpm/npm，请先安装 Node.js 依赖。" >&2
    return 1
  fi

  load_env_file "$ROOT_DIR/web/.env.local"
  load_env_file "$ROOT_DIR/web/.env.vk.local"

  (
    cd "$ROOT_DIR/web"
    export NEXT_PUBLIC_API_BASE_URL="http://127.0.0.1:${VK_BACKEND_PORT}"
    export E2E_API_BASE="http://127.0.0.1:${VK_BACKEND_PORT}"
    export PLAYWRIGHT_BASE_URL="http://127.0.0.1:${VK_FRONTEND_PORT}"
    export PLAYWRIGHT_FRONTEND_PORT="$VK_FRONTEND_PORT"
    nohup "${web_cmd[@]}" >"$WEB_LOG_FILE" 2>&1 &
    echo $! > "$WEB_PID_FILE"
  )

  echo "[vk_dev] web started: http://127.0.0.1:${VK_FRONTEND_PORT} (pid=$(cat "$WEB_PID_FILE"))"
}

show_status() {
  local backend_pid web_pid
  backend_pid="$(read_pid "$BACKEND_PID_FILE")"
  web_pid="$(read_pid "$WEB_PID_FILE")"

  echo "[vk_dev] branch=${VK_GIT_BRANCH} (main=${VK_IS_MAIN_BRANCH})"
  echo "[vk_dev] backend_url=http://127.0.0.1:${VK_BACKEND_PORT}"
  if is_pid_running "$backend_pid"; then
    echo "[vk_dev] backend=running pid=${backend_pid}"
  else
    echo "[vk_dev] backend=stopped"
  fi

  echo "[vk_dev] frontend_url=http://127.0.0.1:${VK_FRONTEND_PORT}"
  if is_pid_running "$web_pid"; then
    echo "[vk_dev] web=running pid=${web_pid}"
  else
    echo "[vk_dev] web=stopped"
  fi

  echo "[vk_dev] logs: $BACKEND_LOG_FILE, $WEB_LOG_FILE"
}

print_usage() {
  cat <<USAGE
Usage: bash scripts/vk_dev.sh [up|backend|web|status]
  up       启动 backend + web
  backend  仅启动 backend
  web      仅启动 web
  status   查看运行状态
USAGE
}

case "$ACTION" in
  up)
    start_backend
    start_web
    show_status
    ;;
  backend)
    start_backend
    show_status
    ;;
  web)
    start_web
    show_status
    ;;
  status)
    show_status
    ;;
  *)
    print_usage
    exit 1
    ;;
esac
