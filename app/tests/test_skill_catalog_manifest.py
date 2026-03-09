"""Progressive Skill catalog manifest 专项测试。"""

import asyncio
from contextlib import nullcontext
from types import SimpleNamespace

from langchain_core.messages import HumanMessage

from app.ai.workflow import multi_agent_graph
from app.services.skill_service import SkillService


def test_build_skill_catalog_manifest_uses_definition_version_truth_source(monkeypatch) -> None:
    """catalog manifest 应完全基于 definition/version 真理源构建并稳定排序。"""

    rows = [
        SimpleNamespace(
            skill_id="skill.beta",
            name="Beta Skill",
            description="Beta 描述",
            content="# Beta\n正文",
            catalog_path="beta/path",
            catalog_order=20,
            effective_version="v2",
            when_to_use="用于 beta",
            catalog_description="Beta catalog",
            scope="global",
            binding_status=None,
            is_enabled=True,
            priority=20,
        ),
        SimpleNamespace(
            skill_id="skill.alpha",
            name="Alpha Skill",
            description="Alpha 描述",
            content="# Alpha\n正文",
            catalog_path="alpha/path",
            catalog_order=10,
            effective_version="v1",
            when_to_use="用于 alpha",
            catalog_description="Alpha catalog",
            scope="global",
            binding_status=None,
            is_enabled=True,
            priority=10,
        ),
    ]

    monkeypatch.setattr("app.services.skill_service.get_db_context", lambda: nullcontext(object()))
    monkeypatch.setattr(
        SkillService,
        "_list_definition_runtime_rows",
        classmethod(lambda cls, db, user_id=None, require_content=True: rows),
    )

    payload = SkillService.build_skill_catalog_manifest(user_id=42)

    assert [item["skill_id"] for item in payload["manifest"]] == ["skill.alpha", "skill.beta"]
    assert payload["visible_skill_count"] == 2
    assert payload["catalog_build_source"] == SkillService.SKILL_CATALOG_SOURCE
    assert payload["catalog_version"]


def test_preprocess_writes_skill_catalog_context_in_progressive_mode(monkeypatch) -> None:
    """preprocess 应写入 skill_catalog_* 会话态而不是旧 skill_context 主路径。"""

    events = []
    monkeypatch.setattr(multi_agent_graph, "get_stream_writer", lambda: events.append)
    monkeypatch.setattr("app.ai.message_utils.validate_messages", lambda messages, fix_reasoning=False: messages)

    class _GuardrailRunner:
        async def validate_input(self, content: str):
            return True, content, None

    monkeypatch.setattr("app.ai.guardrails.guardrail_runner", _GuardrailRunner())
    monkeypatch.setattr(
        SkillService,
        "resolve_runtime_mode",
        classmethod(lambda cls: cls.SKILL_RUNTIME_MODE_PROGRESSIVE),
    )
    monkeypatch.setattr(
        SkillService,
        "build_skill_catalog_manifest",
        classmethod(
            lambda cls, user_id=None: {
                "manifest": [
                    {
                        "skill_id": "sql.query.author",
                        "display_name": "SQL Author",
                        "description": "编写 SQL",
                        "effective_version": "v2026.03.07",
                        "when_to_use": "当你需要 SQL 查询时",
                        "catalog_path": "sql/query/author",
                        "catalog_order": 10,
                    }
                ],
                "catalog_version": "cat-001",
                "visible_skill_count": 1,
                "catalog_build_source": SkillService.SKILL_CATALOG_SOURCE,
            }
        ),
    )
    monkeypatch.setattr(
        SkillService,
        "format_skill_catalog_as_context_with_meta",
        classmethod(
            lambda cls, manifest, max_length=2400: (
                "以下是当前可见技能目录：\n- sql/query/author | SQL Author | v2026.03.07 | 当你需要 SQL 查询时",
                {
                    "budget_chars": 2400,
                    "used_chars": 72,
                    "truncated": False,
                    "included_skill_ids": ["sql.query.author"],
                    "excluded_skill_ids": [],
                    "visible_skill_count": 1,
                },
            )
        ),
    )

    updates = asyncio.run(
        multi_agent_graph._preprocess_multimodal(
            {
                "messages": [HumanMessage(content="帮我统计贷款余额")],
                "enable_thinking": False,
                "user_id": 42,
            }
        )
    )

    assert updates["skill_catalog_manifest"][0]["skill_id"] == "sql.query.author"
    assert updates["skill_catalog_context"].startswith("以下是当前可见技能目录")
    assert updates["catalog_version"] == "cat-001"
    assert updates["visible_skill_count"] == 1
    assert updates["skill_context"] is None
    assert updates["skill_injection_meta"]["runtime_mode"] == SkillService.SKILL_RUNTIME_MODE_PROGRESSIVE
    assert any(event.get("type") == "status" for event in events)



def test_build_skill_catalog_manifest_carries_tool_contract(monkeypatch) -> None:
    """catalog manifest 应携带 version 级 tool_contract，供 runtime 统一消费。"""

    rows = [
        SimpleNamespace(
            skill_id="knowledge-search",
            name="Knowledge Search",
            description="知识检索",
            content="# Knowledge Search\n正文",
            catalog_path="knowledge/search",
            catalog_order=10,
            effective_version="v1",
            when_to_use="当你需要查询知识库时",
            catalog_description="知识库检索",
            tool_contract={
                "required_tools": ["knowledge_search"],
                "optional_tools": [],
                "tool_groups": ["knowledge"],
                "expose_after_load": True,
            },
            scope="global",
            binding_status=None,
            is_enabled=True,
            priority=10,
        )
    ]

    monkeypatch.setattr("app.services.skill_service.get_db_context", lambda: nullcontext(object()))
    monkeypatch.setattr(
        SkillService,
        "_list_definition_runtime_rows",
        classmethod(lambda cls, db, user_id=None, require_content=True: rows),
    )

    payload = SkillService.build_skill_catalog_manifest(user_id=42)

    assert payload["manifest"][0]["tool_contract"]["required_tools"] == ["knowledge_search"]
    assert payload["catalog_version"]
