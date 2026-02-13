"""SkillService 单元测试（中文注释）。"""

from pathlib import Path

from app.services.skill_service import SkillService


def test_parse_skill_file_with_metadata(tmp_path: Path) -> None:
    """应正确解析 SKILL frontmatter 元数据。"""

    skill_dir = tmp_path / "sql-expert"
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(
        """---
name: SQL Expert
description: SQL 检索与优化
scope: data
priority: 10
auto_enabled: true
is_enabled: false
trigger_phrases: ["贷款余额", "分行统计"]
conflicts_with: ["copywriter"]
---

# SQL Expert

这是技能正文。
""",
        encoding="utf-8",
    )

    parsed = SkillService._parse_skill_file(skill_file)

    assert parsed is not None
    assert parsed["skill_id"] == "sql-expert"
    assert parsed["name"] == "SQL Expert"
    assert parsed["scope"] == "data"
    assert parsed["priority"] == 10
    assert parsed["auto_enabled"] is True
    assert parsed["is_enabled"] is False
    assert parsed["trigger_phrases"] == ["贷款余额", "分行统计"]
    assert parsed["conflicts_with"] == ["copywriter"]


def test_pick_sections_prefers_query_relevant_content() -> None:
    """应优先选择与查询关键词相关的章节。"""

    content = """# 概览
通用介绍。

# 贷款分析
分行贷款余额趋势统计方法。

# 附录
附加说明。
"""

    sections = SkillService._pick_sections(content, query="按分行统计贷款余额", max_sections=1)

    assert len(sections) == 1
    assert sections[0][0] == "贷款分析"


def test_apply_policy_filters_resolves_conflicts_by_priority() -> None:
    """冲突技能应按优先级保留。"""

    candidates = [
        {
            "skill_id": "safe-review",
            "priority": 10,
            "final_score": 0.62,
            "trigger_hit": 0.0,
            "is_enabled": True,
            "auto_enabled": True,
            "scope": "global",
            "conflicts_with": ["general-review"],
        },
        {
            "skill_id": "general-review",
            "priority": 100,
            "final_score": 0.95,
            "trigger_hit": 0.0,
            "is_enabled": True,
            "auto_enabled": True,
            "scope": "global",
            "conflicts_with": [],
        },
    ]

    selected, dropped = SkillService._apply_policy_filters(
        candidates,
        top_k=2,
        threshold=0.3,
        scope="global",
        auto_only=True,
    )

    assert [item["skill_id"] for item in selected] == ["safe-review"]
    assert dropped[0]["skill_id"] == "general-review"
    assert dropped[0]["reason"] == "conflict_replaced"
