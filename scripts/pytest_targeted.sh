#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
用法: bash scripts/pytest_targeted.sh [--repo-root <path>] [pytest args...]

开发期定向 pytest 入口：
- 固定注入 --no-cov
- 禁止与 --cov* 参数混用
- Python 解释器统一通过 scripts/repo_python.sh 解析
USAGE
}

REPO_ROOT=""
PYTEST_ARGS=()

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
      PYTEST_ARGS+=("$1")
      shift
      ;;
  esac
done

for arg in "${PYTEST_ARGS[@]}"; do
  case "$arg" in
    --cov|--cov=*|--cov-*)
      echo "PYTEST_TARGETED_COVERAGE_MIXED: 开发期定向入口禁止与 coverage 参数混用，请改走最终收口命令" >&2
      exit 2
      ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_PYTHON_CMD=("bash" "$SCRIPT_DIR/repo_python.sh")
if [[ -n "$REPO_ROOT" ]]; then
  REPO_PYTHON_CMD+=("--repo-root" "$REPO_ROOT")
fi
PYTHON_BIN="$(${REPO_PYTHON_CMD[@]})"

exec "$PYTHON_BIN" -m pytest --no-cov "${PYTEST_ARGS[@]}"
