"""Agent 写法治理文档/规则/模板合同回归测试。"""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

REQUIRED_MARKERS = {
    "AGENTS.md": [
        "app/ai/AGENTS.md",
        ".cursor/rules/agent_authoring.mdc",
    ],
    "app/ai/AGENTS.md": [
        "simple-first",
        "contract-first",
        "single semantic decider",
        "keyword_primary_routing",
    ],
    ".cursor/rules/agent_authoring.mdc": [
        "multi_decider_stack",
        "keyword_primary_routing",
        "dual_truth_design",
        "speculative_fallback",
        "missing_eval_evidence",
    ],
    "docs/README.md": [
        "app/ai/AGENTS.md",
        "agent authoring",
    ],
    "docs/开发文档/规范/多智能体开发规范.md": [
        "keyword_primary_routing",
        "multi_decider_stack",
        "AI模块设计.md",
    ],
    ".cursor/commands/jjk-review.md": [
        "agent_authoring_review",
        "multi_decider_stack",
        "keyword_primary_routing",
        "missing_eval_evidence",
    ],
    ".cursor/commands/jjk-verify.md": [
        "agent_governance_result",
        "real_task_eval_verified",
        "missing_eval_evidence",
    ],
    "workdocs/_templates/jjk_review_templates.md": [
        "agent_authoring_review",
        "multi_decider_stack",
        "keyword_primary_routing",
        "missing_eval_evidence",
    ],
    "workdocs/_templates/jjk_verify_templates.md": [
        "agent_governance_result",
        "real_task_eval_verified",
        "missing_eval_evidence",
    ],
    "workdocs/任务拆解/2026-03-13_codex-agent-governance-phase1/reports/agent_governance_real_task_eval.md": [
        "EC-01",
        "EC-05",
        "multi_decider_stack",
        "keyword_primary_routing",
        "missing_eval_evidence",
        "manual_eval_verdict",
    ],
    ".github/workflows/agent-governance-gate.yml": [
        "test_agent_governance_contract_docs.py",
        ".cursor/rules/agent_authoring.mdc",
        "app/ai/AGENTS.md",
    ],
}


def test_agent_governance_contract_markers_present() -> None:
    missing: list[str] = []

    for relative_path, markers in REQUIRED_MARKERS.items():
        path = ROOT / relative_path
        if not path.exists():
            missing.append(f"{relative_path}::MISSING_FILE")
            continue

        text = path.read_text(encoding="utf-8")
        for marker in markers:
            if marker not in text:
                missing.append(f"{relative_path}::{marker}")

    assert not missing, (
        "Agent 治理合同标记缺失，请同步补齐规则入口、专项规则、review/verify 模板和 workflow gate。"
        f"\n缺失项: {missing}"
    )
