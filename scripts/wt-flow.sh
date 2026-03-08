#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_RELATIVE_PATH="scripts/coder4/wt-flow.sh"
TARGET_SCRIPT="${SCRIPT_DIR}/coder4/wt-flow.sh"

if [[ ! -f "${TARGET_SCRIPT}" ]]; then
  echo "[wt-flow-wrapper] ERROR: 当前脚本只是 wrapper，不是实体脚本。" >&2
  echo "[wt-flow-wrapper] ERROR: 单一真理源是 ${TARGET_RELATIVE_PATH}。" >&2
  echo "[wt-flow-wrapper] ERROR: 若需脱离仓库调试，请直接使用实体脚本 ${TARGET_RELATIVE_PATH}。" >&2
  echo "[wt-flow-wrapper] ERROR: 当前缺失目标=${TARGET_SCRIPT}" >&2
  exit 1
fi

exec "${TARGET_SCRIPT}" "$@"
