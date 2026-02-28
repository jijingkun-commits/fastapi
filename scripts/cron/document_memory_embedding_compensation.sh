#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

LIMIT="${DOCUMENT_MEMORY_EMBEDDING_BATCH_SIZE:-200}"
STATUS_FILTER="${DOCUMENT_MEMORY_EMBEDDING_STATUS_FILTER:-pending,failed}"
MAX_RETRY="${DOCUMENT_MEMORY_EMBEDDING_MAX_RETRY:-3}"

venv/bin/python scripts/memory/rebuild_document_embeddings.py \
  --limit "$LIMIT" \
  --status "$STATUS_FILTER" \
  --max-retry "$MAX_RETRY"
