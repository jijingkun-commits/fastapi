#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
用法: bash scripts/jjk_commit.sh [--verify-cmd <command>] [--message <msg>] [--base-branch <name>]

基于当前 worktree 输出一条“可在任意目录执行”的提交并收口命令串。
默认只输出，不直接执行。

参数：
- --verify-cmd   可选；本次交付的验证命令，默认 `:`（不额外执行验证）
- --message      可选；若当前有未提交改动，默认自动生成 `chore: deliver <branch>`
- --base-branch  可选；默认 master

门禁：
- 禁止 detached HEAD
- 禁止当前就在 base branch
- 禁止 delivery 上下文非 idle
- 禁止 base branch 不可达
- 禁止“无未提交改动且分支也没有领先提交”
USAGE
}

die() {
  echo "$1" >&2
  exit 1
}

quote() {
  printf '%q' "$1"
}

PY_HASH_SCRIPT=$'import hashlib, sys\nprint(hashlib.sha256(sys.stdin.buffer.read()).hexdigest())'

BASE_BRANCH="master"
VERIFY_CMD=""
COMMIT_MESSAGE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --verify-cmd)
      [[ $# -ge 2 ]] || die "COMMIT_ARG_MISSING: 缺少 --verify-cmd 参数值"
      VERIFY_CMD="$2"
      shift 2
      ;;
    --message)
      [[ $# -ge 2 ]] || die "COMMIT_ARG_MISSING: 缺少 --message 参数值"
      COMMIT_MESSAGE="$2"
      shift 2
      ;;
    --base-branch)
      [[ $# -ge 2 ]] || die "COMMIT_ARG_MISSING: 缺少 --base-branch 参数值"
      BASE_BRANCH="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      die "COMMIT_ARG_UNKNOWN: 未知参数 $1"
      ;;
  esac
done

if [[ -z "$VERIFY_CMD" ]]; then
  VERIFY_CMD=:
fi

CURRENT_WT="$(git rev-parse --show-toplevel 2>/dev/null || true)"
[[ -n "$CURRENT_WT" ]] || die "COMMIT_NOT_GIT_REPO: 当前目录不在 Git worktree 中"
CURRENT_WT="$(cd "$CURRENT_WT" && pwd -P)"

CURRENT_BRANCH="$(git branch --show-current 2>/dev/null || true)"
[[ -n "$CURRENT_BRANCH" ]] || die "COMMIT_BRANCH_INVALID: 当前为 detached HEAD，无法自动识别目标分支"
[[ "$CURRENT_BRANCH" != "$BASE_BRANCH" ]] || die "COMMIT_BRANCH_INVALID: 当前分支就是 ${BASE_BRANCH}，禁止生成交付命令"

CURRENT_HEAD="$(git -C "$CURRENT_WT" rev-parse HEAD 2>/dev/null || true)"
[[ -n "$CURRENT_HEAD" ]] || die "COMMIT_HEAD_MISSING: 无法解析当前 HEAD"

COMMON_GIT_DIR="$(git -C "$CURRENT_WT" rev-parse --git-common-dir 2>/dev/null || true)"
[[ -n "$COMMON_GIT_DIR" ]] || die "COMMIT_COMMON_DIR_MISSING: 无法解析 git common dir"
if [[ "$COMMON_GIT_DIR" != /* ]]; then
  COMMON_GIT_DIR="$(cd "$CURRENT_WT" && cd "$COMMON_GIT_DIR" && pwd -P)"
fi
REPO_ROOT="$(cd "$COMMON_GIT_DIR/.." && pwd -P)"
ENGINE_SCRIPT="$REPO_ROOT/scripts/coder4/git-delivery-engine.sh"
[[ -x "$ENGINE_SCRIPT" ]] || die "COMMIT_ENGINE_MISSING: 缺少 shared delivery engine ${ENGINE_SCRIPT}"

PYTHON_BIN="$(bash "$REPO_ROOT/scripts/repo_python.sh" --repo-root "$CURRENT_WT")"
[[ -x "$PYTHON_BIN" ]] || die "COMMIT_PYTHON_MISSING: 无法解析仓库 Python 解释器"

if ! git -C "$REPO_ROOT" rev-parse --verify "$BASE_BRANCH" >/dev/null 2>&1; then
  die "DELIVERY_BASE_UNAVAILABLE: 基线分支 ${BASE_BRANCH} 不存在"
fi

STATUS_JSON="$(bash "$ENGINE_SCRIPT" status --source-branch "$CURRENT_BRANCH" --source-worktree "$CURRENT_WT" --base-branch "$BASE_BRANCH")"
DELIVERY_STATUS="$(printf '%s' "$STATUS_JSON" | "$PYTHON_BIN" -c 'import json,sys; print(json.load(sys.stdin).get("status", ""))')"
[[ "$DELIVERY_STATUS" == "idle" ]] || die "DELIVERY_NOT_IN_PROGRESS: 当前 delivery 状态=${DELIVERY_STATUS}，请先处理进行中的上下文"

bash "$ENGINE_SCRIPT" prepare-base --source-branch "$CURRENT_BRANCH" --source-worktree "$CURRENT_WT" --base-branch "$BASE_BRANCH" >/dev/null

HAS_PENDING=false
if [[ -n "$(git -C "$CURRENT_WT" status --porcelain=v1)" ]]; then
  HAS_PENDING=true
fi

AHEAD_COUNT="$(git -C "$CURRENT_WT" rev-list --count "${BASE_BRANCH}..${CURRENT_BRANCH}" 2>/dev/null || echo 0)"
if [[ "$HAS_PENDING" == false && "$AHEAD_COUNT" -eq 0 ]]; then
  die "COMMIT_NOTHING_TO_DELIVER: 当前既无未提交改动，分支相对 ${BASE_BRANCH} 也没有领先提交"
fi

if [[ "$HAS_PENDING" == true && -z "$COMMIT_MESSAGE" ]]; then
  COMMIT_MESSAGE="chore: deliver ${CURRENT_BRANCH}"
fi

STATUS_SHA="$(git -C "$CURRENT_WT" status --porcelain=v1 -z | "$PYTHON_BIN" -c "$PY_HASH_SCRIPT")"

WT_Q="$(quote "$CURRENT_WT")"
BRANCH_Q="$(quote "$CURRENT_BRANCH")"
HEAD_Q="$(quote "$CURRENT_HEAD")"
BASE_Q="$(quote "$BASE_BRANCH")"
ENGINE_Q="$(quote "$ENGINE_SCRIPT")"
PY_Q="$(quote "$PYTHON_BIN")"
MSG_Q="$(quote "$COMMIT_MESSAGE")"
HASH_SCRIPT_Q="$(quote "$PY_HASH_SCRIPT")"
STATUS_SHA_Q="$(quote "$STATUS_SHA")"
VERIFY_Q="$(quote "$VERIFY_CMD")"

BODY="cd ${WT_Q} && test \"\$(git branch --show-current)\" = ${BRANCH_Q} && test \"\$(git rev-parse HEAD)\" = ${HEAD_Q} && test \"\$(git status --porcelain=v1 -z | ${PY_Q} -c ${HASH_SCRIPT_Q})\" = ${STATUS_SHA_Q} && bash -lc ${VERIFY_Q} && test \"\$(git status --porcelain=v1 -z | ${PY_Q} -c ${HASH_SCRIPT_Q})\" = ${STATUS_SHA_Q} && git diff --check"
if [[ "$HAS_PENDING" == true ]]; then
  BODY+=" && git add -A && git commit -m ${MSG_Q}"
fi
BODY+=" && bash ${ENGINE_Q} merge --source-branch ${BRANCH_Q} --source-worktree ${WT_Q} --base-branch ${BASE_Q}"

printf 'bash -lc %s\n' "$(quote "$BODY")"
