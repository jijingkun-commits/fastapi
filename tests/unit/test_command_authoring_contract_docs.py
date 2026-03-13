"""命令 / Skill 写法防回退合同测试。"""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

REQUIRED_MARKERS = {
    ".cursor/rules/command_authoring.mdc": [
        "命令是提示词，不是门禁表",
        "作者态单入口",
        "运行态单入口",
        "不要为了瘦身删消费锚点",
        "risk_tags",
        "mandatory_evidence",
        "Required Evidence",
        "APPLY_PATCH_TOOL_UNAVAILABLE_FALLBACK",
        "先补一个最小合同测试",
    ],
    "docs/开发文档/流程与工具/指令用法_实现方式_工程流全景手册.md": [
        "命令 / Skill 防回退速查",
        ".cursor/rules/command_authoring.mdc",
        "risk_tags",
        "mandatory_evidence",
        "先补最小合同测试",
    ],
}


def test_command_authoring_contract_markers_present() -> None:
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
        "命令 / Skill 写法防回退标记缺失，请补齐作者态单入口、消费锚点、瘦身边界和最小合同测试说明。"
        f"\n缺失项: {missing}"
    )
