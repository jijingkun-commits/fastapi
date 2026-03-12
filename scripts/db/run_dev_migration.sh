#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
用法: bash scripts/db/run_dev_migration.sh [--repo-root <path>]

开发态 DB migration 统一入口：
1. 解析仓库 Python 解释器
2. 执行 scripts/db/sync_database.py
3. 回显命中的解释器与执行命令
USAGE
}

REPO_ROOT=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo-root)
      [[ $# -ge 2 ]] || { echo "缺少 --repo-root 参数值" >&2; exit 2; }
      REPO_ROOT="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "未知参数: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
if [[ -z "$REPO_ROOT" ]]; then
  REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd -P)"
else
  REPO_ROOT="$(cd "$REPO_ROOT" && pwd -P)"
fi

PYTHON_BIN="$(bash "$REPO_ROOT/scripts/repo_python.sh" --repo-root "$REPO_ROOT")"

echo "[run_dev_migration] repo_root=$REPO_ROOT"
echo "[run_dev_migration] python=$PYTHON_BIN"
echo "[run_dev_migration] cmd=$PYTHON_BIN scripts/db/sync_database.py"

cd "$REPO_ROOT"
"$PYTHON_BIN" scripts/db/sync_database.py
