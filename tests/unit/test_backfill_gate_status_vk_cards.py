"""backfill_gate_status 回写 vk_cards 并生成 parallel_plan 总览的回归测试。"""

from __future__ import annotations

import json
import sys
import uuid
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


SCRIPT_PATH = Path("scripts/backfill_gate_status.py")
TASK_SPLIT_DIR = "2026-03-08_parallel-plan-summary"
TASK_KEY = "PP-20260308-PARALLEL-PLAN-SUMMARY"


def _load_module():
    module_name = f"backfill_gate_status_test_{uuid.uuid4().hex}"
    spec = spec_from_file_location(module_name, SCRIPT_PATH)
    assert spec and spec.loader
    module = module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _prepare_fixture(tmp_path: Path) -> tuple[Path, Path, Path]:
    repo_root = tmp_path / "repo"
    task_dir = repo_root / "workdocs" / "任务拆解" / TASK_SPLIT_DIR
    impl_path = repo_root / "workdocs" / "归档" / "实施计划" / "parallel-plan-summary_implementation_plan.md"
    (repo_root / "web").mkdir(parents=True, exist_ok=True)
    (task_dir / "contracts").mkdir(parents=True, exist_ok=True)
    impl_path.parent.mkdir(parents=True, exist_ok=True)

    impl_path.write_text(
        """```yaml
planning_contract:
  execution_mode: serial
  card_order: [C01, G01]
  gate_contract:
    mode: as_cards
    gate_ids: [G01]
    depends_on:
      G01: [C01]
```\n""",
        encoding="utf-8",
    )

    vk_cards_path = task_dir / "contracts" / "vk_cards.json"
    _write_json(
        vk_cards_path,
        {
            "task_key": TASK_KEY,
            "task_split_dir": TASK_SPLIT_DIR,
            "plan_title": "parallel-plan-summary 串行卡片包",
            "generated_at": "2026-03-08",
            "execution_mode": "serial",
            "single_active_card": True,
            "auto_done_policy": {
                "implementation-card": "hard_gate",
                "inspection-card": "policy_gate",
            },
            "execution_contract": {
                "delivery_mode": "staged",
                "execution_unit": "per_task",
                "commit_policy": "per_pr",
                "stop_boundary": "per_task",
                "stop_on_blocked": True,
            },
            "gate_contract": {
                "mode": "as_cards",
                "gate_ids": ["G01"],
                "depends_on": {"G01": ["C01"]},
            },
            "card_order": ["C01", "G01"],
            "preflight": {
                "card_id": "C00",
                "feature_ids": ["C00-PREFLIGHT"],
                "required_done_gate": ["scope ok"],
                "source_ws_file": f"workdocs/任务拆解/{TASK_SPLIT_DIR}/workstreams/WS-00.md",
            },
            "source_files": {
                "implementation_plan": str(impl_path.relative_to(repo_root)),
                "parallel_plan": f"workdocs/任务拆解/{TASK_SPLIT_DIR}/parallel_plan.md",
                "workstreams": [
                    f"workdocs/任务拆解/{TASK_SPLIT_DIR}/workstreams/WS-C01.md",
                    f"workdocs/任务拆解/{TASK_SPLIT_DIR}/workstreams/WS-G01.md",
                ],
            },
            "mapping_checks": {
                "plan_consumption_check": "PASS",
                "missing_feature_ids": [],
                "missing_task_ids": [],
                "execution_contract_mismatch": [],
                "acceptance_mapping_missing": [],
            },
            "cards": [
                {
                    "card_id": "C01",
                    "title": "C01 build summary source",
                    "task_mode": "implementation-card",
                    "depends_on": [],
                    "feature_ids": ["F01"],
                    "task_ids": ["T01"],
                    "acceptance_checks": ["pytest -q tests/unit/test_dummy.py"],
                    "source_ws_file": f"workdocs/任务拆解/{TASK_SPLIT_DIR}/workstreams/WS-C01.md",
                    "pr_id": "PR-01",
                },
                {
                    "card_id": "G01",
                    "title": "G01 gate",
                    "task_mode": "inspection-card",
                    "depends_on": ["C01"],
                    "feature_ids": ["G-01"],
                    "task_ids": ["G01"],
                    "acceptance_checks": ["python3 scripts/check_workflow_contract.py --mode gate_contract --task-split-dir x --output -"],
                    "source_ws_file": f"workdocs/任务拆解/{TASK_SPLIT_DIR}/workstreams/WS-G01.md",
                    "pr_id": "PR-GATE",
                },
            ],
        },
    )

    return repo_root, task_dir, vk_cards_path


def test_backfill_gate_status_writes_vk_cards_and_generates_parallel_plan(monkeypatch, tmp_path):
    module = _load_module()
    repo_root, task_dir, vk_cards_path = _prepare_fixture(tmp_path)

    def fake_run_command(command: str, cwd: Path | None = None):
        if command.startswith("venv/bin/python -m pytest"):
            return module.CommandResult(command=command, return_code=0, stdout="2 passed in 0.12s\n", stderr="")
        if command == "npx tsc --noEmit":
            return module.CommandResult(command=command, return_code=0, stdout="", stderr="")
        if command == "npm run -s lint":
            return module.CommandResult(command=command, return_code=0, stdout="Warning: one lint warning\n", stderr="")
        if command.startswith("venv/bin/python scripts/docs_guard.py --strict --json-out "):
            json_out = Path(command.rsplit(" --json-out ", 1)[1])
            json_out.write_text(json.dumps({"stats": {"errors": 0, "warnings": 1}}), encoding="utf-8")
            return module.CommandResult(command=command, return_code=0, stdout="docs ok\n", stderr="")
        raise AssertionError(f"unexpected command: {command} cwd={cwd}")

    monkeypatch.setattr(module, "run_command", fake_run_command)

    payload = module.run_gate_backfill(
        project_root=repo_root,
        vk_cards_path=vk_cards_path,
        skip_baseline_check=True,
        dry_run=False,
    )

    assert payload["overall_passed"] is True

    updated_vk_cards = json.loads(vk_cards_path.read_text(encoding="utf-8"))
    gate_results = updated_vk_cards["gate_results"]
    assert gate_results["overall_passed"] is True
    assert gate_results["checks"]["pytest"]["status"] == "通过（2 passed）"
    assert gate_results["checks"]["docs_guard"]["warnings"] == 1

    parallel_plan_path = task_dir / "parallel_plan.md"
    assert parallel_plan_path.exists()
    parallel_text = parallel_plan_path.read_text(encoding="utf-8")
    assert "自动生成总览" in parallel_text
    assert "pytest" in parallel_text
    assert "通过（2 passed）" in parallel_text
