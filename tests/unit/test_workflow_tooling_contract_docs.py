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
