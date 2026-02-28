"""coder4 bootstrap kernel 本地模式回归测试。"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


SCRIPT_PATH = Path("scripts/coder4_bootstrap_kernel.py")
TASK_KEY = "PP-20260228-AUTO-LARGE-TASK-HOST"
TASK_SPLIT_DIR = "2026-02-28_自动化大型任务开发_主机方案"


def _load_kernel_module():
    module_name = f"coder4_bootstrap_kernel_test_{uuid.uuid4().hex}"
    spec = spec_from_file_location(module_name, SCRIPT_PATH)
    assert spec and spec.loader
    module = module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _prepare_workspace(tmp_path: Path, *, state_payload: dict | None = None) -> tuple[Path, Path, list[str], dict]:
    (tmp_path / ".git").mkdir(parents=True)
    (tmp_path / "scripts").mkdir(parents=True, exist_ok=True)
    (tmp_path / "scripts" / "set_active_task.py").write_text("# test stub\n", encoding="utf-8")

    active_task_path = tmp_path / "docs" / "内部参考" / "任务拆解" / "_active_task.json"
    _write_json(
        active_task_path,
        {
            "project_id": "test-project-id",
            "task_split_dir": TASK_SPLIT_DIR,
            "task_key": TASK_KEY,
            "execution_mode": "serial",
            "single_active_card": True,
            "preflight_required": "C01",
            "status_source_of_truth": "",
        },
    )

    card_order = ["C01", "C02", "C03"]
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
    vk_cards_path = active_task_path.parent / TASK_SPLIT_DIR / "vk_cards.json"
    _write_json(vk_cards_path, {"card_order": card_order, "cards": cards})

    state_path = tmp_path / ".omc" / "state" / "task-runner-state.json"
    if state_payload is None:
        state_payload = {
            "schema_version": "1.0.0",
            "task_key": TASK_KEY,
            "card_order": card_order,
            "card_status_map": {
                "C01": "done",
                "C02": "todo",
            },
            "last_updated": "2026-02-28T12:00:00+00:00",
            "created_at": "2026-02-28T10:00:00+00:00",
        }
    _write_json(state_path, state_payload)

    cards_by_id = {card["card_id"]: card for card in cards}
    return active_task_path, state_path, card_order, cards_by_id


def test_build_kernel_context_local_mode_skips_vk_task_fetch(monkeypatch, tmp_path):
    """local-mode 构建上下文不应调用 VK 任务列表接口。"""

    module = _load_kernel_module()
    active_task_path, state_path, _, _ = _prepare_workspace(tmp_path)

    def _unexpected_list_tasks(*args, **kwargs):
        raise AssertionError("local-mode 不应调用 list_tasks")

    monkeypatch.setattr(module, "list_tasks", _unexpected_list_tasks)

    ctx = module.build_kernel_context(
        active_task_path,
        "http://127.0.0.1:3001",
        local_mode=True,
        state_path=state_path,
    )

    assert ctx.preflight_ok is True
    assert ctx.card_status_map["C01"] == "done"
    assert ctx.card_status_map["C02"] == "todo"


def test_build_kernel_context_local_mode_ignores_status_source_of_truth(monkeypatch, tmp_path):
    """local-mode 预检仅依赖本地状态，不应被状态来源文档放行。"""

    module = _load_kernel_module()
    active_task_path, state_path, _, _ = _prepare_workspace(
        tmp_path,
        state_payload={
            "schema_version": "1.0.0",
            "task_key": TASK_KEY,
            "card_order": ["C01", "C02", "C03"],
            "card_status_map": {
                "C02": "todo",
            },
        },
    )

    source_path = tmp_path / "preflight_source.json"
    _write_json(
        source_path,
        {
            "preflight_required": "C01",
            "passed": True,
        },
    )

    active_payload = json.loads(active_task_path.read_text(encoding="utf-8"))
    active_payload["status_source_of_truth"] = str(source_path)
    _write_json(active_task_path, active_payload)

    def _unexpected_list_tasks(*args, **kwargs):
        raise AssertionError("local-mode 不应调用 list_tasks")

    monkeypatch.setattr(module, "list_tasks", _unexpected_list_tasks)

    ctx = module.build_kernel_context(
        active_task_path,
        "http://127.0.0.1:3001",
        local_mode=True,
        state_path=state_path,
    )

    assert ctx.preflight_ok is False
    assert ctx.preflight_reason == "C01_not_done"


def test_apply_action_local_mode_updates_runtime_fields_without_http(monkeypatch, tmp_path):
    """seed/activate 在 local-mode 下应只写本地状态并记录运行字段。"""

    module = _load_kernel_module()
    _, state_path, card_order, cards_by_id = _prepare_workspace(tmp_path)
    _write_json(
        state_path,
        {
            "schema_version": "1.0.0",
            "task_key": TASK_KEY,
            "card_order": card_order,
            "card_status_map": {
                "C01": "done",
            },
        },
    )

    def _unexpected_http(*args, **kwargs):
        raise AssertionError("local-mode 不应发起 HTTP 调用")

    sync_calls: list[tuple[str, str]] = []

    def _fake_try_sync_vk(**kwargs):
        sync_calls.append((kwargs["card_id"], kwargs["status"]))
        return {
            "attempted": True,
            "ok": True,
            "disabled": False,
            "reason": "spawned",
            "card_id": kwargs["card_id"],
            "status": kwargs["status"],
        }

    monkeypatch.setattr(module, "http_json", _unexpected_http)
    monkeypatch.setattr(module, "_try_sync_vk", _fake_try_sync_vk)

    ctx = module.KernelContext(
        project_id="",
        task_key=TASK_KEY,
        execution_mode="serial",
        preflight_required="C01",
        preflight_ok=True,
        preflight_reason="preflight_card_done",
        card_order=card_order,
        cards_by_id=cards_by_id,
        scoped_tasks=[],
        unscoped_tasks=[],
        card_status_map={"C01": "done"},
        card_task_map={},
    )

    seed_result = module.apply_action(
        "http://127.0.0.1:3001",
        ctx,
        "seed",
        "C02",
        None,
        active_task_path=tmp_path / "docs" / "内部参考" / "任务拆解" / "_active_task.json",
        local_mode=True,
        state_path=state_path,
    )
    assert seed_result["performed"] is True
    assert seed_result["vk_sync"]["ok"] is True

    state_after_seed = json.loads(state_path.read_text(encoding="utf-8"))
    assert state_after_seed["card_status_map"]["C02"] == "todo"
    assert state_after_seed["card_status"]["C02"] == "todo"
    assert state_after_seed["current_card"] == "C02"
    assert state_after_seed["last_action"] == "seed"
    assert state_after_seed["last_action_result"] == "CARD_SEEDED:C02"

    activate_result = module.apply_action(
        "http://127.0.0.1:3001",
        ctx,
        "activate",
        "C02",
        None,
        active_task_path=tmp_path / "docs" / "内部参考" / "任务拆解" / "_active_task.json",
        local_mode=True,
        state_path=state_path,
    )
    assert activate_result["performed"] is True
    assert activate_result["vk_sync"]["ok"] is True

    state_after_activate = json.loads(state_path.read_text(encoding="utf-8"))
    assert state_after_activate["card_status_map"]["C02"] == "inprogress"
    assert state_after_activate["card_status"]["C02"] == "inprogress"
    assert state_after_activate["current_card"] == "C02"
    assert state_after_activate["last_action"] == "activate"
    assert state_after_activate["last_action_result"] == "CARD_ACTIVATED:C02"
    assert sync_calls == [("C02", "todo"), ("C02", "inprogress")]


def test_main_local_mode_triggers_auto_wake_after_card_done(monkeypatch, tmp_path, capsys):
    """检测到前序卡片完成后，kernel 应立即触发下一轮 wake。"""

    module = _load_kernel_module()
    active_task_path, state_path, _, _ = _prepare_workspace(tmp_path)

    wake_calls: list[str] = []

    def _fake_trigger_next_round(reason: str):
        wake_calls.append(reason)
        return {
            "attempted": True,
            "ok": True,
            "status_code": 202,
            "reason": reason,
            "disabled": False,
            "gateway": "http://localhost:18789",
        }

    monkeypatch.setattr(module, "trigger_next_round", _fake_trigger_next_round, raising=False)

    args = argparse.Namespace(
        active_task=str(active_task_path),
        vk_api_base="http://127.0.0.1:3001",
        local_mode=True,
        state_file=str(state_path),
        attempts_dir=str(tmp_path / ".omc" / "state" / "attempts"),
        task_ledger_file=str(tmp_path / ".omc" / "state" / "task-ledger.jsonl"),
        run_lock_file=str(tmp_path / ".omc" / "state" / "coder4-run.lock"),
        idempotency_file=str(tmp_path / ".omc" / "state" / "coder4-idempotency.json"),
        apply_bootstrap=True,
        trigger_source="manual",
        idempotency_key="",
        idempotency_window_seconds=120,
        output="",
    )
    monkeypatch.setattr(module, "parse_args", lambda: args)

    exit_code = module.main()

    assert exit_code == 0
    captured = capsys.readouterr()
    result = json.loads(captured.out.strip().splitlines()[-1])

    assert result["action"] == "activate"
    assert result["auto_wake"]["attempted"] is True
    assert result["auto_wake"]["ok"] is True
    assert result["execution_mode"] == "serial"
    assert result["attempt"]["result"] == "card_activated"
    assert Path(result["attempt"]["attempt_file"]).exists()
    assert Path(result["task_ledger_file"]).exists()
    assert len(wake_calls) == 1

    ledger_lines = Path(result["task_ledger_file"]).read_text(encoding="utf-8").strip().splitlines()
    assert ledger_lines
    latest_ledger = json.loads(ledger_lines[-1])
    assert latest_ledger["task_key"] == TASK_KEY
    assert latest_ledger["card_id"] == "C02"
    assert latest_ledger["attempt_id"] == result["attempt"]["attempt_id"]

    refreshed_state = json.loads(state_path.read_text(encoding="utf-8"))
    assert refreshed_state["last_auto_wake_card"] == "C01"
    assert refreshed_state["last_action_result"] == "CARD_ACTIVATED:C02"
