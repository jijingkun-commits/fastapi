#!/usr/bin/env bash
# worktree 隔离开发生命周期管理脚本。
# 用法:
#   wt-flow.sh create <branch-slug> [base-branch]
#   wt-flow.sh merge  [--no-cleanup]
#   wt-flow.sh cleanup
#   wt-flow.sh status
#   wt-flow.sh guard   # 检查是否在 master 上，返回 0=安全 1=在 master
#   wt-flow.sh next    [--state-dir=<dir>]
#   wt-flow.sh verify  <card-id> [--state-dir=<dir>]
#   wt-flow.sh list    [--state-dir=<dir>]
#
# merge 默认 fail-fast：主仓 dirty 时直接退出。
# 如需兼容旧行为，可显式设置 WT_FLOW_ALLOW_AUTOCOMMIT=1 启用 auto-commit + 重建。

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"
WT_BASE="${REPO_ROOT}/.worktrees"
STATE_FILE="${REPO_ROOT}/.omc/state/wt-flow-state.json"
ACTIVE_TASK_FILE="${REPO_ROOT}/docs/内部参考/任务拆解/_active_task.json"
DEFAULT_STATE_DIR="${REPO_ROOT}/.omc/state"
ALLOWED_PREFIXES=("bash" "python" "python3" "pytest" "ruff" "grep" "cat" "jq" "wc" "test" "diff")

WT_FLOW_PARSE_STATE_DIR=""
WT_FLOW_PARSE_REMAINING=()

# --- 工具函数 ---

_log()  { echo "[wt-flow] $*"; }
_err()  { echo "[wt-flow] ERROR: $*" >&2; }
_die()  { _err "$@"; exit 1; }

_require_cmd() {
  local cmd_name="$1"
  command -v "$cmd_name" >/dev/null 2>&1 || _die "缺少依赖命令: ${cmd_name}"
}

_to_upper() {
  printf "%s" "$1" | tr '[:lower:]' '[:upper:]'
}

_normalize_status() {
  local status="$1"
  status="$(printf "%s" "$status" | tr '[:upper:]' '[:lower:]')"
  status="${status//-/_}"
  if [[ "$status" == "inprogress" || "$status" == "in_progress" ]]; then
    echo "in_progress"
    return
  fi
  if [[ "$status" == "inreview" || "$status" == "in_review" ]]; then
    echo "in_review"
    return
  fi
  if [[ "$status" == "to_do" || "$status" == "backlog" ]]; then
    echo "todo"
    return
  fi
  echo "$status"
}

_default_state_dir() {
  echo "${WT_FLOW_STATE_DIR:-$DEFAULT_STATE_DIR}"
}

_parse_state_dir_flag() {
  local state_dir="$1"
  shift || true

  WT_FLOW_PARSE_REMAINING=()
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --state-dir=*)
        state_dir="${1#*=}"
        shift
        ;;
      --state-dir)
        shift
        [[ $# -gt 0 ]] || _die "--state-dir 缺少参数"
        state_dir="$1"
        shift
        ;;
      *)
        WT_FLOW_PARSE_REMAINING+=("$1")
        shift
        ;;
    esac
  done

  WT_FLOW_PARSE_STATE_DIR="$state_dir"
}

_task_state_file() {
  local state_dir="$1"
  echo "${state_dir}/task-runner-state.json"
}

_state_status_value() {
  local state_file="$1" card_id="$2"
  jq -r --arg card "$card_id" '((.card_status // {})[$card] // (.card_status_map // {})[$card] // "todo")' "$state_file"
}

_resolve_cards_file() {
  local active_file="${WT_FLOW_ACTIVE_TASK_FILE:-$ACTIVE_TASK_FILE}"
  [[ -f "$active_file" ]] || _die "active task 文件不存在: ${active_file}"

  local task_split_dir task_key cards_file
  task_split_dir="$(jq -r '.task_split_dir // empty' "$active_file")"
  task_key="$(jq -r '.task_key // empty' "$active_file")"

  cards_file=""
  if [[ -n "$task_split_dir" ]]; then
    cards_file="${REPO_ROOT}/docs/内部参考/任务拆解/${task_split_dir}/vk_cards.json"
  fi

  if [[ -z "$cards_file" || ! -f "$cards_file" ]]; then
    if [[ -n "$task_key" ]]; then
      cards_file="${REPO_ROOT}/docs/内部参考/任务拆解/${task_key}/vk_cards.json"
    fi
  fi

  [[ -f "$cards_file" ]] || _die "无法定位 vk_cards.json，请检查 ${active_file} 的 task_split_dir/task_key"
  echo "$cards_file"
}

_card_exists_in_cards_file() {
  local card_id="$1" cards_file="$2"
  jq -e --arg card "$card_id" 'any((.cards // [])[]; ((.card_id // "") | ascii_upcase) == ($card | ascii_upcase))' "$cards_file" >/dev/null 2>&1
}

_card_depends_ready() {
  local card_id="$1" state_file="$2" cards_file="$3"
  local dep dep_status

  while IFS= read -r dep; do
    [[ -z "$dep" ]] && continue
    dep="$(_to_upper "$dep")"
    dep_status="$(_normalize_status "$(_state_status_value "$state_file" "$dep")")"
    if [[ "$dep_status" != "done" ]]; then
      return 1
    fi
  done < <(jq -r --arg card "$card_id" '
      (.cards // [])
      | map(select(((.card_id // "") | ascii_upcase) == ($card | ascii_upcase)))
      | .[0]
      | ((.hard_depends_on // .depends_on // [])[]?)
    ' "$cards_file")

  return 0
}

_card_depends_label() {
  local card_id="$1" cards_file="$2"
  local depends

  depends="$(jq -r --arg card "$card_id" '
      (.cards // [])
      | map(select(((.card_id // "") | ascii_upcase) == ($card | ascii_upcase)))
      | .[0]
      | ((.hard_depends_on // .depends_on // []) | join(","))
    ' "$cards_file")"

  if [[ -z "$depends" || "$depends" == "null" ]]; then
    echo "-"
    return
  fi
  echo "$depends"
}

_update_json_file() {
  local target_file="$1"
  shift
  local tmp_file="${target_file}.tmp"

  if ! jq "$@" "$target_file" > "$tmp_file"; then
    rm -f "$tmp_file"
    _die "更新 ${target_file} 失败"
  fi

  if [[ ! -s "$tmp_file" ]]; then
    rm -f "$tmp_file"
    _die "更新 ${target_file} 失败: jq 输出为空"
  fi

  mv "$tmp_file" "$target_file"
}

_extract_prefix() {
  local check="$1"
  check="${check#"${check%%[![:space:]]*}"}"
  check="${check%%[[:space:]]*}"
  echo "$check"
}

_is_allowed_prefix() {
  local prefix="$1" allowed
  for allowed in "${ALLOWED_PREFIXES[@]}"; do
    if [[ "$prefix" == "$allowed" ]]; then
      return 0
    fi
  done
  return 1
}

_resolve_worktree_path_for_card() {
  local card_id="$1"
  local by_card="${WT_BASE}/${card_id}"
  if [[ -d "$by_card" ]]; then
    echo "$by_card"
    return 0
  fi

  if [[ -f "$STATE_FILE" ]]; then
    local state branch wt_path
    state="$(cat "$STATE_FILE")"
    branch="$(echo "$state" | sed -n 's/.*"branch": *"\([^"]*\)".*/\1/p' | head -n1)"
    wt_path="$(echo "$state" | sed -n 's/.*"worktree": *"\([^"]*\)".*/\1/p' | head -n1)"
    if [[ "$branch" == "feature/${card_id}" && -d "$wt_path" ]]; then
      echo "$wt_path"
      return 0
    fi
  fi

  return 1
}

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

# --- 命令: next ---

cmd_next() {
  _require_cmd jq
  _parse_state_dir_flag "$(_default_state_dir)" "$@"
  if [[ "${#WT_FLOW_PARSE_REMAINING[@]}" -gt 0 ]]; then
    _die "用法: wt-flow.sh next [--state-dir=<dir>]"
  fi

  local state_dir="$WT_FLOW_PARSE_STATE_DIR"
  local state_file
  state_file="$(_task_state_file "$state_dir")"
  [[ -f "$state_file" ]] || _die "状态文件不存在: ${state_file}"

  local cards_file execution_mode card status
  cards_file="$(_resolve_cards_file)"
  execution_mode="$(jq -r '.execution_mode // "serial"' "$state_file")"

  local active_cards=""
  while IFS= read -r card; do
    [[ -z "$card" ]] && continue
    status="$(_normalize_status "$(_state_status_value "$state_file" "$card")")"
    if [[ "$status" == "in_progress" || "$status" == "in_review" ]]; then
      if [[ -n "$active_cards" ]]; then
        active_cards="${active_cards},${card}"
      else
        active_cards="$card"
      fi
    fi
  done < <(jq -r '.card_order[]?' "$state_file")

  if [[ "$execution_mode" == "serial" && -n "$active_cards" ]]; then
    _log "BLOCKED: 串行模式存在进行中卡片: ${active_cards}"
    return 2
  fi

  local next_card="" blocked_cards=""
  while IFS= read -r card; do
    [[ -z "$card" ]] && continue
    card="$(_to_upper "$card")"
    if ! _card_exists_in_cards_file "$card" "$cards_file"; then
      _die "卡片 ${card} 不在 vk_cards.json 中"
    fi

    status="$(_normalize_status "$(_state_status_value "$state_file" "$card")")"
    if [[ "$status" != "todo" ]]; then
      continue
    fi

    if _card_depends_ready "$card" "$state_file" "$cards_file"; then
      next_card="$card"
      break
    fi

    if [[ -n "$blocked_cards" ]]; then
      blocked_cards="${blocked_cards},${card}"
    else
      blocked_cards="$card"
    fi
  done < <(jq -r '.card_order[]?' "$state_file")

  if [[ -z "$next_card" ]]; then
    local unfinished=0
    while IFS= read -r card; do
      [[ -z "$card" ]] && continue
      status="$(_normalize_status "$(_state_status_value "$state_file" "$card")")"
      if [[ "$status" != "done" && "$status" != "skipped" ]]; then
        unfinished=$((unfinished + 1))
      fi
    done < <(jq -r '.card_order[]?' "$state_file")

    if [[ "$unfinished" -eq 0 ]]; then
      echo "ALL_DONE"
      return 0
    fi

    if [[ -n "$blocked_cards" ]]; then
      _log "BLOCKED: 无可推进卡片，依赖未满足: ${blocked_cards}"
    else
      _log "BLOCKED: 无可推进卡片"
    fi
    return 2
  fi

  _log "NEXT: ${next_card}"
  cmd_create "$next_card"

  local now
  now="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  _update_json_file "$state_file" \
    --arg card "$next_card" \
    --arg now "$now" \
    '
    .current_card = $card
    | .card_status = ((.card_status // {}) + {($card): "in_progress"})
    | .card_status_map = ((.card_status_map // {}) + {($card): "inprogress"})
    | .last_action = "next"
    | .last_action_result = "activated_by_wt_flow"
    | .last_updated = $now
    '
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

  # 主仓库不干净时默认 fail-fast；仅在显式开关开启时允许 auto-commit。
  if ! git diff --quiet || ! git diff --cached --quiet; then
    if [[ "${WT_FLOW_ALLOW_AUTOCOMMIT:-0}" == "1" ]]; then
      _log "主仓库有未提交变更，检测到 WT_FLOW_ALLOW_AUTOCOMMIT=1，执行 auto-commit + 重建策略 ..."
      git add -u
      git commit -m "chore: auto-commit before worktree merge (wt-flow)"
      _log "master auto-commit 完成，清理当前 worktree，等待下一轮重建"
      cmd_cleanup
      return 0
    fi
    _die "主仓库有未提交变更，默认策略为 fail-fast。请先手动提交/清理，或显式设置 WT_FLOW_ALLOW_AUTOCOMMIT=1"
  fi

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

# --- 命令: verify ---

cmd_verify() {
  _require_cmd jq
  _parse_state_dir_flag "$(_default_state_dir)" "$@"
  if [[ "${#WT_FLOW_PARSE_REMAINING[@]}" -ne 1 ]]; then
    _die "用法: wt-flow.sh verify <card-id> [--state-dir=<dir>]"
  fi

  local card_id
  card_id="$(_to_upper "${WT_FLOW_PARSE_REMAINING[0]}")"

  local state_dir="$WT_FLOW_PARSE_STATE_DIR"
  local state_file
  state_file="$(_task_state_file "$state_dir")"
  [[ -f "$state_file" ]] || _die "状态文件不存在: ${state_file}"

  local cards_file
  cards_file="$(_resolve_cards_file)"
  if ! _card_exists_in_cards_file "$card_id" "$cards_file"; then
    _die "卡片 ${card_id} 不在 vk_cards.json 中"
  fi

  local worktree_path
  if ! worktree_path="$(_resolve_worktree_path_for_card "$card_id")"; then
    _die "未找到卡片 ${card_id} 的 worktree，预期路径: ${WT_BASE}/${card_id}"
  fi

  local all_passed=true
  local checks_count=0
  local evidence_json=""
  local check prefix output rc item

  while IFS= read -r check; do
    [[ -z "$check" ]] && continue
    checks_count=$((checks_count + 1))

    prefix="$(_extract_prefix "$check")"
    if [[ -z "$prefix" ]] || ! _is_allowed_prefix "$prefix"; then
      _err "BLOCKED: 命令前缀不在白名单中: ${check}"
      item="$(jq -n \
        --arg check "$check" \
        --arg prefix "$prefix" \
        '{check: $check, prefix: $prefix, result: "blocked_not_allowed"}')"
      if [[ -n "$evidence_json" ]]; then
        evidence_json="${evidence_json},${item}"
      else
        evidence_json="$item"
      fi
      all_passed=false
      continue
    fi

    _log "执行检查: ${check}"
    set +e
    output="$(cd "$worktree_path" && bash -lc "set -euo pipefail; $check" 2>&1)"
    rc=$?
    set -e

    if [[ "$rc" -eq 0 ]]; then
      item="$(jq -n \
        --arg check "$check" \
        --arg prefix "$prefix" \
        --arg output "$output" \
        '{check: $check, prefix: $prefix, result: "pass", output: $output}')"
    else
      _err "检查失败(${rc}): ${check}"
      _err "$output"
      item="$(jq -n \
        --arg check "$check" \
        --arg prefix "$prefix" \
        --arg output "$output" \
        --argjson exit_code "$rc" \
        '{check: $check, prefix: $prefix, result: "fail", exit_code: $exit_code, output: $output}')"
      all_passed=false
    fi

    if [[ -n "$evidence_json" ]]; then
      evidence_json="${evidence_json},${item}"
    else
      evidence_json="$item"
    fi
  done < <(jq -r --arg card "$card_id" '
      (.cards // [])
      | map(select(((.card_id // "") | ascii_upcase) == ($card | ascii_upcase)))
      | .[0]
      | (.acceptance_checks // [])[]
    ' "$cards_file")

  if [[ "$checks_count" -eq 0 ]]; then
    _log "WARN: ${card_id} 无 acceptance_checks，默认通过"
    evidence_json='{"result":"no_checks_defined"}'
  fi

  local passed_json="true"
  if [[ "$all_passed" != true ]]; then
    passed_json="false"
  fi

  local result_file="${state_dir}/attempts/${card_id}/gate_result.json"
  mkdir -p "$(dirname "$result_file")"

  local checked_at evidence_payload result_tmp
  checked_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  result_tmp="${result_file}.tmp"
  if [[ -n "$evidence_json" ]]; then
    evidence_payload="[${evidence_json}]"
  else
    evidence_payload="[]"
  fi

  if ! jq -n \
    --arg card_id "$card_id" \
    --arg checked_at "$checked_at" \
    --arg worktree_path "$worktree_path" \
    --argjson passed "$passed_json" \
    --argjson evidence "$evidence_payload" \
    '{
      card_id: $card_id,
      passed: $passed,
      checked_at: $checked_at,
      worktree_path: $worktree_path,
      evidence: $evidence
    }' > "$result_tmp"; then
    rm -f "$result_tmp"
    _die "写入 done_gate 结果失败: ${result_file}"
  fi

  if [[ ! -s "$result_tmp" ]]; then
    rm -f "$result_tmp"
    _die "写入 done_gate 结果失败: jq 输出为空"
  fi
  mv "$result_tmp" "$result_file"

  if [[ "$all_passed" == true ]]; then
    _update_json_file "$state_file" \
      --arg card "$card_id" \
      --arg now "$checked_at" \
      '
      .current_card = $card
      | .card_status = ((.card_status // {}) + {($card): "done"})
      | .card_status_map = ((.card_status_map // {}) + {($card): "done"})
      | .last_action = "verify"
      | .last_action_result = "done_gate_passed"
      | .no_increment_count = 0
      | .last_updated = $now
      '
    _log "GATE_PASSED: ${card_id}"
    return 0
  fi

  _update_json_file "$state_file" \
    --arg card "$card_id" \
    --arg now "$checked_at" \
    '
    .current_card = $card
    | .card_status = ((.card_status // {}) + {($card): "in_progress"})
    | .card_status_map = ((.card_status_map // {}) + {($card): "inprogress"})
    | .last_action = "verify"
    | .last_action_result = "done_gate_failed"
    | .no_increment_count = ((.no_increment_count // 0) + 1)
    | .last_updated = $now
    '
  _log "GATE_FAILED: ${card_id}"
  return 1
}

# --- 命令: list ---

cmd_list() {
  _require_cmd jq
  _parse_state_dir_flag "$(_default_state_dir)" "$@"
  if [[ "${#WT_FLOW_PARSE_REMAINING[@]}" -gt 0 ]]; then
    _die "用法: wt-flow.sh list [--state-dir=<dir>]"
  fi

  local state_dir="$WT_FLOW_PARSE_STATE_DIR"
  local state_file
  state_file="$(_task_state_file "$state_dir")"
  [[ -f "$state_file" ]] || _die "状态文件不存在: ${state_file}"

  local cards_file
  cards_file="$(_resolve_cards_file)"

  local task_key execution_mode current_card
  task_key="$(jq -r '.task_key // "unknown"' "$state_file")"
  execution_mode="$(jq -r '.execution_mode // "serial"' "$state_file")"
  current_card="$(jq -r '.current_card // ""' "$state_file")"

  echo "=== 任务队列 ==="
  echo "task_key: ${task_key}"
  echo "mode: ${execution_mode}"
  echo "current: ${current_card:-N/A}"
  echo ""
  printf "%-8s %-12s %-18s %s\n" "CARD" "STATUS" "DEPENDS" "MARK"
  printf "%-8s %-12s %-18s %s\n" "--------" "------------" "------------------" "----"

  local card status depends marker
  while IFS= read -r card; do
    [[ -z "$card" ]] && continue
    card="$(_to_upper "$card")"
    status="$(_normalize_status "$(_state_status_value "$state_file" "$card")")"
    depends="$(_card_depends_label "$card" "$cards_file")"
    marker=""
    if [[ "$card" == "$current_card" ]]; then
      marker="<--"
    fi
    printf "%-8s %-12s %-18s %s\n" "$card" "$status" "$depends" "$marker"
  done < <(jq -r '.card_order[]?' "$state_file")
}

# --- 入口 ---

main() {
  local cmd="${1:-help}"
  shift || true

  case "$cmd" in
    create)  cmd_create "$@" ;;
    next)    cmd_next "$@" ;;
    verify)  cmd_verify "$@" ;;
    list)    cmd_list "$@" ;;
    merge)   cmd_merge "$@" ;;
    cleanup) cmd_cleanup "$@" ;;
    status)  cmd_status "$@" ;;
    guard)   cmd_guard "$@" ;;
    *)
      echo "用法: wt-flow.sh {create|next|verify|list|merge|cleanup|status|guard}"
      echo ""
      echo "  create <slug> [base]  从 base 创建 worktree"
      echo "  next [--state-dir]    选择下一张可执行卡并创建 worktree"
      echo "  verify <card-id>      执行 done_gate 验收（白名单命令前缀）"
      echo "  list [--state-dir]    查看卡片队列与状态"
      echo "  merge [--no-cleanup]  合并回基准分支"
      echo "  cleanup               清理 worktree 和分支"
      echo "  status                查看当前会话"
      echo "  guard                 检查是否在主分支上"
      echo ""
      echo "环境变量:"
      echo "  WT_FLOW_ALLOW_AUTOCOMMIT=1  主仓 dirty 时允许 auto-commit（默认关闭）"
      echo "  WT_FLOW_STATE_DIR         覆盖 task-runner-state 目录（默认 .omc/state）"
      echo "  WT_FLOW_ACTIVE_TASK_FILE  覆盖 active task 文件路径"
      exit 1
      ;;
  esac
}

main "$@"
