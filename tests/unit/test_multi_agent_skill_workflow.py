"""多智能体预处理节点的技能检索状态测试。"""

import asyncio

from langchain_core.messages import HumanMessage

from app.ai.workflow import multi_agent_graph
from app.services.skill_service import SkillService


def test_preprocess_writes_skill_retrieval_fields(monkeypatch) -> None:  # noqa: ANN001
    """预处理节点应写入技能候选、入选与注入元信息。"""

    events = []
    captured = {}
    monkeypatch.setattr(multi_agent_graph, "get_stream_writer", lambda: events.append)
    monkeypatch.setattr("app.ai.message_utils.validate_messages", lambda messages, fix_reasoning=False: messages)

    class _GuardrailRunner:
        async def validate_input(self, content: str):
            return True, content, None

    monkeypatch.setattr("app.ai.guardrails.guardrail_runner", _GuardrailRunner())
    monkeypatch.setattr(
        SkillService,
        "resolve_runtime_mode",
        classmethod(lambda cls: cls.SKILL_RUNTIME_MODE_HYBRID),
    )

    def _fake_search_debug(  # noqa: ANN001
        cls,
        query: str,
        top_k: int = 5,
        threshold: float = None,
        scope: str = "global",
        auto_only: bool = False,
        thread_id=None,
        trace_id=None,
        user_id=None,
    ):
        captured["user_id"] = user_id
        return {
            "query": query,
            "mode": "hybrid",
            "scope": scope,
            "skill_candidates": [
                {
                    "skill_id": "data-loan",
                    "final_score": 0.92,
                    "vector_score": 0.9,
                    "lexical_score": 0.8,
                    "trigger_hit": 1.0,
                    "selected": True,
                    "drop_reasons": [],
                }
            ],
            "selected_skill_ids": ["data-loan"],
            "context_preview": "### 贷款分析技能 · 概要\n按分行统计贷款余额。\n",
            "skill_injection_meta": {
                "budget_chars": 2400,
                "used_chars": 30,
                "truncated": False,
                "included_skill_ids": ["data-loan"],
                "excluded_skill_ids": [],
                "sections_used": 1,
                "selected_count": 1,
            },
        }

    monkeypatch.setattr(SkillService, "search_skills_debug", classmethod(_fake_search_debug))

    updates = asyncio.run(
        multi_agent_graph._preprocess_multimodal(
            {
                "messages": [HumanMessage(content="按分行统计贷款余额")],
                "enable_thinking": False,
                "user_id": 42,
            }
        )
    )

    assert updates["selected_skill_ids"] == ["data-loan"]
    assert updates["skill_context"]
    assert updates["skill_injection_meta"]["selected_count"] == 1
    assert updates["skill_candidates"][0]["skill_id"] == "data-loan"
    assert captured["user_id"] == 42
    assert any(event.get("type") == "status" for event in events)


def test_preprocess_should_render_response_guidance_contract_into_system_context(monkeypatch) -> None:  # noqa: ANN001
    """预处理节点应将结构化 response guidance contract 渲染进 system_context。"""

    monkeypatch.setattr(multi_agent_graph, "get_stream_writer", lambda: (lambda _event: None))
    monkeypatch.setattr("app.ai.message_utils.validate_messages", lambda messages, fix_reasoning=False: messages)

    class _GuardrailRunner:
        async def validate_input(self, content: str):
            return True, content, None

    monkeypatch.setattr("app.ai.guardrails.guardrail_runner", _GuardrailRunner())
    monkeypatch.setattr(
        SkillService,
        "resolve_runtime_mode",
        classmethod(lambda cls: cls.SKILL_RUNTIME_MODE_HYBRID),
    )
    monkeypatch.setattr(
        SkillService,
        "search_skills_debug",
        classmethod(lambda cls, query, **kwargs: {
            "query": query,
            "mode": "hybrid",
            "scope": kwargs.get("scope", "global"),
            "skill_candidates": [],
            "selected_skill_ids": [],
            "context_preview": "",
            "skill_injection_meta": {
                "budget_chars": 2400,
                "used_chars": 0,
                "truncated": False,
                "included_skill_ids": [],
                "excluded_skill_ids": [],
                "sections_used": 0,
                "selected_count": 0,
            },
        }),
    )

    updates = asyncio.run(
        multi_agent_graph._preprocess_multimodal(
            {
                "messages": [HumanMessage(content="继续")],
                "enable_thinking": False,
                "response_guidance_contract": {
                    "kind": "memory_archive",
                    "status": "persisted",
                    "target_canonical_text": "用户要求删除已有记忆：用户是纪宇圩的爸爸",
                    "target_slot_key": "user.profile.relationship.parent.of",
                    "followup_behavior": "reuse_resolved_target",
                },
            }
        )
    )

    assert "长期记忆删除已经写入成功" in updates["system_context"]
    assert "user.profile.relationship.parent.of" in updates["system_context"]
    assert "已唯一确认的删除链" in updates["system_context"]


def test_preprocess_fast_lane_prefetches_external_and_compiles_data_handoff(monkeypatch) -> None:  # noqa: ANN001
    """显式双问题应在 preprocess 直接预取外部信息并编译 data handoff。"""

    events = []
    monkeypatch.setattr(multi_agent_graph, "get_stream_writer", lambda: events.append)
    monkeypatch.setattr("app.ai.message_utils.validate_messages", lambda messages, fix_reasoning=False: messages)

    class _GuardrailRunner:
        async def validate_input(self, content: str):
            return True, content, None

    class _FakeSearchTool:
        async def ainvoke(self, payload):
            assert payload == {"query": "2、嘉兴明天的天气怎么样？"}
            return {
                "results": [
                    {
                        "title": "嘉兴天气预报",
                        "content": "嘉兴 明天 多云 2~13℃ 东北风微风",
                    }
                ]
            }

    monkeypatch.setattr("app.ai.guardrails.guardrail_runner", _GuardrailRunner())
    monkeypatch.setattr(
        SkillService,
        "resolve_runtime_mode",
        classmethod(lambda cls: cls.SKILL_RUNTIME_MODE_HYBRID),
    )
    monkeypatch.setattr(
        SkillService,
        "search_skills_debug",
        classmethod(lambda cls, query, **kwargs: {
            "query": query,
            "mode": "hybrid",
            "scope": kwargs.get("scope", "global"),
            "skill_candidates": [],
            "selected_skill_ids": [],
            "context_preview": "",
            "skill_injection_meta": {
                "budget_chars": 2400,
                "used_chars": 0,
                "truncated": False,
                "included_skill_ids": [],
                "excluded_skill_ids": [],
                "sections_used": 0,
                "selected_count": 0,
            },
        }),
    )
    monkeypatch.setattr(
        multi_agent_graph,
        "_resolve_decomposed_goals_for_query",
        lambda user_query, **kwargs: (
            [
                {"goal_id": "GOAL-01", "order": 1, "kind": "data.query", "title": "数据查询", "must_answer": True, "allowed_agents": ["data_expert"]},
                {"goal_id": "GOAL-02", "order": 2, "kind": "external.lookup", "title": "外部信息", "must_answer": True, "allowed_agents": []},
            ],
            "explicit_multi_goal_fast_path",
        ),
    )
    monkeypatch.setattr(
        multi_agent_graph,
        "_build_compiled_data_goal_handoff",
        lambda state, goal: {
            "target_agent": "data_expert",
            "goal_id": goal["goal_id"],
            "task_description": "查询2025年6月30日贷款余额前10名的客户",
            "frame": {"query_text": "查询2025年6月30日贷款余额前10名的客户"},
        },
    )

    import app.ai.tools.chatTools as chat_tools
    monkeypatch.setattr(chat_tools, "search_tool", _FakeSearchTool())

    updates = asyncio.run(
        multi_agent_graph._preprocess_multimodal(
            {
                "messages": [HumanMessage(content="1、查询2025年6月30日贷款余额前10名的客户\n2、嘉兴明天的天气怎么样？")],
                "enable_thinking": False,
                "user_id": 7,
            }
        )
    )

    assert updates["multi_intent_mode"] is True
    assert updates["pending_handoff"]["target_agent"] == "data_expert"
    assert [goal["kind"] for goal in updates["decomposed_goals"]] == ["data.query", "external.lookup"]
    tool_message = updates["messages"][-1]
    assert tool_message.name == "tavily_search"
    assert any(event.get("type") == "plan_ready" for event in events)
    assert any(event.get("type") == "tool_start" for event in events)
    token_event = next(event for event in events if event.get("type") == "token")
    assert "嘉兴" in token_event["data"]["content"]
