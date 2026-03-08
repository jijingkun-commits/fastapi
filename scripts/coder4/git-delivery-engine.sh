#!/usr/bin/env bash
set -euo pipefail

_log() { echo "[git-delivery] $*" >&2; }
_err() { echo "[git-delivery] ERROR: $*" >&2; }
_die() { _err "$@"; exit 1; }

_require_cmd() {
  command -v "$1" >/dev/null 2>&1 || _die "缺少依赖命令: $1"
}

_to_bool_token() {
  if [[ "${1:-}" == "true" ]]; then
    printf '__BOOL_TRUE__'
  else
    printf '__BOOL_FALSE__'
  fi
}

_emit_json() {
  python3 - "$@" <<'PY'
import json, sys
payload = {}
for arg in sys.argv[1:]:
    key, value = arg.split("=", 1)
    if value == "__BOOL_TRUE__":
        payload[key] = True
    elif value == "__BOOL_FALSE__":
        payload[key] = False
    elif value == "__NULL__":
        payload[key] = None
    else:
        payload[key] = value
print(json.dumps(payload, ensure_ascii=False))
PY
}

_abs_path() {
  cd "$1" && pwd -P
}

_git_top() {
  git -C "$1" rev-parse --show-toplevel 2>/dev/null
}

_common_git_dir() {
  local source_worktree="$1"
  local top common
  top="$(_git_top "$source_worktree")"
  common="$(git -C "$source_worktree" rev-parse --git-common-dir 2>/dev/null || true)"
  [[ -n "$common" ]] || _die "无法解析 git common dir: ${source_worktree}"
  if [[ "$common" != /* ]]; then
    common="$(cd "$top" && cd "$common" && pwd -P)"
  fi
  printf '%s\n' "$common"
}

_common_root() {
  local common_git_dir="$1"
  cd "${common_git_dir}/.." && pwd -P
}

_sanitize_key() {
  printf '%s' "$1" | tr '/ :' '___' | tr -cd 'A-Za-z0-9._-'
}

_meta_file() {
  local source_worktree="$1" source_branch="$2"
  local common_git_dir key
  common_git_dir="$(_common_git_dir "$source_worktree")"
  key="$(_sanitize_key "$source_branch")"
  mkdir -p "${common_git_dir}/codex/jjk-commit"
  printf '%s\n' "${common_git_dir}/codex/jjk-commit/${key}.json"
}

_write_meta() {
  local file="$1"
  shift
  python3 - "$file" "$@" <<'PY'
import json
import pathlib
import sys
path = pathlib.Path(sys.argv[1])
payload = {}
for arg in sys.argv[2:]:
    key, value = arg.split("=", 1)
    if value == "__BOOL_TRUE__":
        payload[key] = True
    elif value == "__BOOL_FALSE__":
        payload[key] = False
    elif value == "__NULL__":
        payload[key] = None
    else:
        payload[key] = value
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY
}

_read_meta_field() {
  local file="$1" field="$2"
  python3 - "$file" "$field" <<'PY'
import json
import pathlib
import sys
path = pathlib.Path(sys.argv[1])
field = sys.argv[2]
if not path.exists():
    raise SystemExit(1)
payload = json.loads(path.read_text(encoding='utf-8'))
value = payload.get(field, "")
if isinstance(value, bool):
    print("true" if value else "false")
elif value is None:
    print("")
else:
    print(value)
PY
}

_emit_meta_payload() {
  local file="$1"
  python3 - "$file" <<'PY'
import json
import pathlib
import sys
path = pathlib.Path(sys.argv[1])
if not path.exists():
    print(json.dumps({"status": "idle"}, ensure_ascii=False))
    raise SystemExit(0)
payload = json.loads(path.read_text(encoding='utf-8'))
print(json.dumps(payload, ensure_ascii=False))
PY
}

_clear_meta() {
  local file="$1"
  rm -f "$file"
}

_cleanup_base_checkout_if_needed() {
  local source_worktree="$1" base_checkout="$2" created_by_engine="$3"
  [[ "$created_by_engine" == "true" ]] || return 0
  [[ -n "$base_checkout" ]] || return 0
  [[ -d "$base_checkout" ]] || return 0
  git -C "$source_worktree" worktree remove "$base_checkout" --force >/dev/null 2>&1 || true
}

_find_existing_base_checkout() {
  local source_worktree="$1" base_branch="$2"
  local common_git_dir common_root current_branch current_path worktree_path branch_ref
  common_git_dir="$(_common_git_dir "$source_worktree")"
  common_root="$(_common_root "$common_git_dir")"

  if git -C "$common_root" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    current_branch="$(git -C "$common_root" branch --show-current 2>/dev/null || true)"
    if [[ "$current_branch" == "$base_branch" ]]; then
      printf '%s\n' "$common_root"
      return 0
    fi
  fi

  current_path=""
  branch_ref=""
  while IFS= read -r line; do
    case "$line" in
      worktree\ *) current_path="${line#worktree }" ;;
      branch\ refs/heads/*)
        branch_ref="${line#branch refs/heads/}"
        if [[ "$branch_ref" == "$base_branch" && -n "$current_path" ]]; then
          printf '%s\n' "$current_path"
          return 0
        fi
        ;;
      '')
        current_path=""
        branch_ref=""
        ;;
    esac
  done < <(git -C "$source_worktree" worktree list --porcelain)

  return 1
}

_prepare_base_checkout() {
  local source_worktree="$1" base_branch="$2"
  local base_checkout created_by_engine common_root repo_name tmp_dir
  if base_checkout="$(_find_existing_base_checkout "$source_worktree" "$base_branch")"; then
    printf '%s\tfalse\n' "$base_checkout"
    return 0
  fi

  common_root="$(_common_root "$(_common_git_dir "$source_worktree")")"
  repo_name="$(basename "$common_root")"
  tmp_dir="$(mktemp -d "${TMPDIR:-/tmp}/git-delivery-${repo_name}-${base_branch}-XXXXXX")"
  git -C "$source_worktree" worktree add "$tmp_dir" "$base_branch" >/dev/null 2>&1 || {
    rm -rf "$tmp_dir"
    _die "DELIVERY_BASE_UNAVAILABLE: 无法创建 ${base_branch} checkout"
  }
  printf '%s\ttrue\n' "$tmp_dir"
}

_source_ahead_count() {
  local source_worktree="$1" source_branch="$2" base_branch="$3"
  git -C "$source_worktree" rev-list --count "${base_branch}..${source_branch}" 2>/dev/null || echo 0
}

_base_ahead_count() {
  local source_worktree="$1" source_branch="$2" base_branch="$3"
  git -C "$source_worktree" rev-list --count "${source_branch}..${base_branch}" 2>/dev/null || echo 0
}

_require_clean_source_worktree() {
  local source_worktree="$1"
  if ! git -C "$source_worktree" diff --quiet || ! git -C "$source_worktree" diff --cached --quiet; then
    _die "COMMIT_WORKTREE_DIRTY: worktree ${source_worktree} 有未提交变更"
  fi
}

_write_conflict_meta() {
  local meta_file="$1" stage="$2" source_branch="$3" source_worktree="$4" base_branch="$5" base_checkout="$6" created_by_engine="$7"
  _write_meta "$meta_file" \
    "status=${stage}" \
    "source_branch=${source_branch}" \
    "source_worktree=${source_worktree}" \
    "base_branch=${base_branch}" \
    "base_checkout=${base_checkout}" \
    "created_by_engine=$(_to_bool_token "$created_by_engine")"
}

_emit_merged_payload() {
  local source_branch="$1" source_worktree="$2" base_branch="$3" base_checkout="$4" created_by_engine="$5" rebase_performed="$6"
  local merge_commit
  merge_commit="$(git -C "$base_checkout" rev-parse HEAD 2>/dev/null || true)"
  _emit_json \
    "status=merged" \
    "source_branch=${source_branch}" \
    "source_worktree=${source_worktree}" \
    "base_branch=${base_branch}" \
    "base_checkout=${base_checkout}" \
    "created_by_engine=$(_to_bool_token "$created_by_engine")" \
    "rebase_performed=$(_to_bool_token "$rebase_performed")" \
    "merge_commit=${merge_commit}"
}

_perform_merge() {
  local source_branch="$1" source_worktree="$2" base_branch="$3" base_checkout="$4" created_by_engine="$5" rebase_performed="$6" meta_file="$7"
  git -C "$base_checkout" checkout "$base_branch" >/dev/null 2>&1
  if ! git -C "$base_checkout" merge --no-ff "$source_branch" -m "merge: ${source_branch} into ${base_branch}" >/dev/null 2>&1; then
    _write_conflict_meta "$meta_file" "merge_conflict" "$source_branch" "$source_worktree" "$base_branch" "$base_checkout" "$created_by_engine"
    _emit_json \
      "status=merge_conflict" \
      "source_branch=${source_branch}" \
      "source_worktree=${source_worktree}" \
      "base_branch=${base_branch}" \
      "base_checkout=${base_checkout}" \
      "created_by_engine=$(_to_bool_token "$created_by_engine")"
    return 1
  fi
  _clear_meta "$meta_file"
  _emit_merged_payload "$source_branch" "$source_worktree" "$base_branch" "$base_checkout" "$created_by_engine" "$rebase_performed"
  return 0
}

_parse_args() {
  SOURCE_BRANCH=""
  SOURCE_WORKTREE=""
  BASE_BRANCH="master"
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --source-branch)
        SOURCE_BRANCH="$2"
        shift 2
        ;;
      --source-worktree)
        SOURCE_WORKTREE="$(_abs_path "$2")"
        shift 2
        ;;
      --base-branch)
        BASE_BRANCH="$2"
        shift 2
        ;;
      *)
        _die "未知参数: $1"
        ;;
    esac
  done
  [[ -n "$SOURCE_BRANCH" ]] || _die "缺少 --source-branch"
  [[ -n "$SOURCE_WORKTREE" ]] || _die "缺少 --source-worktree"
}

cmd_prepare_base() {
  _parse_args "$@"
  local prepared base_checkout created_by_engine
  prepared="$(_prepare_base_checkout "$SOURCE_WORKTREE" "$BASE_BRANCH")"
  base_checkout="${prepared%%$'\t'*}"
  created_by_engine="${prepared##*$'\t'}"
  _emit_json \
    "status=base_ready" \
    "source_branch=${SOURCE_BRANCH}" \
    "source_worktree=${SOURCE_WORKTREE}" \
    "base_branch=${BASE_BRANCH}" \
    "base_checkout=${base_checkout}" \
    "created_by_engine=$(_to_bool_token "$created_by_engine")"
}

cmd_merge() {
  _parse_args "$@"
  _require_clean_source_worktree "$SOURCE_WORKTREE"

  local ahead meta_file prepared base_checkout created_by_engine base_ahead rebase_performed
  ahead="$(_source_ahead_count "$SOURCE_WORKTREE" "$SOURCE_BRANCH" "$BASE_BRANCH")"
  [[ "$ahead" -gt 0 ]] || _die "MERGE_NO_COMMITS: 分支 ${SOURCE_BRANCH} 相对 ${BASE_BRANCH} 无新提交"

  meta_file="$(_meta_file "$SOURCE_WORKTREE" "$SOURCE_BRANCH")"
  prepared="$(_prepare_base_checkout "$SOURCE_WORKTREE" "$BASE_BRANCH")"
  base_checkout="${prepared%%$'\t'*}"
  created_by_engine="${prepared##*$'\t'}"
  base_checkout="$(_abs_path "$base_checkout")"
  rebase_performed=false

  base_ahead="$(_base_ahead_count "$SOURCE_WORKTREE" "$SOURCE_BRANCH" "$BASE_BRANCH")"
  if [[ "$base_ahead" -gt 0 ]]; then
    rebase_performed=true
    if ! git -C "$SOURCE_WORKTREE" rebase "$BASE_BRANCH" >/dev/null 2>&1; then
      _write_conflict_meta "$meta_file" "rebase_conflict" "$SOURCE_BRANCH" "$SOURCE_WORKTREE" "$BASE_BRANCH" "$base_checkout" "$created_by_engine"
      _emit_json \
        "status=rebase_conflict" \
        "source_branch=${SOURCE_BRANCH}" \
        "source_worktree=${SOURCE_WORKTREE}" \
        "base_branch=${BASE_BRANCH}" \
        "base_checkout=${base_checkout}" \
        "created_by_engine=$(_to_bool_token "$created_by_engine")"
      return 1
    fi
  fi

  _perform_merge "$SOURCE_BRANCH" "$SOURCE_WORKTREE" "$BASE_BRANCH" "$base_checkout" "$created_by_engine" "$rebase_performed" "$meta_file"
}

cmd_status() {
  _parse_args "$@"
  local meta_file
  meta_file="$(_meta_file "$SOURCE_WORKTREE" "$SOURCE_BRANCH")"
  _emit_meta_payload "$meta_file"
}

cmd_abort() {
  _parse_args "$@"
  local meta_file status base_checkout created_by_engine
  meta_file="$(_meta_file "$SOURCE_WORKTREE" "$SOURCE_BRANCH")"
  [[ -f "$meta_file" ]] || _die "DELIVERY_NOT_IN_PROGRESS: 当前没有进行中的 delivery"
  status="$(_read_meta_field "$meta_file" status)"
  base_checkout="$(_read_meta_field "$meta_file" base_checkout)"
  created_by_engine="$(_read_meta_field "$meta_file" created_by_engine)"

  case "$status" in
    rebase_conflict)
      git -C "$SOURCE_WORKTREE" rebase --abort >/dev/null 2>&1 || true
      ;;
    merge_conflict)
      git -C "$base_checkout" merge --abort >/dev/null 2>&1 || true
      ;;
    *)
      _die "DELIVERY_NOT_IN_PROGRESS: 当前没有可中止的 delivery"
      ;;
  esac

  _clear_meta "$meta_file"
  _cleanup_base_checkout_if_needed "$SOURCE_WORKTREE" "$base_checkout" "$created_by_engine"
  _emit_json \
    "status=aborted" \
    "source_branch=${SOURCE_BRANCH}" \
    "source_worktree=${SOURCE_WORKTREE}" \
    "base_checkout=${base_checkout}"
}

cmd_continue() {
  _parse_args "$@"
  local meta_file status base_branch base_checkout created_by_engine
  meta_file="$(_meta_file "$SOURCE_WORKTREE" "$SOURCE_BRANCH")"
  [[ -f "$meta_file" ]] || _die "DELIVERY_NOT_IN_PROGRESS: 当前没有进行中的 delivery"
  status="$(_read_meta_field "$meta_file" status)"
  base_branch="$(_read_meta_field "$meta_file" base_branch)"
  base_checkout="$(_read_meta_field "$meta_file" base_checkout)"
  created_by_engine="$(_read_meta_field "$meta_file" created_by_engine)"

  case "$status" in
    rebase_conflict)
      if ! GIT_EDITOR=true git -C "$SOURCE_WORKTREE" rebase --continue >/dev/null 2>&1; then
        _emit_json \
          "status=rebase_conflict" \
          "source_branch=${SOURCE_BRANCH}" \
          "source_worktree=${SOURCE_WORKTREE}" \
          "base_branch=${base_branch}" \
          "base_checkout=${base_checkout}" \
          "created_by_engine=$(_to_bool_token "$created_by_engine")"
        return 1
      fi
      _perform_merge "$SOURCE_BRANCH" "$SOURCE_WORKTREE" "$base_branch" "$base_checkout" "$created_by_engine" true "$meta_file"
      ;;
    merge_conflict)
      if ! GIT_EDITOR=true git -C "$base_checkout" merge --continue >/dev/null 2>&1; then
        _emit_json \
          "status=merge_conflict" \
          "source_branch=${SOURCE_BRANCH}" \
          "source_worktree=${SOURCE_WORKTREE}" \
          "base_branch=${base_branch}" \
          "base_checkout=${base_checkout}" \
          "created_by_engine=$(_to_bool_token "$created_by_engine")"
        return 1
      fi
      _clear_meta "$meta_file"
      _emit_merged_payload "$SOURCE_BRANCH" "$SOURCE_WORKTREE" "$base_branch" "$base_checkout" "$created_by_engine" true
      ;;
    *)
      _die "DELIVERY_NOT_IN_PROGRESS: 当前没有可继续的 delivery"
      ;;
  esac
}

main() {
  _require_cmd git
  local cmd="${1:-}"
  shift || true
  case "$cmd" in
    prepare-base) cmd_prepare_base "$@" ;;
    merge) cmd_merge "$@" ;;
    status) cmd_status "$@" ;;
    continue) cmd_continue "$@" ;;
    abort) cmd_abort "$@" ;;
    *)
      _die "用法: git-delivery-engine.sh {prepare-base|merge|status|continue|abort} --source-branch <branch> --source-worktree <path> [--base-branch master]"
      ;;
  esac
}

main "$@"
