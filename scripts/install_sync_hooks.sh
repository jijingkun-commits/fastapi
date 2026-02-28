#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

chmod +x \
  .githooks/sync_cursor_mirrors.sh \
  .githooks/pre-commit \
  .githooks/post-checkout \
  .githooks/post-merge \
  .githooks/post-rewrite

git config core.hooksPath .githooks
echo "Installed Git hooks path: $(git config --get core.hooksPath)"
