#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
用法: bash scripts/repo_python.sh [--repo-root <path>]

输出当前仓库应使用的 Python 解释器绝对路径。
优先级: VK_RUNTIME_VENV -> venv -> .venv -> .vibe/venv -> python3 -> python
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

if [[ -z "$REPO_ROOT" ]]; then
  REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd -P)"
fi
REPO_ROOT="$(cd "$REPO_ROOT" && pwd -P)"

add_candidate() {
  local base="$1"
  [[ -n "$base" ]] || return 0
  if [[ "$base" == */bin/python ]]; then
    printf '%s\n' "$base"
    return 0
  fi
  printf '%s/bin/python\n' "${base%/}"
}

candidates=()
if [[ -n "${VK_RUNTIME_VENV:-}" ]]; then
  if [[ "$VK_RUNTIME_VENV" = /* ]]; then
    candidates+=("$(add_candidate "$VK_RUNTIME_VENV")")
  else
    candidates+=("$(add_candidate "$REPO_ROOT/$VK_RUNTIME_VENV")")
  fi
fi
candidates+=("$(add_candidate "$REPO_ROOT/venv")")
candidates+=("$(add_candidate "$REPO_ROOT/.venv")")
candidates+=("$(add_candidate "$REPO_ROOT/.vibe/venv")")

seen='|'
for candidate in "${candidates[@]}"; do
  if [[ "$seen" == *"|$candidate|"* ]]; then
    continue
  fi
  seen+="$candidate|"
  if [[ -x "$candidate" ]]; then
    printf '%s\n' "$candidate"
    exit 0
  fi
done

if system_python="$(command -v python3 2>/dev/null)" && [[ -n "$system_python" ]]; then
  printf '%s\n' "$system_python"
  exit 0
fi

if system_python="$(command -v python 2>/dev/null)" && [[ -n "$system_python" ]]; then
  printf '%s\n' "$system_python"
  exit 0
fi

echo "未找到可用 Python 解释器：请准备 VK_RUNTIME_VENV/venv/.venv/.vibe/venv，或安装系统 python3" >&2
exit 1
