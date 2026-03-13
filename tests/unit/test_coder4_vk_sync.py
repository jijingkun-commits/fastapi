"""coder4 VK 只读同步脚本回归测试。"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


SCRIPT_PATH = Path("scripts/coder4_vk_sync.py")
TASK_KEY = "PP-20260228-AUTO-LARGE-TASK-HOST"
TASK_SPLIT_DIR = "2026-02-28_自动化大型任务开发_主机方案"


def _load_module():
    module_name = f"coder4_vk_sync_test_{uuid.uuid4().hex}"
    spec = spec_from_file_location(module_name, SCRIPT_PATH)
    assert spec and spec.loader
    module = module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _prepare_workspace(tmp_path: Path) -> tuple[Path, Path]:
    (tmp_path / ".git").mkdir(parents=True)
    (tmp_path / "scripts").mkdir(parents=True, exist_ok=True)
    (tmp_path / "scripts" / "set_active_task.py").write_text("# test stub\n", encoding="utf-8")

    active_task_index_path = tmp_path / "workdocs" / "任务拆解" / "_active_task.json"
    active_task_path = tmp_path / "workdocs" / "任务拆解" / TASK_SPLIT_DIR / "contracts" / "_active_task.json"
    _write_json(
        active_task_path,
        {
            "project_id": "vk-project-1",
            "task_split_dir": TASK_SPLIT_DIR,
            "task_key": TASK_KEY,
            "execution_mode": "serial",
            "single_active_card": True,
            "preflight_required": "C00",
            "status_source_of_truth": "",
        },
    )
    _write_json(
        active_task_index_path,
        {
            "project_id": "vk-project-1",
            "task_split_dir": TASK_SPLIT_DIR,
            "task_key": TASK_KEY,
            "execution_mode": "serial",
            "single_active_card": True,
            "preflight_required": "C00",
            "status_source_of_truth": "",
            "active_task_path": str(active_task_path),
        },
    )

    cards = [
        {
            "card_id": "C01",
            "title": "C01 preflight",
            "hard_depends_on": [],
            "task_mode": "implementation-card",
            "merge_required": True,
        },
        {
            "card_id": "C02",
            "title": "C02 kernel",
            "hard_depends_on": ["C01"],
            "task_mode": "implementation-card",
            "merge_required": True,
        },
        {
            "card_id": "C03",
            "title": "C03 follow-up",
            "hard_depends_on": ["C02"],
            "task_mode": "implementation-card",
            "merge_required": True,
        },
    ]
    _write_json(
        active_task_path.parent / "vk_cards.json",
        {
            "card_order": ["C01", "C02", "C03"],
            "cards": cards,
        },
    )

    state_path = tmp_path / ".omc" / "state" / "task-runner-state.json"
    _write_json(
        state_path,
        {
            "schema_version": "1.0.0",
            "task_key": TASK_KEY,
            "card_order": ["C01", "C02", "C03"],
            "card_status_map": {
                "C01": "done",
                "C02": "inprogress",
                "C03": "todo",
            },
        },
    )

    return active_task_path, state_path


def _build_args(active_task_path: Path, state_path: Path, **kwargs):
    payload = {
        "active_task": str(active_task_path),
        "state_file": str(state_path),
        "vk_api_base": "http://127.0.0.1:3001",
        "project_id": "",
        "task_key": "",
        "card_id": "",
        "status": "",
        "sync_all": False,
        "dry_run": False,
        "strict": False,
        "timeout_seconds": 8,
        "output": "",
    }
    payload.update(kwargs)
    return argparse.Namespace(**payload)


def test_run_sync_all_cards_dry_run_reports_reconciliation(monkeypatch, tmp_path):
    module = _load_module()
    active_task_path, state_path = _prepare_workspace(tmp_path)

    def _fake_fetch_scoped_task_map(_ctx):
        return {
            "C01": {
                "id": "task-c01",
                "status": "todo",
                "title": "C01 preflight",
                "description": "card_id: C01\n",
            },
            "C02": {
                "id": "task-c02",
                "status": "inprogress",
                "title": "C02 kernel",
                "description": "card_id: C02\n",
            },
        }

    monkeypatch.setattr(module, "fetch_scoped_task_map", _fake_fetch_scoped_task_map)
    monkeypatch.setattr(module, "DEFAULT_REPO_ROOT", tmp_path.resolve())

    payload = module.run_sync(
        _build_args(
            active_task_path,
            state_path,
            sync_all=True,
            dry_run=True,
        )
    )

    assert payload["mode"] == "sync_all_cards"
    assert payload["has_failed"] is False

    by_card = {item["card_id"]: item for item in payload["results"]}
    assert by_card["C01"]["sync_result"] == "dry_run_update"
    assert by_card["C02"]["sync_result"] == "noop_already_in_sync"
    assert by_card["C03"]["sync_result"] == "dry_run_create"


def test_run_sync_single_card_respects_disable_env(monkeypatch, tmp_path):
    module = _load_module()
    active_task_path, state_path = _prepare_workspace(tmp_path)

    def _unexpected_fetch(_ctx):
        raise AssertionError("disabled 模式不应访问 VK 任务列表")

    monkeypatch.setenv("DISABLE_VK_SYNC", "1")
    monkeypatch.setattr(module, "fetch_scoped_task_map", _unexpected_fetch)
    monkeypatch.setattr(module, "DEFAULT_REPO_ROOT", tmp_path.resolve())

    payload = module.run_sync(
        _build_args(
            active_task_path,
            state_path,
            card_id="C02",
            status="done",
        )
    )

    assert payload["mode"] == "sync_to_vk"
    assert payload["has_failed"] is False
    assert payload["result"]["sync_result"] == "skipped_disabled"


def test_main_strict_exit_nonzero_on_failed_sync(monkeypatch, tmp_path, capsys):
    module = _load_module()
    active_task_path, state_path = _prepare_workspace(tmp_path)

    args = _build_args(
        active_task_path,
        state_path,
        card_id="C02",
        status="inprogress",
        strict=True,
    )

    monkeypatch.setattr(module, "parse_args", lambda: args)
    monkeypatch.setattr(
        module,
        "run_sync",
        lambda _args: {
            "mode": "sync_to_vk",
            "has_failed": True,
            "result": {
                "card_id": "C02",
                "sync_result": "failed",
            },
        },
    )

    exit_code = module.main()
    assert exit_code == 1

    output = capsys.readouterr().out.strip().splitlines()[-1]
    payload = json.loads(output)
    assert payload["ok"] is False
    assert payload["strict_mode"] is True


def test_build_vktodo_card_title_injects_main_task_name_before_subtask():
    module = _load_module()

    title = module.build_vktodo_card_title(
        raw_title="G01 Gate 统一质量门禁 [PP-20260301-KB-RETRIEVAL-P2]",
        card_id="G01",
        task_key="PP-20260301-KB-RETRIEVAL-P2",
        main_task_name="知识库检索P2分阶段治理",
    )

    assert title == "G01 Gate 知识库检索P2分阶段治理 统一质量门禁 [PP-20260301-KB-RETRIEVAL-P2]"


def test_extract_main_task_name_removes_date_prefix():
    module = _load_module()

    assert module.extract_main_task_name("2026-03-01_知识库检索P2分阶段治理") == "知识库检索P2分阶段治理"
    assert module.extract_main_task_name("知识库检索P2分阶段治理") == "知识库检索P2分阶段治理"
