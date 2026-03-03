#!/usr/bin/env python3
"""IG01 集成门禁校验：实现卡必须已合并且主干可见。"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TASK_SPLIT_BASE = Path("docs/内部参考/任务拆解")
DEFAULT_STATE_DIR = Path(".omc/state")


class IntegrationGateError(RuntimeError):
    """IG01 校验输入错误。"""


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise IntegrationGateError(f"JSON 根节点不是对象: {path}")
    return payload


def _normalize_id(raw: Any) -> str:
    return str(raw or "").strip().strip("`'\"").upper()


def _normalize_status(raw: Any) -> str:
    value = str(raw or "").strip().lower().replace("-", "_")
    if value in {"inprogress", "in_progress"}:
        return "in_progress"
    if value in {"inreview", "in_review"}:
        return "in_review"
    if value in {"todo", "to_do", "backlog"}:
        return "todo"
    return value


def _resolve_task_split_dir(repo_root: Path, raw_value: str) -> Path:
    raw = str(raw_value or "").strip()
    if not raw:
        raise IntegrationGateError("缺少 --task-split-dir")

    direct = Path(raw).expanduser()
    candidates = []
    if direct.is_absolute():
        candidates.append(direct)
    else:
        candidates.extend(
            [
                (repo_root / raw),
                (repo_root / TASK_SPLIT_BASE / raw),
            ]
        )
    for candidate in candidates:
        if candidate.exists() and candidate.is_dir():
            return candidate.resolve()
    joined = " | ".join(str(path) for path in candidates)
    raise IntegrationGateError(f"无法定位 task_split_dir: {raw}; candidates={joined}")


def _run_git(repo_root: Path, *args: str) -> tuple[int, str, str]:
    proc = subprocess.run(
        ["git", "-C", str(repo_root), *args],
        check=False,
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def _resolve_baseline_ref(repo_root: Path, baseline: str) -> str:
    candidate = str(baseline or "").strip()
    if not candidate:
        raise IntegrationGateError("baseline 不能为空")

    for ref in (candidate, f"refs/heads/{candidate}", f"origin/{candidate}"):
        code, stdout, _stderr = _run_git(repo_root, "rev-parse", "--verify", ref)
        if code == 0 and stdout:
            return stdout.splitlines()[0]
    raise IntegrationGateError(f"无法解析 baseline: {candidate}")


def _commit_exists(repo_root: Path, commit_sha: str) -> bool:
    code, _stdout, _stderr = _run_git(repo_root, "cat-file", "-e", f"{commit_sha}^{{commit}}")
    return code == 0


def _is_ancestor(repo_root: Path, ancestor_sha: str, target_sha: str) -> bool:
    code, _stdout, _stderr = _run_git(repo_root, "merge-base", "--is-ancestor", ancestor_sha, target_sha)
    return code == 0


def _collect_merge_required_cards(vk_cards: dict[str, Any]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for card in vk_cards.get("cards") or []:
        if not isinstance(card, dict):
            continue
        merge_required = bool(card.get("merge_required"))
        task_mode = str(card.get("task_mode") or "").strip().lower()
        if not merge_required:
            continue
        if task_mode and task_mode != "implementation-card":
            continue
        card_id = _normalize_id(card.get("card_id"))
        if not card_id or card_id in seen:
            continue
        result.append(card_id)
        seen.add(card_id)
    return result


def _load_card_status_map(state_file: Path) -> dict[str, str]:
    if not state_file.exists():
        return {}
    payload = load_json(state_file)
    card_status = payload.get("card_status_map") or payload.get("card_status") or {}
    if not isinstance(card_status, dict):
        return {}
    result: dict[str, str] = {}
    for card_id, status in card_status.items():
        normalized_card = _normalize_id(card_id)
        if not normalized_card:
            continue
        result[normalized_card] = _normalize_status(status)
    return result


def _sanitize_task_key_segment(task_key: str) -> str:
    normalized = "".join(ch if ch.isalnum() or ch in {".", "_", "-"} else "_" for ch in str(task_key or "").strip())
    return normalized.strip("._")


def _resolve_task_state_dir(state_dir: Path, task_key: str) -> Path:
    sanitized_task_key = _sanitize_task_key_segment(task_key)
    if not sanitized_task_key:
        return state_dir

    scoped_dir = state_dir / sanitized_task_key
    scoped_state_file = scoped_dir / "task-runner-state.json"
    legacy_state_file = state_dir / "task-runner-state.json"

    if scoped_state_file.exists() or (scoped_dir / "attempts").exists():
        return scoped_dir
    if legacy_state_file.exists() or (state_dir / "attempts").exists():
        return state_dir
    return scoped_dir


def run_check(
    *,
    repo_root: Path,
    task_split_dir: Path,
    state_dir: Path,
    baseline: str,
) -> dict[str, Any]:
    vk_cards_path = task_split_dir / "vk_cards.json"
    if not vk_cards_path.exists():
        raise IntegrationGateError(f"缺少文件: {vk_cards_path}")
    vk_cards = load_json(vk_cards_path)
    baseline_sha = _resolve_baseline_ref(repo_root, baseline)

    merge_required_cards = _collect_merge_required_cards(vk_cards)
    if not merge_required_cards:
        raise IntegrationGateError(f"{vk_cards_path} 未找到 merge_required 的 implementation-card")

    task_key = str(vk_cards.get("task_key") or "").strip()
    resolved_state_dir = _resolve_task_state_dir(state_dir, task_key)
    state_file = resolved_state_dir / "task-runner-state.json"
    status_map = _load_card_status_map(state_file)

    missing_merge_result: list[str] = []
    merge_result_invalid: list[str] = []
    missing_commit_sha: list[str] = []
    unknown_commit_sha: list[str] = []
    not_merged_to_baseline: list[str] = []
    status_not_done: list[str] = []
    checked_cards: list[dict[str, Any]] = []

    for card_id in merge_required_cards:
        merge_result_path = resolved_state_dir / "attempts" / card_id / "merge_result.json"
        card_result: dict[str, Any] = {
            "card_id": card_id,
            "merge_result_file": str(merge_result_path),
            "merged": False,
            "merge_commit": "",
            "baseline_visible": False,
        }
        if not merge_result_path.exists():
            missing_merge_result.append(card_id)
            checked_cards.append(card_result)
            continue

        try:
            merge_payload = load_json(merge_result_path)
        except Exception:
            merge_result_invalid.append(card_id)
            checked_cards.append(card_result)
            continue

        merged = bool(merge_payload.get("merged"))
        merge_commit = str(merge_payload.get("merge_commit") or "").strip()
        card_result["merged"] = merged
        card_result["merge_commit"] = merge_commit
        if not merged:
            merge_result_invalid.append(card_id)
            checked_cards.append(card_result)
            continue
        if not merge_commit:
            missing_commit_sha.append(card_id)
            checked_cards.append(card_result)
            continue
        if not _commit_exists(repo_root, merge_commit):
            unknown_commit_sha.append(f"{card_id}:{merge_commit}")
            checked_cards.append(card_result)
            continue
        baseline_visible = _is_ancestor(repo_root, merge_commit, baseline_sha)
        card_result["baseline_visible"] = baseline_visible
        if not baseline_visible:
            not_merged_to_baseline.append(f"{card_id}:{merge_commit}")

        card_status = status_map.get(card_id)
        if card_status and card_status != "done":
            status_not_done.append(f"{card_id}:{card_status}")

        checked_cards.append(card_result)

    errors: list[str] = []
    if missing_merge_result:
        errors.append(f"缺少 merge_result.json: {missing_merge_result}")
    if merge_result_invalid:
        errors.append(f"merge_result 非 merged=true: {merge_result_invalid}")
    if missing_commit_sha:
        errors.append(f"merge_result 缺少 merge_commit: {missing_commit_sha}")
    if unknown_commit_sha:
        errors.append(f"merge_commit 在仓库不存在: {unknown_commit_sha}")
    if not_merged_to_baseline:
        errors.append(f"merge_commit 非 {baseline} 可见祖先: {not_merged_to_baseline}")
    if status_not_done:
        errors.append(f"state 中实现卡非 done: {status_not_done}")

    return {
        "ok": not errors,
        "task_key": task_key,
        "task_split_dir": str(task_split_dir),
        "baseline": baseline,
        "baseline_sha": baseline_sha,
        "state_dir": str(state_dir),
        "resolved_state_dir": str(resolved_state_dir),
        "merge_required_cards": merge_required_cards,
        "checked_cards": checked_cards,
        "errors": errors,
    }


def _write_output(path: str, payload: dict[str, Any]) -> None:
    if not path:
        return
    if path == "-":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    output_path = Path(path).expanduser()
    if not output_path.is_absolute():
        output_path = (ROOT / output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="IG01 集成门禁校验")
    parser.add_argument("--task-split-dir", required=True, help="任务拆解目录名或绝对路径")
    parser.add_argument("--baseline", default="master", help="主干基线分支（默认 master）")
    parser.add_argument("--state-dir", default=str(DEFAULT_STATE_DIR), help="状态目录（默认 .omc/state）")
    parser.add_argument("--repo-root", default=str(ROOT), help="仓库根目录")
    parser.add_argument("--output", default="", help="可选输出 JSON 文件路径，'-' 表示打印 JSON")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).expanduser().resolve()
    state_dir = Path(args.state_dir).expanduser()
    if not state_dir.is_absolute():
        state_dir = (repo_root / state_dir).resolve()

    try:
        task_split_dir = _resolve_task_split_dir(repo_root, args.task_split_dir)
        result = run_check(
            repo_root=repo_root,
            task_split_dir=task_split_dir,
            state_dir=state_dir,
            baseline=args.baseline,
        )
    except IntegrationGateError as exc:
        print(f"INTEGRATION_GATE: FAIL\n- {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"INTEGRATION_GATE: FAIL\n- unexpected error: {exc}", file=sys.stderr)
        return 1

    if result["ok"]:
        print("INTEGRATION_GATE: PASS")
        print(
            f"- baseline={args.baseline} merge_required_cards="
            f"{len(result['merge_required_cards'])}"
        )
        _write_output(args.output, result)
        return 0

    print("INTEGRATION_GATE: FAIL", file=sys.stderr)
    for issue in result["errors"]:
        print(f"- {issue}", file=sys.stderr)
    _write_output(args.output, result)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
