"""workflow contract 时间窗与规划门禁回归测试。"""

from __future__ import annotations

import json
import sys
import uuid
from datetime import datetime, timezone
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


SCRIPT_PATH = Path("scripts/check_workflow_contract.py")


def _load_module():
    module_name = f"check_workflow_contract_test_{uuid.uuid4().hex}"
    spec = spec_from_file_location(module_name, SCRIPT_PATH)
    assert spec and spec.loader
    module = module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def test_retirement_guard_does_not_block_on_window_maturity():
    module = _load_module()

    payload = module.retirement_guard(
        wrapper_report={"ok": True, "entries": []},
        usage_report={
            "ok": True,
            "summary": {"legacy_calls": 0},
            "events": [
                {"recorded_at": "2026-03-06T19:58:13Z", "legacy_entry": False},
            ],
        },
        ttl_report={"ok": True, "summary": {"active_truth_source_harmed": 0}},
    )

    assert payload["ok"] is True
    assert payload["blockers"] == []


def test_retirement_guard_still_blocks_on_legacy_usage():
    module = _load_module()

    payload = module.retirement_guard(
        wrapper_report={"ok": True, "entries": []},
        usage_report={
            "ok": True,
            "summary": {"legacy_calls": 2},
            "events": [
                {"recorded_at": "2026-03-06T19:58:13Z", "legacy_entry": True},
            ],
        },
        ttl_report={"ok": True, "summary": {"active_truth_source_harmed": 0}},
    )

    assert payload["ok"] is False
    assert any(item["code"] == "LEGACY_USAGE_DETECTED" for item in payload["blockers"])


def test_temporal_gate_contract_detects_window_blockers(tmp_path):
    module = _load_module()
    repo_root = tmp_path / "repo"
    task_dir = repo_root / "docs" / "内部参考" / "任务拆解" / "2026-03-07_temporal-gate"
    impl_path = repo_root / "docs" / "内部参考" / "迭代需求" / "temporal_gate_implementation_plan.md"
    task_dir.mkdir(parents=True, exist_ok=True)
    impl_path.parent.mkdir(parents=True, exist_ok=True)

    (task_dir / "parallel_plan.md").write_text("done_gate: 删除前连续7天零调用\n", encoding="utf-8")
    impl_path.write_text("acceptance_gates:\n  - 删除前连续7天零调用\n", encoding="utf-8")
    (task_dir / "vk_cards.json").write_text(
        json.dumps(
            {
                "source_files": {"implementation_plan": str(impl_path.relative_to(repo_root))},
                "cards": [
                    {
                        "card_id": "C07",
                        "acceptance_checks": ["python3 scripts/check_workflow_contract.py --mode usage-report --window-days 7 --log-path logs/workflow-gate-usage.jsonl --report-output docs/内部参考/任务拆解/2026-03-06_工程减法治理/evidence/workflow-gate-usage-report.json"],
                        "done_gate": ["支持7天零调用聚合判定"],
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    payload = module.check_temporal_gate_contract(task_dir, repo_root)

    assert payload["ok"] is False
    assert any(item["code"] == "TEMPORAL_GATE_BLOCKER_DETECTED" for item in payload["errors"])


def test_plan_db_evidence_contract_detects_missing_db_evidence(tmp_path):
    module = _load_module()
    implementation_path = tmp_path / "demo_implementation_plan.md"
    implementation_path.write_text(
        """
```yaml
implementation_tasks:
  - task_id: T-01
    risk_tags:
      - chat_db
    mandatory_evidence:
      - unit
    acceptance_cmds:
      - kind: unit
        cmd: bash scripts/pytest_targeted.sh tests/unit/test_dummy.py -q
implementation_readiness:
  implementation_ready: true
```
""".strip()
        + "\n",
        encoding="utf-8",
    )

    payload = module._validate_plan_db_evidence_contract(implementation_path)

    assert payload["ok"] is False
    assert any(item["code"] == "PLAN_DB_EVIDENCE_MISSING" for item in payload["errors"])


def test_plan_db_evidence_contract_detects_invalid_acceptance_kind(tmp_path):
    module = _load_module()
    implementation_path = tmp_path / "demo_kind_implementation_plan.md"
    implementation_path.write_text(
        """
```yaml
implementation_tasks:
  - task_id: T-02
    risk_tags:
      - data_db
    mandatory_evidence:
      - data_db_route_sql_result
    acceptance_cmds:
      - cmd: bash scripts/pytest_targeted.sh tests/unit/test_dummy.py -q
implementation_readiness:
  implementation_ready: true
```
""".strip()
        + "\n",
        encoding="utf-8",
    )

    payload = module._validate_plan_db_evidence_contract(implementation_path)

    assert payload["ok"] is False
    assert any(item["code"] == "PLAN_EVIDENCE_KIND_INVALID" for item in payload["errors"])


def test_vkplan_db_evidence_contract_detects_mapping_gap_and_split_unclosed(tmp_path):
    module = _load_module()
    repo_root = tmp_path / "repo"
    implementation_path = repo_root / "docs" / "内部参考" / "迭代需求" / "demo_implementation_plan.md"
    task_split_dir = repo_root / "docs" / "内部参考" / "任务拆解" / "2026-03-08_demo"
    implementation_path.parent.mkdir(parents=True, exist_ok=True)
    task_split_dir.mkdir(parents=True, exist_ok=True)

    implementation_path.write_text(
        """
```yaml
implementation_tasks:
  - task_id: T-03
    risk_tags:
      - chat_db
    mandatory_evidence:
      - chat_db_write_read
    acceptance_cmds:
      - kind: chat_db
        cmd: bash scripts/pytest_targeted.sh tests/unit/test_dummy.py -q
implementation_readiness:
  implementation_ready: true
```
""".strip()
        + "\n",
        encoding="utf-8",
    )

    (task_split_dir / "vk_cards.json").write_text(
        json.dumps(
            {
                "execution_mode": "serial",
                "card_order": ["C01", "C02"],
                "cards": [
                    {
                        "card_id": "C01",
                        "task_ids": ["T-03"],
                        "risk_tags": [],
                        "mandatory_evidence": [],
                        "cross_card_closure": {"required": False, "closure_owner": None},
                    },
                    {
                        "card_id": "C02",
                        "task_ids": ["T-03"],
                        "risk_tags": [],
                        "mandatory_evidence": [],
                        "cross_card_closure": {"required": False, "closure_owner": None},
                    },
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    payload = module._validate_vkplan_db_evidence_contract(
        repo_root=repo_root,
        task_split_dir=task_split_dir,
        implementation_path=implementation_path,
    )

    assert payload["ok"] is False
    assert any(item["code"] == "VKPLAN_EVIDENCE_MAPPING_BROKEN" for item in payload["errors"])
    assert any(item["code"] == "VKPLAN_DB_CHAIN_SPLIT_UNCLOSED" for item in payload["errors"])
