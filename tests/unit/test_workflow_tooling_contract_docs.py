"""工程流文件编辑工具契约回归测试。"""

from __future__ import annotations

from pathlib import Path


AGENTS_PATH = Path("AGENTS.md")
CLAUDE_PATH = Path("CLAUDE.md")
HANDBOOK_PATH = Path("docs/开发文档/工作流/指令用法_实现方式_工程流全景手册.md")
FALLBACK_MARKER = "APPLY_PATCH_TOOL_UNAVAILABLE_FALLBACK"
APPLY_PATCH_RULE = "禁止通过 `exec_command` 包装 `apply_patch`"


def test_agents_and_claude_define_apply_patch_fallback_contract():
    agents_text = AGENTS_PATH.read_text(encoding="utf-8")
    claude_text = CLAUDE_PATH.read_text(encoding="utf-8")

    assert FALLBACK_MARKER in agents_text
    assert APPLY_PATCH_RULE in agents_text
    assert FALLBACK_MARKER in claude_text
    assert APPLY_PATCH_RULE in claude_text



def test_workflow_handbook_records_same_apply_patch_contract():
    handbook_text = HANDBOOK_PATH.read_text(encoding="utf-8")

    assert "文件编辑工具契约" in handbook_text
    assert FALLBACK_MARKER in handbook_text
    assert APPLY_PATCH_RULE in handbook_text


COMMAND_CONTRACT_MARKERS = {
    ".cursor/commands/jjk-plan.md": [
        "risk_tags",
        "mandatory_evidence",
        "acceptance_cmds[*]",
        "PLAN_DB_EVIDENCE_MISSING",
    ],
    ".cursor/commands/jjk-vkplan.md": [
        "risk_tags",
        "mandatory_evidence",
        "cross_card_closure",
        "VKPLAN_EVIDENCE_MAPPING_BROKEN",
        "VKPLAN_DB_CHAIN_SPLIT_UNCLOSED",
    ],
    ".cursor/commands/jjk-cardrun.md": [
        "acceptance_results",
        "evidence_satisfied",
        "CARDRUN_DB_EVIDENCE_UNSATISFIED",
    ],
    ".cursor/commands/jjk-wtimp.md": [
        "acceptance_results[*]",
        "evidence_satisfied",
        "WTIMP_DB_ASSERTION_MISSING",
        "WTIMP_ANALYTICS_ROUTE_UNVERIFIED",
    ],
    ".cursor/commands/jjk-test.md": [
        "Required Evidence",
        "Actual Evidence",
        "Scripted Flow Status",
        "TEST_DB_CHAIN_INCOMPLETE",
    ],
    ".cursor/commands/jjk-verify.md": [
        "mandatory_evidence",
        "VERIFY_CHAT_DB_UNPROVEN",
        "VERIFY_DATA_DB_UNPROVEN",
    ],
}


def test_workflow_commands_freeze_db_evidence_gate_contract_terms():
    for relative_path, markers in COMMAND_CONTRACT_MARKERS.items():
        text = Path(relative_path).read_text(encoding="utf-8")
        for marker in markers:
            assert marker in text, f"{relative_path} missing marker: {marker}"
