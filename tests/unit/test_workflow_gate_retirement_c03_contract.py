"""workflow-gate-retirement C03 契约回归测试。"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


TASK_SPLIT_DIR = Path("workdocs/任务拆解/2026-03-06_工程减法治理")
WS_C03_PATH = TASK_SPLIT_DIR / "workstreams" / "WS-C03_P1_L1旧脚本wrapper兼容壳.md"
VK_CARDS_PATH = TASK_SPLIT_DIR / "contracts" / "vk_cards.json"


def test_c03_contract_closes_file_scope_and_acceptance_command():
    ws_text = WS_C03_PATH.read_text(encoding="utf-8")
    vk_cards = json.loads(VK_CARDS_PATH.read_text(encoding="utf-8"))
    c03_card = next(card for card in vk_cards["cards"] if str(card.get("card_id")).upper() == "C03")

    assert "scripts/check_workflow_contract.py" in ws_text
    assert "legacy_wrapper_compat" in ws_text
    assert "scripts/check_workflow_contract.py" in c03_card["file_scope"]
    assert any(
        "scripts/check_workflow_contract.py --mode legacy_wrapper_compat" in command
        for command in c03_card["acceptance_checks"]
    )


def test_c03_legacy_wrapper_acceptance_command_passes():
    result = subprocess.run(
        [
            sys.executable,
            "scripts/check_workflow_contract.py",
            "--mode",
            "legacy_wrapper_compat",
            "--task-split-dir",
            str(TASK_SPLIT_DIR),
            "--output",
            "-",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert len(payload["checks"]) == 4
