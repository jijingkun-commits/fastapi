"""set_active_task 脚本回归测试。"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


SCRIPT_PATH = Path("scripts/set_active_task.py")
TASK_SPLIT_DIR = "2026-03-01_任务作用域存储迁移"
TASK_KEY = "PP-20260301-ACTIVE-TASK-STORAGE"


def _load_module():
    module_name = f"set_active_task_test_{uuid.uuid4().hex}"
    spec = spec_from_file_location(module_name, SCRIPT_PATH)
    assert spec and spec.loader
    module = module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _prepare_repo_root(tmp_path: Path) -> tuple[Path, Path]:
    repo_root = tmp_path / "repo"
    split_dir = repo_root / "docs" / "内部参考" / "任务拆解" / TASK_SPLIT_DIR
    split_dir.mkdir(parents=True, exist_ok=True)
    (repo_root / "scripts").mkdir(parents=True, exist_ok=True)
    (repo_root / "scripts" / "set_active_task.py").write_text("# placeholder\n", encoding="utf-8")
    _write_json(
        split_dir / "vk_cards.json",
        {
            "task_key": TASK_KEY,
            "execution_mode": "serial",
            "single_active_card": True,
            "auto_done_policy": {
                "implementation-card": "hard_gate",
                "inspection/question-card": "policy_gate",
            },
            "preflight": {"card_id": "C00"},
        },
    )
    _write_json(
        split_dir / "preflight_status.json",
        {
            "preflight_required": "C00",
            "passed": True,
        },
    )
    return repo_root, split_dir


def test_set_active_task_writes_task_scoped_and_index_files(monkeypatch, tmp_path):
    module = _load_module()
    repo_root, split_dir = _prepare_repo_root(tmp_path)
    monkeypatch.setattr(module, "__file__", str(repo_root / "scripts" / "set_active_task.py"))

    args = argparse.Namespace(
        task_split_dir=TASK_SPLIT_DIR,
        project_id="project-1",
        auto_done_policy="hard_gate",
        status_source_of_truth=None,
        updated_by="unit-test",
        active_task_path="docs/内部参考/任务拆解/_active_task.json",
    )
    monkeypatch.setattr(module, "parse_args", lambda: args)

    assert module.main() == 0

    task_scoped_path = split_dir / "_active_task.json"
    active_index_path = repo_root / "docs" / "内部参考" / "任务拆解" / "_active_task.json"
    assert task_scoped_path.exists()
    assert active_index_path.exists()

    task_payload = json.loads(task_scoped_path.read_text(encoding="utf-8"))
    index_payload = json.loads(active_index_path.read_text(encoding="utf-8"))
    assert task_payload["task_key"] == TASK_KEY
    assert task_payload["task_split_dir"] == TASK_SPLIT_DIR
    assert index_payload["task_key"] == TASK_KEY
    assert index_payload["active_task_path"] == str(task_scoped_path.resolve())


def test_set_active_task_respects_custom_index_path(monkeypatch, tmp_path):
    module = _load_module()
    repo_root, split_dir = _prepare_repo_root(tmp_path)
    monkeypatch.setattr(module, "__file__", str(repo_root / "scripts" / "set_active_task.py"))

    args = argparse.Namespace(
        task_split_dir=TASK_SPLIT_DIR,
        project_id="project-2",
        auto_done_policy="hard_gate",
        status_source_of_truth=None,
        updated_by="unit-test",
        active_task_path="docs/内部参考/任务拆解/_active_task.index.json",
    )
    monkeypatch.setattr(module, "parse_args", lambda: args)

    assert module.main() == 0

    task_scoped_path = split_dir / "_active_task.json"
    custom_index_path = repo_root / "docs" / "内部参考" / "任务拆解" / "_active_task.index.json"
    assert task_scoped_path.exists()
    assert custom_index_path.exists()

    index_payload = json.loads(custom_index_path.read_text(encoding="utf-8"))
    assert index_payload["active_task_path"] == str(task_scoped_path.resolve())

