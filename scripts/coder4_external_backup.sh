#!/usr/bin/env bash

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="${1:-${REPO_ROOT}/.omc/backup/external-${TIMESTAMP}}"
MANIFEST="${BACKUP_DIR}/manifest.tsv"
CHECKSUMS="${BACKUP_DIR}/checksums.sha256"

FILES=(
  "~/.openclaw-dev/openclaw.json"
  "~/.openclaw-dev/cron/jobs.json"
  "~/.openclaw/workspace-dev/WORKFLOW_AUTO.md"
  "~/.openclaw/workspace-dev/VK_AGENT_PROMPTS.md"
  "~/.openclaw/workspace-dev/state/coder4_cron_state.json"
)

mkdir -p "${BACKUP_DIR}/files"
echo -e "status\tsource\tbackup" > "${MANIFEST}"

for raw in "${FILES[@]}"; do
  src="${raw/#\~/${HOME}}"
  rel="${src#/}"
  dst="${BACKUP_DIR}/files/${rel}"
  if [[ -f "${src}" ]]; then
    mkdir -p "$(dirname "${dst}")"
    cp -p "${src}" "${dst}"
    echo -e "present\t${src}\t${dst}" >> "${MANIFEST}"
  else
    echo -e "missing\t${src}\t-" >> "${MANIFEST}"
  fi
done

while IFS= read -r src; do
  [[ -n "${src}" ]] || continue
  rel="${src#/}"
  dst="${BACKUP_DIR}/files/${rel}"
  mkdir -p "$(dirname "${dst}")"
  cp -p "${src}" "${dst}"
  echo -e "present\t${src}\t${dst}" >> "${MANIFEST}"
done < <(
  find "${REPO_ROOT}/docs/内部参考/任务拆解" \
    -mindepth 3 -maxdepth 3 -type f -name "coder4_scope_request.json" 2>/dev/null \
    | LC_ALL=C sort
)

> "${CHECKSUMS}"
while IFS=$'\t' read -r status _src dst; do
  [[ "${status}" == "status" ]] && continue
  if [[ "${status}" == "present" ]]; then
    LC_ALL=C shasum -a 256 "${dst}" >> "${CHECKSUMS}"
  fi
done < "${MANIFEST}"

echo "[backup] done: ${BACKUP_DIR}"
echo "[backup] manifest: ${MANIFEST}"
echo "[backup] checksums: ${CHECKSUMS}"
