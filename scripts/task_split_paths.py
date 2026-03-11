#!/usr/bin/env python3
"""Canonical task_split path resolver.

单一职责：统一解析 task_split 的 canonical 目录、contracts/reports 路径与运行态根目录。
默认只认：
- 过程层 root: workdocs/任务拆解/<task_split_dir>
- 运行态 root: .artifacts/states/task_splits/<task_split_dir>/<task_key>

兼容仅体现在“读旧入参”上：允许把 docs 旧路径字符串解析成新 canonical 路径，
也允许把根索引 `_active_task.json` 解析成当前 task_split；
但不在这里制造双写或长期 fallback。
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

CANONICAL_TASK_SPLIT_BASE = Path("workdocs/任务拆解")
LEGACY_TASK_SPLIT_BASE = Path("docs/内部参考/任务拆解")
TASK_ACTIVE_FILENAME = "_active_task.json"
DEFAULT_ACTIVE_TASK_INDEX_PATH = str(CANONICAL_TASK_SPLIT_BASE / TASK_ACTIVE_FILENAME)
VK_CARDS_FILENAME = "vk_cards.json"
PARALLEL_PLAN_FILENAME = "parallel_plan.md"
CONTRACTS_DIRNAME = "contracts"
REPORTS_DIRNAME = "reports"
SYNC_DIRNAME = "sync"
WORKSTREAMS_DIRNAME = "workstreams"
TASK_SPLIT_RUNTIME_BASE = Path(".artifacts/states/task_splits")
REPORT_FILENAMES = {
    "preflight_status.json",
    "consumption_report.json",
    "gate_contract_report.json",
}
SYNC_FILENAMES = {
    "vktodo_create_result.json",
    "vksync_status.json",
}


def detect_repo_root(start: Path) -> Path:
    resolved = start.resolve()
    for ancestor in (resolved, *resolved.parents):
        if (ancestor / ".git").exists():
            return ancestor
    return resolved.parents[1]


ROOT = detect_repo_root(Path(__file__))


@dataclass(frozen=True)
class TaskSplitPaths:
    repo_root: Path
    task_split_dir: str
    canonical_task_split_dir: Path
    legacy_task_split_dir: Path
    legacy_input_used: bool = False

    @property
    def contracts_dir(self) -> Path:
        return self.canonical_task_split_dir / CONTRACTS_DIRNAME

    @property
    def reports_dir(self) -> Path:
        return self.canonical_task_split_dir / REPORTS_DIRNAME

    @property
    def sync_dir(self) -> Path:
        return self.reports_dir / SYNC_DIRNAME

    @property
    def workstreams_dir(self) -> Path:
        return self.canonical_task_split_dir / WORKSTREAMS_DIRNAME

    @property
    def parallel_plan_file(self) -> Path:
        return self.canonical_task_split_dir / PARALLEL_PLAN_FILENAME

    @property
    def active_task_index_file(self) -> Path:
        return self.repo_root / CANONICAL_TASK_SPLIT_BASE / TASK_ACTIVE_FILENAME

    @property
    def active_task_file(self) -> Path:
        return self.contracts_dir / TASK_ACTIVE_FILENAME

    @property
    def legacy_active_task_file(self) -> Path:
        return self.legacy_task_split_dir / TASK_ACTIVE_FILENAME

    @property
    def vk_cards_file(self) -> Path:
        return self.contracts_dir / VK_CARDS_FILENAME

    @property
    def legacy_vk_cards_file(self) -> Path:
        return self.legacy_task_split_dir / VK_CARDS_FILENAME

    @property
    def preflight_status_file(self) -> Path:
        return self.reports_dir / "preflight_status.json"

    @property
    def consumption_report_file(self) -> Path:
        return self.reports_dir / "consumption_report.json"

    @property
    def gate_contract_report_file(self) -> Path:
        return self.reports_dir / "gate_contract_report.json"

    @property
    def vktodo_create_result_file(self) -> Path:
        return self.sync_dir / "vktodo_create_result.json"

    @property
    def vksync_status_file(self) -> Path:
        return self.sync_dir / "vksync_status.json"

    @property
    def runtime_task_split_dir(self) -> Path:
        return self.repo_root / TASK_SPLIT_RUNTIME_BASE / self.task_split_dir

    def runtime_state_dir(self, task_key: str | None = None) -> Path:
        normalized = sanitize_task_key_segment(task_key or "")
        return self.runtime_task_split_dir / normalized if normalized else self.runtime_task_split_dir

    def to_payload(self, *, task_key: str = "") -> dict[str, Any]:
        payload = {
            "task_split_dir": self.task_split_dir,
            "canonical_task_split_dir": str(self.canonical_task_split_dir),
            "legacy_task_split_dir": str(self.legacy_task_split_dir),
            "contracts_dir": str(self.contracts_dir),
            "reports_dir": str(self.reports_dir),
            "sync_dir": str(self.sync_dir),
            "workstreams_dir": str(self.workstreams_dir),
            "parallel_plan_file": str(self.parallel_plan_file),
            "active_task_index_file": str(self.active_task_index_file),
            "active_task_file": str(self.active_task_file),
            "vk_cards_file": str(self.vk_cards_file),
            "preflight_status_file": str(self.preflight_status_file),
            "consumption_report_file": str(self.consumption_report_file),
            "gate_contract_report_file": str(self.gate_contract_report_file),
            "vktodo_create_result_file": str(self.vktodo_create_result_file),
            "vksync_status_file": str(self.vksync_status_file),
            "runtime_task_split_dir": str(self.runtime_task_split_dir),
            "legacy_input_used": self.legacy_input_used,
        }
        if task_key:
            payload["runtime_state_dir"] = str(self.runtime_state_dir(task_key))
        return payload


def sanitize_task_key_segment(task_key: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9._-]+", "_", str(task_key or "").strip())
    normalized = normalized.strip("._")
    return normalized or ""


def _load_json_object(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be object: {path}")
    return payload


def _is_relative_to(path: Path, base: Path) -> bool:
    try:
        path.relative_to(base)
        return True
    except ValueError:
        return False


def _canonical_base(repo_root: Path) -> Path:
    return (repo_root / CANONICAL_TASK_SPLIT_BASE).resolve()


def _legacy_base(repo_root: Path) -> Path:
    return (repo_root / LEGACY_TASK_SPLIT_BASE).resolve()


def _active_task_index_candidates(repo_root: Path) -> tuple[Path, Path]:
    repo_root = repo_root.resolve()
    return (
        (_canonical_base(repo_root) / TASK_ACTIVE_FILENAME).resolve(),
        (_legacy_base(repo_root) / TASK_ACTIVE_FILENAME).resolve(),
    )


def _match_active_task_index(repo_root: Path, raw_value: str) -> Path | None:
    raw = str(raw_value or "").strip()
    if not raw:
        return None

    direct = Path(raw).expanduser()
    candidates = [direct] if direct.is_absolute() else [(repo_root / direct), direct]
    canonical_index, legacy_index = _active_task_index_candidates(repo_root)
    for candidate in candidates:
        resolved = candidate.resolve() if candidate.is_absolute() else (repo_root / candidate).resolve()
        if resolved == canonical_index or resolved == legacy_index:
            return canonical_index
    return None


def _task_split_from_active_index(repo_root: Path, index_path: Path) -> str:
    if not index_path.exists():
        raise FileNotFoundError(f"active task index not found: {index_path}")
    payload = _load_json_object(index_path)
    task_split_dir = str(payload.get("task_split_dir") or "").strip()
    if not task_split_dir:
        raise FileNotFoundError(f"active task index missing task_split_dir: {index_path}")
    return task_split_dir


def _extract_task_split_name(repo_root: Path, candidate: Path) -> str:
    repo_root = repo_root.resolve()
    canonical_base = _canonical_base(repo_root)
    legacy_base = _legacy_base(repo_root)

    for base in (canonical_base, legacy_base):
        if _is_relative_to(candidate, base):
            rel = candidate.relative_to(base)
            if rel.parts and not rel.parts[0].startswith("_"):
                return rel.parts[0]
    return ""


def _candidate_paths(repo_root: Path, raw_value: str) -> list[Path]:
    raw = str(raw_value or "").strip()
    if not raw:
        return []
    direct = Path(raw).expanduser()
    if direct.is_absolute():
        return [direct]
    return [
        (repo_root / raw),
        (_canonical_base(repo_root) / raw),
        (_legacy_base(repo_root) / raw),
    ]


def resolve_task_split_paths(repo_root: Path, raw_value: str, *, must_exist: bool = True) -> TaskSplitPaths:
    repo_root = repo_root.resolve()
    raw = str(raw_value or "").strip()
    if not raw:
        raise FileNotFoundError("missing task_split_dir")

    task_split_dir = ""
    legacy_input_used = False

    index_path = _match_active_task_index(repo_root, raw)
    if index_path is not None:
        task_split_dir = _task_split_from_active_index(repo_root, index_path)
        _, legacy_index = _active_task_index_candidates(repo_root)
        legacy_input_used = Path(raw).expanduser().resolve() == legacy_index if Path(raw).expanduser().is_absolute() else False

    if not task_split_dir:
        for candidate in _candidate_paths(repo_root, raw):
            task_split_dir = _extract_task_split_name(repo_root, candidate)
            if task_split_dir:
                if _is_relative_to(candidate, _legacy_base(repo_root)):
                    legacy_input_used = True
                break

    if not task_split_dir and "/" not in raw and "\\" not in raw:
        task_split_dir = raw

    if not task_split_dir:
        raise FileNotFoundError(f"cannot resolve task_split_dir: {raw}")

    locator = TaskSplitPaths(
        repo_root=repo_root,
        task_split_dir=task_split_dir,
        canonical_task_split_dir=(_canonical_base(repo_root) / task_split_dir).resolve(),
        legacy_task_split_dir=(_legacy_base(repo_root) / task_split_dir).resolve(),
        legacy_input_used=legacy_input_used,
    )
    if must_exist and not locator.canonical_task_split_dir.exists():
        raise FileNotFoundError(f"canonical task_split_dir not found: {locator.canonical_task_split_dir}")
    return locator


def iter_task_split_paths(repo_root: Path) -> list[TaskSplitPaths]:
    repo_root = repo_root.resolve()
    base = _canonical_base(repo_root)
    if not base.exists():
        return []
    results: list[TaskSplitPaths] = []
    for item in sorted(base.iterdir()):
        if not item.is_dir() or item.name.startswith("_"):
            continue
        results.append(resolve_task_split_paths(repo_root, item.name, must_exist=True))
    return results


def resolve_active_task_path(repo_root: Path, raw_active_task: str = "") -> Path:
    repo_root = repo_root.resolve()
    raw = str(raw_active_task or "").strip()
    canonical_index, _legacy_index = _active_task_index_candidates(repo_root)

    if raw:
        index_match = _match_active_task_index(repo_root, raw)
        if index_match is not None:
            if not canonical_index.exists():
                raise FileNotFoundError(f"active task index not found: {canonical_index}")
            return canonical_index.resolve()
        locator = resolve_task_split_paths(repo_root, raw, must_exist=False)
        candidate = locator.active_task_file
        if not candidate.exists():
            raise FileNotFoundError(f"active task not found: {candidate}")
        return candidate.resolve()

    if canonical_index.exists():
        return canonical_index.resolve()

    candidates = [item.active_task_file for item in iter_task_split_paths(repo_root) if item.active_task_file.is_file()]
    if not candidates:
        raise FileNotFoundError("未找到任务级 _active_task.json，请显式传 --active-task 或设置 CODER4_ACTIVE_TASK_FILE")
    if len(candidates) > 1:
        raise FileNotFoundError(f"检测到多个任务级 _active_task.json（{len(candidates)} 个），请显式传 --active-task 或设置 CODER4_ACTIVE_TASK_FILE")
    return candidates[0].resolve()


def resolve_runtime_path(*, repo_root: Path, task_split_dir: str, raw_path: str, task_key: str = "") -> Path:
    repo_root = repo_root.resolve()
    target = Path(str(raw_path or "").strip()).expanduser()
    if target.is_absolute():
        return target.resolve()

    locator = resolve_task_split_paths(repo_root, task_split_dir, must_exist=False)
    raw = str(raw_path or "").strip()
    if raw in {".state", "./.state"}:
        return locator.runtime_task_split_dir.resolve()
    if raw.startswith(".state/") or raw.startswith("./.state/"):
        suffix = raw.split(".state/", 1)[1]
        if task_key:
            suffix = suffix.replace("{task_key}", sanitize_task_key_segment(task_key))
        return (locator.runtime_task_split_dir / suffix).resolve()
    return (repo_root / target).resolve()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Resolve canonical task_split paths")
    sub = parser.add_subparsers(dest="command", required=True)

    locate = sub.add_parser("locate", help="resolve task_split paths")
    locate.add_argument("--repo-root", default=str(ROOT))
    locate.add_argument("--task-split-dir", default="")
    locate.add_argument("--active-task", default="")
    locate.add_argument("--task-key", default="")
    locate.add_argument("--output", default="-")

    resolve_active = sub.add_parser("resolve-active-task", help="resolve active task path")
    resolve_active.add_argument("--repo-root", default=str(ROOT))
    resolve_active.add_argument("--active-task", default="")
    resolve_active.add_argument("--output", default="-")

    list_cmd = sub.add_parser("list-active-tasks", help="list task-scoped active task files")
    list_cmd.add_argument("--repo-root", default=str(ROOT))
    list_cmd.add_argument("--output", default="-")
    return parser


def _write_output(output: str, payload: Any) -> None:
    data = json.dumps(payload, ensure_ascii=False, indent=2)
    if output in {"", "-"}:
        print(data)
        return
    path = Path(output).expanduser()
    if not path.is_absolute():
        path = (ROOT / path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data + "\n", encoding="utf-8")


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    repo_root = Path(args.repo_root).expanduser().resolve()

    if args.command == "locate":
        raw = str(args.task_split_dir or args.active_task or "").strip()
        if not raw:
            raise SystemExit("locate 缺少 --task-split-dir 或 --active-task")
        locator = resolve_task_split_paths(repo_root, raw, must_exist=False)
        _write_output(args.output, locator.to_payload(task_key=str(args.task_key or "")))
        return 0

    if args.command == "resolve-active-task":
        payload = {"active_task_file": str(resolve_active_task_path(repo_root, args.active_task))}
        _write_output(args.output, payload)
        return 0

    if args.command == "list-active-tasks":
        payload = {
            "active_task_files": [str(item.active_task_file) for item in iter_task_split_paths(repo_root) if item.active_task_file.is_file()]
        }
        _write_output(args.output, payload)
        return 0

    raise SystemExit(f"unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
