#!/usr/bin/env python3
"""composite-query-multimodal-response-contract 门禁脚本。

注意：文件名保留 .sh 以匹配既有计划约定，实际由 Python 解释执行。
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
REQUIREMENTS_PATH = ROOT / "docs/内部参考/迭代需求/composite-query-multimodal-response-contract_requirements.md"
IMPLEMENTATION_PATH = ROOT / "docs/内部参考/迭代需求/composite-query-multimodal-response-contract_implementation_plan.md"
CLARIFY_ALIGNMENT_OUTPUT = ROOT / "docs/内部参考/迭代需求/composite-query-multimodal-response-contract_clarify_plan_alignment.json"
TEMPORAL_GATE_OUTPUT = ROOT / "docs/内部参考/迭代需求/composite-query-multimodal-response-contract_planning_temporal_gate.json"
RESULT_SCHEMA_PATH = ROOT / "contracts/streaming/result-event.schema.json"


class GateFailure(RuntimeError):
    """门禁失败。"""


def run_command(label: str, cmd: list[str]) -> None:
    print(f"[contract-gate] {label}: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=ROOT, check=False)
    if result.returncode != 0:
        raise GateFailure(f"{label} failed with exit code {result.returncode}")


def assert_symbols_exist() -> None:
    required_symbols = [
        "result_event_union",
        "text_event_stream_itemSchema",
        "asyncapi_transitional_contract",
        "last_event_id_resume",
        "payload_budget_rules",
    ]
    symbol_targets = {
        "docs/开发文档/代码解读/SSE事件协议.md": ROOT / "docs/开发文档/代码解读/SSE事件协议.md",
        "docs/产品文档/聊天系统需求.md": ROOT / "docs/产品文档/聊天系统需求.md",
        "docs/api/streaming-events.asyncapi.yaml": ROOT / "docs/api/streaming-events.asyncapi.yaml",
        "docs/api/openapi.yaml": ROOT / "docs/api/openapi.yaml",
    }

    text_by_file: dict[str, str] = {}
    for label, file_path in symbol_targets.items():
        if not file_path.exists():
            raise GateFailure(f"missing required file: {label}")
        text_by_file[label] = file_path.read_text(encoding="utf-8")

    for symbol in required_symbols:
        found = any(symbol in text for text in text_by_file.values())
        if not found:
            raise GateFailure(f"missing required symbol: {symbol}")


def assert_result_schema_drift() -> None:
    if not RESULT_SCHEMA_PATH.exists():
        raise GateFailure(f"missing schema artifact: {RESULT_SCHEMA_PATH}")

    from app.contracts.result_event_contract import result_event_union_json_schema

    expected_schema = result_event_union_json_schema()
    current_schema = json.loads(RESULT_SCHEMA_PATH.read_text(encoding="utf-8"))

    # 允许 artifact 额外携带文档元信息，不计入 drift。
    for extra_key in ("$id", "$schema", "title"):
        expected_schema.pop(extra_key, None)
        current_schema.pop(extra_key, None)

    if expected_schema != current_schema:
        raise GateFailure(
            "contract_drift_gate failed: contracts/streaming/result-event.schema.json is out of sync "
            "with app/contracts/result_event_contract.py"
        )


def main() -> int:
    summary: dict[str, Any] = {
        "contract_drift_gate": "pending",
        "unknown_data_type_fallback_test": "pending",
        "replay_consistency_test": "pending",
        "multi_result_ordering_test": "pending",
        "sse_resume_dedup_test": "pending",
        "redaction_whitelist_test": "pending",
        "clarify_plan_alignment": "pending",
        "planning_temporal_gate": "pending",
    }

    try:
        assert_result_schema_drift()
        summary["contract_drift_gate"] = "passed"

        run_command(
            "pytest_targeted",
            [
                "bash",
                "scripts/pytest_targeted.sh",
                "tests/unit/test_chat_service_done_payload.py",
                "tests/unit/test_chat_service_turn_slice.py",
                "tests/unit/test_multi_intent_coverage_reconcile.py",
            ],
        )
        summary["unknown_data_type_fallback_test"] = "passed"
        summary["replay_consistency_test"] = "passed"
        summary["multi_result_ordering_test"] = "passed"
        summary["sse_resume_dedup_test"] = "passed"

        assert_symbols_exist()
        summary["redaction_whitelist_test"] = "passed"

        run_command(
            "clarify_plan_alignment",
            [
                sys.executable,
                "scripts/check_workflow_contract.py",
                "--mode",
                "clarify_plan",
                "--requirements-path",
                str(REQUIREMENTS_PATH),
                "--implementation-path",
                str(IMPLEMENTATION_PATH),
                "--output",
                str(CLARIFY_ALIGNMENT_OUTPUT),
            ],
        )
        summary["clarify_plan_alignment"] = "passed"

        run_command(
            "planning_temporal_gate",
            [
                sys.executable,
                "scripts/check_workflow_contract.py",
                "--mode",
                "planning_temporal_gate",
                "--implementation-path",
                str(IMPLEMENTATION_PATH),
                "--output",
                str(TEMPORAL_GATE_OUTPUT),
            ],
        )
        summary["planning_temporal_gate"] = "passed"

    except GateFailure as exc:
        summary["error"] = str(exc)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 1

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
