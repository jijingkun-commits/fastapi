"""workflow-gate usage report 契约回归测试。"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


SCRIPT_PATH = Path("scripts/check_workflow_contract.py")
TASK_SPLIT_DIR = Path("docs/内部参考/任务拆解/2026-03-06_工程减法治理")
WS_C05_PATH = TASK_SPLIT_DIR / "workstreams" / "WS-C05_P2_旧入口调用观测.md"
VK_CARDS_PATH = TASK_SPLIT_DIR / "vk_cards.json"
REPORT_PATH = "docs/内部参考/任务拆解/2026-03-06_工程减法治理/evidence/workflow-gate-usage-report.json"
RUNTIME_LOG = "logs/workflow-gate-usage.jsonl"
EXPECTED_CMD_FRAGMENT = (
    "scripts/check_workflow_contract.py --mode usage-report "
    "--log-path logs/workflow-gate-usage.jsonl "
    "--report-output docs/内部参考/任务拆解/2026-03-06_工程减法治理/evidence/workflow-gate-usage-report.json"
)



def test_c05_contract_uses_tracked_usage_report_artifact():
    ws_text = WS_C05_PATH.read_text(encoding="utf-8")
    vk_cards = json.loads(VK_CARDS_PATH.read_text(encoding="utf-8"))
    c05_card = next(card for card in vk_cards["cards"] if str(card.get("card_id")).upper() == "C05")

    assert EXPECTED_CMD_FRAGMENT in ws_text
    assert REPORT_PATH in ws_text
    assert RUNTIME_LOG not in c05_card["file_scope"]
    assert REPORT_PATH in c05_card["file_scope"]
    assert EXPECTED_CMD_FRAGMENT in c05_card["acceptance_checks"][0]



def test_usage_report_can_export_tracked_report_file(tmp_path: Path):
    log_path = tmp_path / "logs" / "workflow-gate-usage.jsonl"
    report_path = tmp_path / "evidence" / "workflow-gate-usage-report.json"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(
        json.dumps(
            {
                "record_type": "usage_event",
                "recorded_at": "2026-03-08T00:00:00Z",
                "mode": "clarify_plan",
                "caller": "legacy:test",
                "legacy_entry": True,
                "ok": True,
                "exit_code": 0,
                "log_path": str(log_path),
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--mode",
            "usage-report",
            "--window-days",
            "7",
            "--log-path",
            str(log_path),
            "--report-output",
            str(report_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert report_path.exists()
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["summary"]["legacy_calls"] == 1
    assert payload["summary"]["total_calls"] == 1
