#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(git rev-parse --show-toplevel)"
cd "$ROOT_DIR"

force="${1:-}"
need_rules=0
need_commands=0

has_changes() {
  local pathspec="$1"
  if git diff --name-only -- "$pathspec" | grep -q .; then
    return 0
  fi
  if git diff --cached --name-only -- "$pathspec" | grep -q .; then
    return 0
  fi
  if git ls-files --others --exclude-standard -- "$pathspec" | grep -q .; then
    return 0
  fi
  return 1
}

if [[ "$force" == "--force" ]]; then
  need_rules=1
  need_commands=1
else
  if has_changes ".cursor/rules/*.mdc"; then
    need_rules=1
  fi
  if has_changes ".cursor/commands/*.md"; then
    need_commands=1
  fi
fi

if [[ $need_rules -eq 0 && $need_commands -eq 0 ]]; then
  exit 0
fi

if [[ $need_rules -eq 1 && $need_commands -eq 1 ]]; then
  python3 scripts/sync_rules_to_cc.py >/dev/null
elif [[ $need_rules -eq 1 ]]; then
  python3 scripts/sync_rules_to_cc.py --only rules >/dev/null
else
  python3 scripts/sync_rules_to_cc.py --only commands >/dev/null
fi

echo "[sync-hooks] cursor mirrors synced"
