#!/usr/bin/env bash
# 自动同步 Cursor 规则和命令到 Claude/Codex 镜像。
# 由 Claude Code PostToolUse hook 触发；当 payload 无 file_path 时回退到 git 状态探测。
set -euo pipefail

ROOT_DIR="$(git -C "$(dirname "$0")" rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT_DIR"

input="$(cat 2>/dev/null || true)"
if [[ -z "$input" ]]; then
  input="{}"
fi

touched_paths="$(
  printf '%s' "$input" | python3 - <<'PY'
import json
import sys

paths = set()
try:
    data = json.load(sys.stdin)
except Exception:
    data = {}

tool_input = data.get("tool_input", {})
if isinstance(tool_input, dict):
    for key in ("file_path", "path"):
        value = tool_input.get(key)
        if isinstance(value, str) and value:
            paths.add(value)
    value = tool_input.get("paths")
    if isinstance(value, list):
        for item in value:
            if isinstance(item, str) and item:
                paths.add(item)
            elif isinstance(item, dict):
                candidate = item.get("file_path") or item.get("path")
                if isinstance(candidate, str) and candidate:
                    paths.add(candidate)

for path in sorted(paths):
    print(path)
PY
)
"

need_rules=0
need_commands=0

if [[ -n "$touched_paths" ]]; then
  while IFS= read -r path; do
    if [[ "$path" == */.cursor/rules/*.mdc ]]; then
      need_rules=1
    fi
    if [[ "$path" == */.cursor/commands/*.md ]]; then
      need_commands=1
    fi
  done <<< "$touched_paths"
fi

# 回退探测：兼容 MultiEdit/Write 等 payload 不含 file_path 的场景
if [[ $need_rules -eq 0 ]]; then
  if git status --porcelain -- ".cursor/rules/*.mdc" | grep -q .; then
    need_rules=1
  fi
fi

if [[ $need_commands -eq 0 ]]; then
  if git status --porcelain -- ".cursor/commands/*.md" | grep -q .; then
    need_commands=1
  fi
fi

if [[ $need_rules -eq 1 ]]; then
  python3 scripts/sync_rules_to_cc.py --only rules >/dev/null 2>&1
  echo "rules synced"
fi

if [[ $need_commands -eq 1 ]]; then
  output="$(python3 scripts/sync_rules_to_cc.py --only commands --skip-codex-prompts 2>&1)"
  if [[ "$output" == *"警告:"* ]]; then
    echo "$output" | grep "警告:"
  fi
  echo "commands synced"
fi
