#!/usr/bin/env bash
# worktree 隔离开发生命周期管理脚本。
# 用法:
#   wt-flow.sh create <branch-slug> [base-branch]
#   wt-flow.sh merge  [--no-cleanup] [--state-dir=<dir>]
#   wt-flow.sh cleanup
#   wt-flow.sh status
#   wt-flow.sh guard   # 检查是否在 master 上，返回 0=安全 1=在 master
#   wt-flow.sh next    [--state-dir=<dir>]
#   wt-flow.sh verify  <card-id> [--state-dir=<dir>]
#   wt-flow.sh list    [--state-dir=<dir>]
#
# merge 默认 fail-fast：仅非白名单 dirty 会阻断。
# 可通过 WT_FLOW_DIRTY_WHITELIST 配置白名单路径前缀（逗号分隔）。
# 如需兼容旧行为，可显式设置 WT_FLOW_ALLOW_AUTOCOMMIT=1 启用 auto-commit + 重建。

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"
WT_BASE="${REPO_ROOT}/.worktrees"
ACTIVE_TASK_FILE="${REPO_ROOT}/docs/内部参考/任务拆解/_active_task.json"
DEFAULT_STATE_DIR="${REPO_ROOT}/.omc/state"
LEGACY_STATE_FILE="${DEFAULT_STATE_DIR}/wt-flow-state.json"
ALLOWED_PREFIXES=(
  "bash"
  "python"
  "python3"
  "pytest"
  "ruff"
  "grep"
  "cat"
  "jq"
  "wc"
  "test"
  "diff"
  "venv/bin/python"
  "venv/bin/alembic"
  "${REPO_ROOT}/venv/bin/python"
  "${REPO_ROOT}/venv/bin/alembic"
  "npm"
)
DIRTY_POLICY_VERSION="v1_docs_templates"
DEFAULT_DIRTY_WHITELIST=(
  "docs/"
  ".cursor/commands/"
  ".agents/skills/"
  ".claude/commands/"
)

WT_FLOW_PARSE_STATE_DIR=""
WT_FLOW_PARSE_REMAINING=()
WT_FLOW_LAST_SESSION_FILE=""
WT_FLOW_SESSION_ID="${WT_FLOW_SESSION_ID:-}"

# --- 工具函数 ---

_generate_session_id() {
  local timestamp
  timestamp="$(date +%s)"
  local random_suffix
  random_suffix="$(printf "%04x" $((RANDOM % 65536)))"
  echo "${timestamp}-${random_suffix}"
}

_get_or_create_session_id() {
  if [[ -n "$WT_FLOW_SESSION_ID" ]]; then
    echo "$WT_FLOW_SESSION_ID"
    return 0
  fi
  _generate_session_id
}

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

_trim_spaces() {
  local value="$1"
  value="${value#"${value%%[![:space:]]*}"}"
  value="${value%"${value##*[![:space:]]}"}"
  echo "$value"
}

_sanitize_task_key_segment() {
  local value
  value="$(_trim_spaces "${1:-}")"
  if [[ -z "$value" ]]; then
    echo ""
    return 0
  fi
  value="$(printf "%s" "$value" | sed -E 's/[^A-Za-z0-9._-]+/_/g')"
  value="${value#_}"
  value="${value%_}"
  echo "$value"
}

_active_task_key() {
  local active_file="${WT_FLOW_ACTIVE_TASK_FILE:-$ACTIVE_TASK_FILE}"
  if [[ ! -f "$active_file" ]]; then
    echo ""
    return 0
  fi
  jq -r '.task_key // ""' "$active_file" 2>/dev/null || echo ""
}

_task_state_root() {
  local state_dir="$1"
  local task_key_override="${2:-}"
  local task_key="$task_key_override"
  if [[ -z "$task_key" ]]; then
    task_key="$(_active_task_key)"
  fi
  task_key="$(_sanitize_task_key_segment "$task_key")"
  if [[ -n "$task_key" ]]; then
    echo "${state_dir}/${task_key}"
    return 0
  fi
  echo "$state_dir"
}

_task_state_file() {
  local state_dir="$1"
  local task_key_override="${2:-}"
  local root
  root="$(_task_state_root "$state_dir" "$task_key_override")"
  echo "${root}/task-runner-state.json"
}

_task_state_file_for_read() {
  local state_dir="$1"
  local scoped_candidate legacy_candidate
  scoped_candidate="$(_task_state_file "$state_dir")"
  if [[ -f "$scoped_candidate" ]]; then
    echo "$scoped_candidate"
    return 0
  fi
  legacy_candidate="${state_dir}/task-runner-state.json"
  if [[ -f "$legacy_candidate" ]]; then
    echo "$legacy_candidate"
    return 0
  fi
  echo "$scoped_candidate"
}

_session_state_file() {
  local task_key_override="${1:-}"
  local session_id="${2:-}"
  local task_root
  task_root="$(_task_state_root "$DEFAULT_STATE_DIR" "$task_key_override")"
  if [[ -n "$session_id" ]]; then
    echo "${task_root}/sessions/${session_id}/wt-flow-state.json"
  else
    echo "${task_root}/wt-flow-state.json"
  fi
}

_session_state_file_for_read() {
  local session_id="${WT_FLOW_SESSION_ID:-}"
  local scoped_candidate

  if [[ -n "$session_id" ]]; then
    scoped_candidate="$(_session_state_file "" "$session_id")"
    if [[ -f "$scoped_candidate" ]]; then
      echo "$scoped_candidate"
      return 0
    fi
  fi

  scoped_candidate="$(_session_state_file)"
  if [[ -f "$scoped_candidate" ]]; then
    echo "$scoped_candidate"
    return 0
  fi
  if [[ -f "$LEGACY_STATE_FILE" ]]; then
    echo "$LEGACY_STATE_FILE"
    return 0
  fi
  return 1
}

_normalize_dirty_prefix() {
  local prefix="$1"
  prefix="${prefix#"${prefix%%[![:space:]]*}"}"
  prefix="${prefix%"${prefix##*[![:space:]]}"}"
  prefix="${prefix#./}"
  prefix="${prefix#/}"
  prefix="${prefix%/}"
  [[ -n "$prefix" ]] || return 1
  echo "${prefix}/"
}

_dirty_whitelist_csv() {
  local raw="${WT_FLOW_DIRTY_WHITELIST:-}"
  local prefixes=()
  local prefix normalized csv=""

  if [[ -n "$raw" ]]; then
    IFS=',' read -r -a prefixes <<< "$raw"
  else
    prefixes=("${DEFAULT_DIRTY_WHITELIST[@]}")
  fi

  for prefix in "${prefixes[@]}"; do
    normalized="$(_normalize_dirty_prefix "$prefix" || true)"
    [[ -n "$normalized" ]] || continue
    if [[ -n "$csv" ]]; then
      csv="${csv},${normalized}"
    else
      csv="${normalized}"
    fi
  done

  if [[ -z "$csv" ]]; then
    local old_ifs="$IFS"
    IFS=,
    csv="${DEFAULT_DIRTY_WHITELIST[*]}"
    IFS="$old_ifs"
  fi

  echo "$csv"
}

_extract_dirty_path_from_status_line() {
  local line="$1"
  local path="$line"
  if [[ "${#line}" -ge 3 ]]; then
    path="${line:3}"
  fi
  if [[ "$path" == *" -> "* ]]; then
    path="${path##* -> }"
  fi
  path="${path#./}"
  path="${path#/}"
  echo "$path"
}

_is_dirty_path_allowed() {
  local path="$1" whitelist_csv="$2"
  local prefixes=()
  local prefix
  IFS=',' read -r -a prefixes <<< "$whitelist_csv"
  for prefix in "${prefixes[@]}"; do
    [[ -z "$prefix" ]] && continue
    if [[ "$path" == "$prefix"* ]]; then
      return 0
    fi
  done
  return 1
}

_collect_disallowed_dirty_lines() {
  local whitelist_csv="$1"
  local line path
  while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    path="$(_extract_dirty_path_from_status_line "$line")"
    if ! _is_dirty_path_allowed "$path" "$whitelist_csv"; then
      echo "$line"
    fi
  done < <(git status --porcelain --untracked-files=no)
}

_format_dirty_preview() {
  local lines="$1"
  if [[ -z "$lines" ]]; then
    echo ""
    return 0
  fi
  printf "%s\n" "$lines" | sed '/^$/d' | head -n 8 | tr '\n' '; ' | sed 's/; $//'
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

_extract_effective_prefix() {
  local check="$1"
  check="${check#"${check%%[![:space:]]*}"}"

  if [[ "$check" =~ ^cd[[:space:]]+([^&;]+)[[:space:]]*\&\&[[:space:]]*(.+)$ ]]; then
    _extract_effective_prefix "${BASH_REMATCH[2]}"
    return
  fi

  _extract_prefix "$check"
}

_normalize_check_for_worktree() {
  local check="$1" worktree_path="$2"
  local trimmed target rest rel
  trimmed="$(_trim_spaces "$check")"

  if [[ "$trimmed" =~ ^cd[[:space:]]+([^&;]+)[[:space:]]*\&\&[[:space:]]*(.+)$ ]]; then
    target="$(_trim_spaces "${BASH_REMATCH[1]}")"
    rest="$(_trim_spaces "${BASH_REMATCH[2]}")"
    target="${target#\"}"
    target="${target%\"}"
    target="${target#\'}"
    target="${target%\'}"

    if [[ "$target" == "$REPO_ROOT" || "$target" == "$worktree_path" ]]; then
      echo "$rest"
      return
    fi

    if [[ "$target" == "$REPO_ROOT/"* ]]; then
      rel="${target#"$REPO_ROOT/"}"
      echo "cd ${rel} && ${rest}"
      return
    fi

    if [[ "$target" == "$worktree_path/"* ]]; then
      rel="${target#"$worktree_path/"}"
      echo "cd ${rel} && ${rest}"
      return
    fi
  fi

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
  local session_id="${WT_FLOW_SESSION_ID:-}"
  local active_task_key sanitized_task_key by_card by_task_card by_session

  active_task_key="$(_active_task_key)"
  sanitized_task_key="$(_sanitize_task_key_segment "$active_task_key")"

  if [[ -n "$sanitized_task_key" ]]; then
    if [[ -n "$session_id" ]]; then
      by_session="${WT_BASE}/${sanitized_task_key}/${card_id}/${session_id}"
      if [[ -d "$by_session" ]]; then
        echo "$by_session"
        return 0
      fi
    fi

    by_task_card="${WT_BASE}/${sanitized_task_key}/${card_id}"
    if [[ -d "$by_task_card" ]]; then
      echo "$by_task_card"
      return 0
    fi
  fi

  by_card="${WT_BASE}/${card_id}"
  if [[ -d "$by_card" ]]; then
    echo "$by_card"
    return 0
  fi

  local state_file state branch wt_path legacy_wt_path
  if state_file="$(_session_state_file_for_read)"; then
    state="$(cat "$state_file")"
    branch="$(echo "$state" | sed -n 's/.*"branch": *"\([^"]*\)".*/\1/p' | head -n1)"
    wt_path="$(echo "$state" | sed -n 's/.*"worktree": *"\([^"]*\)".*/\1/p' | head -n1)"

    if [[ "$branch" =~ ^feature/(.+)/(.+)/(.+)$ ]]; then
      local branch_task_key branch_card_id branch_session_id
      branch_task_key="$(_sanitize_task_key_segment "${BASH_REMATCH[1]}")"
      branch_card_id="$(_to_upper "${BASH_REMATCH[2]}")"
      branch_session_id="${BASH_REMATCH[3]}"
      if [[ "$branch_card_id" == "$card_id" && -d "$wt_path" ]]; then
        if [[ -z "$sanitized_task_key" || "$branch_task_key" == "$sanitized_task_key" ]]; then
          if [[ -z "$session_id" || "$branch_session_id" == "$session_id" ]]; then
            echo "$wt_path"
            return 0
          fi
        fi
      fi
    elif [[ "$branch" =~ ^feature/(.+)/(.+)$ ]]; then
      local branch_task_key branch_card_id
      branch_task_key="$(_sanitize_task_key_segment "${BASH_REMATCH[1]}")"
      branch_card_id="$(_to_upper "${BASH_REMATCH[2]}")"
      if [[ "$branch_card_id" == "$card_id" && -d "$wt_path" ]]; then
        if [[ -z "$sanitized_task_key" || "$branch_task_key" == "$sanitized_task_key" ]]; then
          echo "$wt_path"
          return 0
        fi
      fi
    fi
    if [[ "$branch" == "feature/${card_id}" && -d "$wt_path" ]]; then
      echo "$wt_path"
      return 0
    fi
  fi

  if [[ -n "$sanitized_task_key" ]]; then
    legacy_wt_path="${WT_BASE}/${card_id}"
    if [[ -d "$legacy_wt_path" ]]; then
      echo "$legacy_wt_path"
      return 0
    fi
  fi

  return 1
}

_ensure_clean() {
  local whitelist_csv disallowed preview
  whitelist_csv="$(_dirty_whitelist_csv)"
  disallowed="$(_collect_disallowed_dirty_lines "$whitelist_csv")"
  if [[ -n "$disallowed" ]]; then
    preview="$(_format_dirty_preview "$disallowed")"
    _die "工作区存在非白名单变更，policy=${DIRTY_POLICY_VERSION} whitelist=${whitelist_csv} preview=${preview}"
  fi
}

_save_state() {
  local branch="$1" worktree="$2" base="$3" session_id="$4"
  local task_key
  task_key="$(_active_task_key)"
  local state_file
  state_file="$(_session_state_file "$task_key" "$session_id")"
  mkdir -p "$(dirname "$state_file")"
  cat > "$state_file" <<EOF
{
  "branch": "$branch",
  "worktree": "$worktree",
  "base_branch": "$base",
  "task_key": "$task_key",
  "session_id": "$session_id",
  "created_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
  WT_FLOW_LAST_SESSION_FILE="$state_file"
}

_read_state() {
  local state_file=""
  if ! state_file="$(_session_state_file_for_read)"; then
    _die "没有活跃的 worktree 会话，请先执行 create"
  fi
  WT_FLOW_LAST_SESSION_FILE="$state_file"
  # 输出 JSON 内容供调用方解析
  cat "$state_file"
}

_clear_state() {
  local state_file="${WT_FLOW_LAST_SESSION_FILE:-}"
  if [[ -z "$state_file" ]]; then
    state_file="$(_session_state_file)"
  fi
  rm -f "$state_file"
}

_mark_card_done_after_merge() {
  local branch="$1" base_branch="$2" state_dir="$3" merge_commit="$4"

  local task_key=""
  local card_id=""
  if [[ "$branch" =~ ^feature/(.+)/(.+)$ ]]; then
    task_key="$(_sanitize_task_key_segment "${BASH_REMATCH[1]}")"
    card_id="$(_to_upper "${BASH_REMATCH[2]}")"
  elif [[ "$branch" =~ ^feature/(.+)$ ]]; then
    card_id="$(_to_upper "${BASH_REMATCH[1]}")"
  else
    return 0
  fi

  [[ -n "$card_id" ]] || return 0

  local state_file task_state_root
  if [[ -n "$task_key" ]]; then
    state_file="$(_task_state_file "$state_dir" "$task_key")"
  else
    state_file="$(_task_state_file_for_read "$state_dir")"
  fi
  [[ -f "$state_file" ]] || return 0
  task_state_root="$(dirname "$state_file")"

  if ! jq -e --arg card "$card_id" 'any(.card_order[]?; ascii_upcase == ($card | ascii_upcase))' "$state_file" >/dev/null 2>&1; then
    return 0
  fi

  local merged_at
  merged_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  _update_json_file "$state_file" \
    --arg card "$card_id" \
    --arg now "$merged_at" \
    '
    .current_card = $card
    | .card_status = ((.card_status // {}) + {($card): "done"})
    | .card_status_map = ((.card_status_map // {}) + {($card): "done"})
    | .last_action = "merge"
    | .last_action_result = "merged_to_base"
    | .no_increment_count = 0
    | .last_updated = $now
    '

  local result_file result_tmp
  result_file="${task_state_root}/attempts/${card_id}/merge_result.json"
  mkdir -p "$(dirname "$result_file")"
  result_tmp="${result_file}.tmp"
  if ! jq -n \
    --arg card_id "$card_id" \
    --arg merged_at "$merged_at" \
    --arg branch "$branch" \
    --arg base_branch "$base_branch" \
    --arg merge_commit "$merge_commit" \
    '{
      card_id: $card_id,
      merged: true,
      merged_at: $merged_at,
      branch: $branch,
      base_branch: $base_branch,
      merge_commit: $merge_commit
    }' > "$result_tmp"; then
    rm -f "$result_tmp"
    _die "写入 merge 结果失败: ${result_file}"
  fi
  mv "$result_tmp" "$result_file"
}

# --- 命令: create ---

cmd_create() {
  local slug="${1:?用法: wt-flow.sh create <branch-slug> [base-branch]}"
  local base="${2:-master}"

  _ensure_clean

  local task_key sanitized_task_key branch wt_path session_id
  task_key="$(_active_task_key)"
  sanitized_task_key="$(_sanitize_task_key_segment "$task_key")"
  session_id="$(_get_or_create_session_id)"

  branch="feature/${slug}"
  wt_path="${WT_BASE}/${slug}"
  if [[ -n "$sanitized_task_key" ]]; then
    branch="feature/${sanitized_task_key}/${slug}/${session_id}"
    wt_path="${WT_BASE}/${sanitized_task_key}/${slug}/${session_id}"
  fi

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

  _save_state "$branch" "$wt_path" "$base" "$session_id"

  _log "worktree 已创建:"
  _log "  分支:    ${branch}"
  _log "  路径:    ${wt_path}"
  _log "  基准:    ${base}"
  _log "  会话:    ${session_id}"
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
  state_file="$(_task_state_file_for_read "$state_dir")"
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
  local state_dir="$(_default_state_dir)"

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --no-cleanup)
        no_cleanup=true
        shift
        ;;
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
        _die "用法: wt-flow.sh merge [--no-cleanup] [--state-dir=<dir>]"
        ;;
    esac
  done

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
    local no_merge_commit
    no_merge_commit="$(git rev-parse "${base_branch}" 2>/dev/null || true)"
    _mark_card_done_after_merge "$branch" "$base_branch" "$state_dir" "$no_merge_commit"
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

  # 主仓库不干净时默认 fail-fast（白名单内变更放行）；仅在显式开关开启时允许 auto-commit。
  local whitelist_csv disallowed preview
  whitelist_csv="$(_dirty_whitelist_csv)"
  disallowed="$(_collect_disallowed_dirty_lines "$whitelist_csv")"
  if [[ -n "$disallowed" ]]; then
    preview="$(_format_dirty_preview "$disallowed")"
    if [[ "${WT_FLOW_ALLOW_AUTOCOMMIT:-0}" == "1" ]]; then
      _log "主仓库有未提交变更，检测到 WT_FLOW_ALLOW_AUTOCOMMIT=1，执行 auto-commit + 重建策略 ..."
      git add -u
      git commit -m "chore: auto-commit before worktree merge (wt-flow)"
      _log "master auto-commit 完成，清理当前 worktree，等待下一轮重建"
      cmd_cleanup
      return 0
    fi
    _die "主仓库存在非白名单变更，policy=${DIRTY_POLICY_VERSION} whitelist=${whitelist_csv} preview=${preview}。请先提交/清理，或设置 WT_FLOW_ALLOW_AUTOCOMMIT=1"
  fi

  git checkout "${base_branch}"
  if ! git merge --no-ff "${branch}" -m "merge: ${branch} into ${base_branch}"; then
    _err "merge 冲突，自动中止"
    git merge --abort 2>/dev/null || true
    _err "请手动解决冲突后重新执行 merge"
    exit 1
  fi

  _log "合并完成"
  local merge_commit
  merge_commit="$(git rev-parse HEAD 2>/dev/null || true)"
  _mark_card_done_after_merge "$branch" "$base_branch" "$state_dir" "$merge_commit"

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
  local state_file=""
  if ! state_file="$(_session_state_file_for_read)"; then
    _log "没有活跃的 worktree 会话"
    return 0
  fi
  _log "当前会话:"
  cat "$state_file"
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

# --- 命令: global-status ---

cmd_global_status() {
  _require_cmd jq

  echo "=== 全局 Worktree 状态 ==="
  printf "%-45s %-8s %-15s %-50s %-40s\n" "TASK_KEY" "CARD" "STATUS" "WORKTREE_PATH" "BRANCH"
  printf "%-45s %-8s %-15s %-50s %-40s\n" "---------------------------------------------" "--------" "---------------" "--------------------------------------------------" "----------------------------------------"

  local all_sessions=()
  if [[ -d "${DEFAULT_STATE_DIR}" ]]; then
    while IFS= read -r session_file; do
      [[ -z "$session_file" ]] && continue
      all_sessions+=("$session_file")
    done < <(find "${DEFAULT_STATE_DIR}" -name "wt-flow-state.json" -type f 2>/dev/null)
  fi

  if [[ "${#all_sessions[@]}" -eq 0 ]]; then
    echo "无活跃的 worktree 会话"
    return 0
  fi

  for session_file in "${all_sessions[@]}"; do
    local task_key branch wt_path session_id card_id status
    task_key="$(jq -r '.task_key // "unknown"' "$session_file" 2>/dev/null || echo "unknown")"
    branch="$(jq -r '.branch // ""' "$session_file" 2>/dev/null || echo "")"
    wt_path="$(jq -r '.worktree // ""' "$session_file" 2>/dev/null || echo "")"
    session_id="$(jq -r '.session_id // ""' "$session_file" 2>/dev/null || echo "")"

    card_id=""
    if [[ "$branch" =~ ^feature/(.+)/(.+)/(.+)$ ]]; then
      card_id="$(_to_upper "${BASH_REMATCH[2]}")"
    elif [[ "$branch" =~ ^feature/(.+)/(.+)$ ]]; then
      card_id="$(_to_upper "${BASH_REMATCH[2]}")"
    elif [[ "$branch" =~ ^feature/(.+)$ ]]; then
      card_id="$(_to_upper "${BASH_REMATCH[1]}")"
    fi

    status="active"
    if [[ ! -d "$wt_path" ]]; then
      status="stale"
    fi

    local display_path="${wt_path#"$REPO_ROOT/"}"
    local display_branch="${branch}"
    if [[ "${#display_branch}" -gt 40 ]]; then
      display_branch="${display_branch:0:37}..."
    fi

    printf "%-45s %-8s %-15s %-50s %-40s\n" \
      "${task_key:0:45}" \
      "${card_id}" \
      "${status}" \
      "${display_path:0:50}" \
      "${display_branch}"
  done

  echo ""
  echo "提示: 使用 'wt-flow.sh status' 查看当前会话详情"
  echo "提示: 使用 'WT_FLOW_SESSION_ID=<session_id> wt-flow.sh ...' 操作特定会话"
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
  state_file="$(_task_state_file_for_read "$state_dir")"
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
  local check normalized_check run_check prefix output rc item

  while IFS= read -r check; do
    [[ -z "$check" ]] && continue
    checks_count=$((checks_count + 1))

    normalized_check="$(_normalize_check_for_worktree "$check" "$worktree_path")"
    run_check="$(printf '%s' "$normalized_check" | sed "s#venv/bin/#${REPO_ROOT}/venv/bin/#g")"
    prefix="$(_extract_effective_prefix "$run_check")"
    if [[ -z "$prefix" ]] || ! _is_allowed_prefix "$prefix"; then
      _err "BLOCKED: 命令前缀不在白名单中: ${run_check}"
      item="$(jq -n \
        --arg check "$check" \
        --arg normalized_check "$normalized_check" \
        --arg run_check "$run_check" \
        --arg prefix "$prefix" \
        '{check: $check, normalized_check: $normalized_check, run_check: $run_check, prefix: $prefix, result: "blocked_not_allowed"}')"
      if [[ -n "$evidence_json" ]]; then
        evidence_json="${evidence_json},${item}"
      else
        evidence_json="$item"
      fi
      all_passed=false
      continue
    fi

    _log "执行检查: ${run_check}"
    set +e
    output="$(cd "$worktree_path" && bash -lc "set -euo pipefail; $run_check" 2>&1)"
    rc=$?
    set -e

    if [[ "$rc" -eq 0 ]]; then
      item="$(jq -n \
        --arg check "$check" \
        --arg normalized_check "$normalized_check" \
        --arg run_check "$run_check" \
        --arg prefix "$prefix" \
        --arg output "$output" \
        '{check: $check, normalized_check: $normalized_check, run_check: $run_check, prefix: $prefix, result: "pass", output: $output}')"
    else
      _err "检查失败(${rc}): ${run_check}"
      _err "$output"
      item="$(jq -n \
        --arg check "$check" \
        --arg normalized_check "$normalized_check" \
        --arg run_check "$run_check" \
        --arg prefix "$prefix" \
        --arg output "$output" \
        --argjson exit_code "$rc" \
        '{check: $check, normalized_check: $normalized_check, run_check: $run_check, prefix: $prefix, result: "fail", exit_code: $exit_code, output: $output}')"
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

  local state_root
  state_root="$(dirname "$state_file")"
  local result_file="${state_root}/attempts/${card_id}/gate_result.json"
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
      | .card_status = ((.card_status // {}) + {($card): "verified"})
      | .card_status_map = ((.card_status_map // {}) + {($card): "verified"})
      | .last_action = "verify"
      | .last_action_result = "done_gate_passed_waiting_merge"
      | .no_increment_count = 0
      | .last_updated = $now
      '
    _log "GATE_PASSED: ${card_id} (status=verified, waiting merge)"
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
  state_file="$(_task_state_file_for_read "$state_dir")"
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
    global-status) cmd_global_status "$@" ;;
    *)
      echo "用法: wt-flow.sh {create|next|verify|list|merge|cleanup|status|guard|global-status}"
      echo ""
      echo "  create <slug> [base]  从 base 创建 worktree（自动生成会话 ID）"
      echo "  next [--state-dir]    选择下一张可执行卡并创建 worktree"
      echo "  verify <card-id>      执行 done_gate 验收（通过后置为 verified）"
      echo "  list [--state-dir]    查看卡片队列与状态"
      echo "  merge [--no-cleanup] [--state-dir]  合并回基准分支并标记 done"
      echo "  cleanup               清理 worktree 和分支"
      echo "  status                查看当前会话"
      echo "  guard                 检查是否在主分支上"
      echo "  global-status         查看所有活跃的 worktree 会话"
      echo ""
      echo "环境变量:"
      echo "  WT_FLOW_SESSION_ID=<id>  指定会话 ID（用于多实例并行）"
      echo "  WT_FLOW_DIRTY_WHITELIST=docs/,.cursor/commands/  配置 dirty 白名单前缀（逗号分隔）"
      echo "  WT_FLOW_ALLOW_AUTOCOMMIT=1  非白名单 dirty 时允许 auto-commit（默认关闭）"
      echo "  WT_FLOW_STATE_DIR         覆盖 task-runner-state 目录（默认 .omc/state）"
      echo "  WT_FLOW_ACTIVE_TASK_FILE  覆盖 active task 文件路径"
      exit 1
      ;;
  esac
}

main "$@"
