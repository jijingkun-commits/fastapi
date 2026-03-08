"""gate_contract 校验在 parallel_plan 缺失时的兼容回归测试。"""

from __future__ import annotations

import json
import sys
import uuid
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


SCRIPT_PATH = Path("scripts/workflow_contract_gate_contract_impl.py")


def _load_module():
    module_name = f"workflow_contract_gate_contract_impl_test_{uuid.uuid4().hex}"
    spec = spec_from_file_location(module_name, SCRIPT_PATH)
    assert spec and spec.loader
    module = module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_gate_contract_allows_missing_parallel_plan(tmp_path):
    module = _load_module()
    repo_root = tmp_path / "repo"
    task_dir = repo_root / "docs" / "内部参考" / "任务拆解" / "2026-03-08_gate-contract-no-parallel"
    impl_path = repo_root / "docs" / "内部参考" / "迭代需求" / "gate_contract_no_parallel_implementation_plan.md"
    task_dir.mkdir(parents=True, exist_ok=True)
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

    _write_json(
        task_dir / "vk_cards.json",
        {
            "task_key": "PP-20260308-GATE-CONTRACT",
            "execution_mode": "serial",
            "card_order": ["C01", "G01"],
            "gate_contract": {
                "mode": "as_cards",
                "gate_ids": ["G01"],
                "depends_on": {"G01": ["C01"]},
            },
            "source_files": {
                "implementation_plan": str(impl_path.relative_to(repo_root)),
            },
            "cards": [
                {"card_id": "C01"},
                {"card_id": "G01"},
            ],
        },
    )

    result = module.run_check(task_dir, repo_root)

    assert result["ok"] is True
    assert result["files"]["parallel_plan"] is None
    assert result["contracts"]["parallel_plan"] is None
