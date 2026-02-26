#!/usr/bin/env bash
# worktree 隔离开发生命周期管理脚本。
# 用法:
#   wt-flow.sh create <branch-slug> [base-branch]
#   wt-flow.sh merge  [--no-cleanup]
#   wt-flow.sh cleanup
#   wt-flow.sh status
#   wt-flow.sh guard   # 检查是否在 master 上，返回 0=安全 1=在 master

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"
WT_BASE="${REPO_ROOT}/.worktrees"
STATE_FILE="${REPO_ROOT}/.omc/state/wt-flow-state.json"

# --- 工具函数 ---

_log()  { echo "[wt-flow] $*"; }
_err()  { echo "[wt-flow] ERROR: $*" >&2; }
_die()  { _err "$@"; exit 1; }

_ensure_clean() {
  if ! git diff --quiet || ! git diff --cached --quiet; then
    _die "工作区有未提交的变更，请先 commit 或 stash"
  fi
}

_save_state() {
  local branch="$1" worktree="$2" base="$3"
  mkdir -p "$(dirname "$STATE_FILE")"
  cat > "$STATE_FILE" <<EOF
{
  "branch": "$branch",
  "worktree": "$worktree",
  "base_branch": "$base",
  "created_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
}

_read_state() {
  if [[ ! -f "$STATE_FILE" ]]; then
    _die "没有活跃的 worktree 会话，请先执行 create"
  fi
  # 输出 JSON 内容供调用方解析
  cat "$STATE_FILE"
}

_clear_state() {
  rm -f "$STATE_FILE"
}

# --- 命令: create ---

cmd_create() {
  local slug="${1:?用法: wt-flow.sh create <branch-slug> [base-branch]}"
  local base="${2:-master}"

  _ensure_clean

  local branch="feature/${slug}"
  local wt_path="${WT_BASE}/${slug}"

  if git show-ref --verify --quiet "refs/heads/${branch}" 2>/dev/null; then
    _die "分支 ${branch} 已存在，请换一个名字或先清理"
  fi

  if [[ -d "$wt_path" ]]; then
    _die "worktree 路径 ${wt_path} 已存在"
  fi

  # 确保基准分支是最新的
  _log "从 ${base} 创建分支 ${branch} ..."
  git fetch origin "${base}" 2>/dev/null || true
  git worktree add -b "${branch}" "${wt_path}" "${base}"

  _save_state "$branch" "$wt_path" "$base"

  _log "worktree 已创建:"
  _log "  分支:    ${branch}"
  _log "  路径:    ${wt_path}"
  _log "  基准:    ${base}"
  echo "${wt_path}"
}

# --- 命令: merge ---

cmd_merge() {
  local no_cleanup=false
  [[ "${1:-}" == "--no-cleanup" ]] && no_cleanup=true

  local state
  state="$(_read_state)"
  local branch wt_path base_branch
  branch="$(echo "$state" | grep '"branch"' | sed 's/.*: *"\(.*\)".*/\1/')"
  wt_path="$(echo "$state" | grep '"worktree"' | sed 's/.*: *"\(.*\)".*/\1/')"
  base_branch="$(echo "$state" | grep '"base_branch"' | sed 's/.*: *"\(.*\)".*/\1/')"

  # 检查 worktree 内是否有未提交变更
  if ! git -C "$wt_path" diff --quiet || ! git -C "$wt_path" diff --cached --quiet; then
    _die "worktree ${wt_path} 有未提交的变更，请先 commit"
  fi

  # 检查分支是否有新提交
  local ahead
  ahead="$(git rev-list --count "${base_branch}..${branch}" 2>/dev/null || echo 0)"
  if [[ "$ahead" -eq 0 ]]; then
    _log "分支 ${branch} 没有新提交，跳过合并"
    if [[ "$no_cleanup" == false ]]; then
      cmd_cleanup
    fi
    return 0
  fi

  _log "合并 ${branch} -> ${base_branch} (${ahead} 个提交) ..."

  # 检查 master 是否前进了（worktree 创建后有新提交）
  local base_ahead
  base_ahead="$(git rev-list --count "${branch}..${base_branch}" 2>/dev/null || echo 0)"
  if [[ "$base_ahead" -gt 0 ]]; then
    _log "${base_branch} 有 ${base_ahead} 个新提交，先 rebase ..."
    if ! git -C "$wt_path" rebase "${base_branch}" 2>/dev/null; then
      _err "rebase 冲突，自动中止 rebase，保留 worktree 供手动解决"
      git -C "$wt_path" rebase --abort 2>/dev/null || true
      _err "请手动进入 ${wt_path} 解决冲突后重新执行 merge"
      exit 1
    fi
    _log "rebase 成功"
  fi

  # 切回主仓库执行合并
  cd "$REPO_ROOT"
  git checkout "${base_branch}"
  if ! git merge --no-ff "${branch}" -m "merge: ${branch} into ${base_branch}"; then
    _err "merge 冲突，自动中止"
    git merge --abort 2>/dev/null || true
    _err "请手动解决冲突后重新执行 merge"
    exit 1
  fi

  _log "合并完成"

  if [[ "$no_cleanup" == false ]]; then
    cmd_cleanup
  fi
}

# --- 命令: cleanup ---

cmd_cleanup() {
  local state
  state="$(_read_state)"
  local branch wt_path
  branch="$(echo "$state" | grep '"branch"' | sed 's/.*: *"\(.*\)".*/\1/')"
  wt_path="$(echo "$state" | grep '"worktree"' | sed 's/.*: *"\(.*\)".*/\1/')"

  cd "$REPO_ROOT"

  if [[ -d "$wt_path" ]]; then
    _log "移除 worktree: ${wt_path}"
    git worktree remove "$wt_path" --force 2>/dev/null || true
  fi

  if git show-ref --verify --quiet "refs/heads/${branch}" 2>/dev/null; then
    _log "删除分支: ${branch}"
    git branch -D "$branch" 2>/dev/null || true
  fi

  _clear_state
  _log "清理完成"
}

# --- 命令: status ---

cmd_status() {
  if [[ ! -f "$STATE_FILE" ]]; then
    _log "没有活跃的 worktree 会话"
    return 0
  fi
  _log "当前会话:"
  cat "$STATE_FILE"
}

# --- 命令: guard ---

cmd_guard() {
  local current_branch
  current_branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null)"
  if [[ "$current_branch" == "master" || "$current_branch" == "main" ]]; then
    return 1
  fi
  return 0
}

# --- 入口 ---

main() {
  local cmd="${1:-help}"
  shift || true

  case "$cmd" in
    create)  cmd_create "$@" ;;
    merge)   cmd_merge "$@" ;;
    cleanup) cmd_cleanup "$@" ;;
    status)  cmd_status "$@" ;;
    guard)   cmd_guard "$@" ;;
    *)
      echo "用法: wt-flow.sh {create|merge|cleanup|status|guard}"
      echo ""
      echo "  create <slug> [base]  从 base 创建 worktree"
      echo "  merge [--no-cleanup]  合并回基准分支"
      echo "  cleanup               清理 worktree 和分支"
      echo "  status                查看当前会话"
      echo "  guard                 检查是否在主分支上"
      exit 1
      ;;
  esac
}

main "$@"
