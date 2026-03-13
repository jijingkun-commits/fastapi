#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
用法: bash scripts/jjk_deleteworktree.sh [--base-branch <name>]

基于当前 worktree 输出一条“可在任意目录执行”的删除命令串。
默认只输出，不直接执行删除。

门禁：
- 禁止主仓库根 worktree / master worktree
- 禁止 detached HEAD
- 禁止脏 worktree
- 禁止未并入 base branch（默认 master）
USAGE
}

die() {
  echo "$1" >&2
  exit 1
}

quote() {
  printf '%q' "$1"
}

find_branch_worktree() {
  local repo_root="$1"
  local branch_name="$2"
  local target_ref="refs/heads/${branch_name}"
  local line=""
  local worktree_path=""
  local worktree_branch=""

  while IFS= read -r line || [[ -n "$line" ]]; do
    if [[ -z "$line" ]]; then
      if [[ -n "$worktree_path" && "$worktree_branch" == "$target_ref" ]]; then
        printf '%s\n' "$worktree_path"
        return 0
      fi
      worktree_path=""
      worktree_branch=""
      continue
    fi

    case "$line" in
      worktree\ *)
        worktree_path="${line#worktree }"
        ;;
      branch\ *)
        worktree_branch="${line#branch }"
        ;;
    esac
  done < <(git -C "$repo_root" worktree list --porcelain)

  if [[ -n "$worktree_path" && "$worktree_branch" == "$target_ref" ]]; then
    printf '%s\n' "$worktree_path"
    return 0
  fi

  return 1
}

BASE_BRANCH="master"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --base-branch)
      [[ $# -ge 2 ]] || die "DELETE_WORKTREE_ARG_MISSING: 缺少 --base-branch 参数值"
      BASE_BRANCH="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      die "DELETE_WORKTREE_ARG_UNKNOWN: 未知参数 $1"
      ;;
  esac
done

CURRENT_WT="$(git rev-parse --show-toplevel 2>/dev/null || true)"
[[ -n "$CURRENT_WT" ]] || die "DELETE_WORKTREE_NOT_GIT_REPO: 当前目录不在 Git worktree 中"
CURRENT_WT="$(cd "$CURRENT_WT" && pwd -P)"

CURRENT_BRANCH="$(git branch --show-current 2>/dev/null || true)"
[[ -n "$CURRENT_BRANCH" ]] || die "DELETE_WORKTREE_BRANCH_INVALID: 当前为 detached HEAD，无法自动识别要删除的分支"
[[ "$CURRENT_BRANCH" != "$BASE_BRANCH" ]] || die "DELETE_WORKTREE_PRIMARY_FORBIDDEN: 当前分支就是 ${BASE_BRANCH}，禁止生成删除命令"

COMMON_GIT_DIR="$(git rev-parse --git-common-dir 2>/dev/null || true)"
[[ -n "$COMMON_GIT_DIR" ]] || die "DELETE_WORKTREE_COMMON_DIR_MISSING: 无法解析 git common dir"
if [[ "$COMMON_GIT_DIR" != /* ]]; then
  COMMON_GIT_DIR="$(cd "$CURRENT_WT" && cd "$COMMON_GIT_DIR" && pwd -P)"
fi
REPO_ROOT="$(cd "$COMMON_GIT_DIR/.." && pwd -P)"

[[ "$CURRENT_WT" != "$REPO_ROOT" ]] || die "DELETE_WORKTREE_PRIMARY_FORBIDDEN: 当前 worktree 是主仓库根工作区，禁止删除"

if [[ -n "$(git -C "$CURRENT_WT" status --porcelain)" ]]; then
  die "DELETE_WORKTREE_DIRTY: 当前 worktree 有未提交改动，禁止生成删除命令"
fi

CURRENT_HEAD="$(git -C "$CURRENT_WT" rev-parse HEAD 2>/dev/null || true)"
[[ -n "$CURRENT_HEAD" ]] || die "DELETE_WORKTREE_HEAD_MISSING: 无法解析当前 HEAD"

if ! git -C "$REPO_ROOT" rev-parse --verify "$BASE_BRANCH" >/dev/null 2>&1; then
  die "DELETE_WORKTREE_BASE_MISSING: 基线分支 ${BASE_BRANCH} 不存在"
fi

if ! git -C "$REPO_ROOT" merge-base --is-ancestor "$CURRENT_HEAD" "$BASE_BRANCH"; then
  die "DELETE_WORKTREE_NOT_MERGED: 当前 HEAD 尚未并入 ${BASE_BRANCH}，请先完成收口"
fi

WORKTREE_OWNER_COUNT="$(git worktree list --porcelain | awk -v branch="refs/heads/${CURRENT_BRANCH}" '
  $1 == "branch" && $2 == branch { count += 1 }
  END { print count + 0 }
')"
if [[ "$WORKTREE_OWNER_COUNT" -gt 1 ]]; then
  die "DELETE_WORKTREE_BRANCH_INVALID: 分支 ${CURRENT_BRANCH} 仍被其他 worktree 持有"
fi

BRANCH_DELETE_WT="$(find_branch_worktree "$REPO_ROOT" "$BASE_BRANCH" || true)"
[[ -n "$BRANCH_DELETE_WT" ]] || die "DELETE_WORKTREE_BASE_CONTEXT_MISSING: 未找到检出 ${BASE_BRANCH} 的 worktree，无法安全生成 branch -d 命令"
BRANCH_DELETE_WT="$(cd "$BRANCH_DELETE_WT" && pwd -P)"

REPO_Q="$(quote "$REPO_ROOT")"
WT_Q="$(quote "$CURRENT_WT")"
BRANCH_Q="$(quote "$CURRENT_BRANCH")"
HEAD_Q="$(quote "$CURRENT_HEAD")"
BASE_Q="$(quote "$BASE_BRANCH")"
BRANCH_DELETE_WT_Q="$(quote "$BRANCH_DELETE_WT")"

printf 'git -C %s rev-parse --verify %s >/dev/null && git -C %s merge-base --is-ancestor %s %s && test -z "$(git -C %s status --porcelain 2>/dev/null)" && test "$(git -C %s branch --show-current 2>/dev/null)" = %s && git -C %s worktree remove %s && git -C %s branch -d %s\n' \
  "$REPO_Q" "$BASE_Q" "$REPO_Q" "$HEAD_Q" "$BASE_Q" "$WT_Q" "$BRANCH_DELETE_WT_Q" "$BASE_Q" "$REPO_Q" "$WT_Q" "$BRANCH_DELETE_WT_Q" "$BRANCH_Q"
