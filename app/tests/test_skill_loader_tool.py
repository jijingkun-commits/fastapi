"""Progressive load_skills 工具专项测试。"""

import json

from langgraph.types import Command

from app.ai.workflow import multi_agent_graph
from app.services.skill_service import SkillService


def test_get_supervisor_tools_registers_load_skills_in_progressive_mode(monkeypatch) -> None:
    """progressive mode 下 Supervisor 必须显式暴露 load_skills 工具。"""

    monkeypatch.setattr(multi_agent_graph, "_get_common_tool_entries", lambda: [])
    monkeypatch.setattr(
        multi_agent_graph,
        "_apply_tool_governance_policy",
        lambda entries, agent_name: [entry["tool"] for entry in entries],
    )
    monkeypatch.setattr(
        SkillService,
        "resolve_runtime_mode",
        classmethod(lambda cls: cls.SKILL_RUNTIME_MODE_PROGRESSIVE),
    )

    tools = multi_agent_graph._get_supervisor_tools()

    assert any(getattr(tool, "name", "") == "load_skills" for tool in tools)


def test_load_skills_tool_updates_registry_and_tool_message(monkeypatch) -> None:
    """load_skills 工具应回写 loaded_skill_registry/context，并携带 canonical skill_runtime。"""

    monkeypatch.setattr(
        SkillService,
        "resolve_runtime_mode",
        classmethod(lambda cls: cls.SKILL_RUNTIME_MODE_PROGRESSIVE),
    )
    monkeypatch.setattr(
        SkillService,
        "load_skills_for_session",
        classmethod(
            lambda cls, **kwargs: {
                "requested_skill_ids": ["sql.query.author"],
                "loaded_skills": [
                    {
                        "skill_id": "sql.query.author",
                        "effective_version": "v2026.03.07",
                        "content": "# SQL Author\n正文",
                        "truncated": False,
                    }
                ],
                "errors": [],
                "truncated_count": 0,
                "loaded_skill_registry": {
                    "sql.query.author": {
                        "skill_id": "sql.query.author",
                        "version": "v2026.03.07",
                        "truncated": False,
                        "source_turn_id": kwargs.get("source_turn_id"),
                    }
                },
                "loaded_skill_context": "以下技能正文已加载到当前会话，可直接复用：\n\n### SQL Author | skill_id=sql.query.author | version=v2026.03.07\n# SQL Author\n正文",
                "catalog_version": "cat-001",
                "visible_skill_count": 1,
                "missing_skills": [],
            }
        ),
    )

    tool = multi_agent_graph._create_load_skills_tool()
    command = tool.func(
        skill_ids=["sql.query.author"],
        reason="需要 SQL 正文",
        state={
            "messages": [],
            "user_id": 7,
            "turn_id": "turn-001",
            "catalog_version": "cat-001",
            "visible_skill_count": 1,
            "skill_catalog_manifest": [{"skill_id": "sql.query.author", "effective_version": "v2026.03.07"}],
        },
        tool_call_id="tc-001",
    )

    assert isinstance(command, Command)
    assert command.update["loaded_skill_registry"]["sql.query.author"]["version"] == "v2026.03.07"
    assert command.update["loaded_skill_context"].startswith("以下技能正文已加载到当前会话")

    message = command.update["messages"][0]
    payload = json.loads(message.content)
    assert payload["requested_skill_ids"] == ["sql.query.author"]
    assert message.name == "load_skills"
    assert message.additional_kwargs["skill_runtime"]["loaded_skills"][0]["skill_id"] == "sql.query.author"
    assert message.additional_kwargs["skill_runtime"]["replay_source"] == "live"
