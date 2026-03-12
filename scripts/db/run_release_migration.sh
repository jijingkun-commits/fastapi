#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
用法:
  bash scripts/db/run_release_migration.sh --message "<message>" [--repo-root <path>] [--skip-upgrade]
  bash scripts/db/run_release_migration.sh --upgrade-only [--repo-root <path>]

发布态 DB migration 统一入口：
1. 解析仓库 Python 解释器
2. 可选：生成 Alembic 迁移脚本（revision --autogenerate）
3. 执行 alembic upgrade head
4. 回显命中的解释器与执行命令
USAGE
}

REPO_ROOT=""
MESSAGE=""
SKIP_UPGRADE=false
UPGRADE_ONLY=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo-root)
      [[ $# -ge 2 ]] || { echo "缺少 --repo-root 参数值" >&2; exit 2; }
      REPO_ROOT="$2"
      shift 2
      ;;
    --message)
      [[ $# -ge 2 ]] || { echo "缺少 --message 参数值" >&2; exit 2; }
      MESSAGE="$2"
      shift 2
      ;;
    --skip-upgrade)
      SKIP_UPGRADE=true
      shift
      ;;
    --upgrade-only)
      UPGRADE_ONLY=true
      shift
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

if [[ "$UPGRADE_ONLY" == false && -z "$MESSAGE" ]]; then
  echo "缺少必填参数: --message" >&2
  usage >&2
  exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
if [[ -z "$REPO_ROOT" ]]; then
  REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd -P)"
else
  REPO_ROOT="$(cd "$REPO_ROOT" && pwd -P)"
fi

PYTHON_BIN="$(bash "$REPO_ROOT/scripts/repo_python.sh" --repo-root "$REPO_ROOT")"

cd "$REPO_ROOT"

echo "[run_release_migration] repo_root=$REPO_ROOT"
echo "[run_release_migration] python=$PYTHON_BIN"

if [[ "$UPGRADE_ONLY" == false ]]; then
  echo "[run_release_migration] cmd=$PYTHON_BIN -m alembic revision --autogenerate -m $MESSAGE"
  "$PYTHON_BIN" -m alembic revision --autogenerate -m "$MESSAGE"
fi

if [[ "$SKIP_UPGRADE" == false ]]; then
  echo "[run_release_migration] cmd=$PYTHON_BIN -m alembic upgrade head"
  "$PYTHON_BIN" -m alembic upgrade head
fi
