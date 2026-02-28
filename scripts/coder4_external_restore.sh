#!/usr/bin/env bash

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "usage: $0 <backup-dir>" >&2
  exit 1
fi

BACKUP_DIR="$1"
MANIFEST="${BACKUP_DIR}/manifest.tsv"
CHECKSUMS="${BACKUP_DIR}/checksums.sha256"

[[ -d "${BACKUP_DIR}" ]] || { echo "[restore] backup dir not found: ${BACKUP_DIR}" >&2; exit 1; }
[[ -f "${MANIFEST}" ]] || { echo "[restore] manifest not found: ${MANIFEST}" >&2; exit 1; }

if [[ -f "${CHECKSUMS}" ]]; then
  (
    cd "${BACKUP_DIR}"
    LC_ALL=C shasum -a 256 -c "${CHECKSUMS##${BACKUP_DIR}/}"
  ) >/dev/null
fi

while IFS=$'\t' read -r status src dst; do
  [[ "${status}" == "status" ]] && continue
  [[ "${status}" == "present" ]] || continue
  if [[ ! -f "${dst}" ]]; then
    echo "[restore] missing backup file: ${dst}" >&2
    exit 1
  fi
  mkdir -p "$(dirname "${src}")"
  cp -p "${dst}" "${src}"
  echo "[restore] restored: ${src}"
done < "${MANIFEST}"

echo "[restore] completed from ${BACKUP_DIR}"
