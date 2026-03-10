"""消息工具契约回归测试。"""

import asyncio

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from app.ai.message_utils import validate_messages
from app.ai.workflow import multi_agent_graph
from app.services.skill_service import SkillService


def test_validate_messages_should_drop_ai_message_with_empty_text_block() -> None:
    """缺少 text 的空壳 assistant block 不应继续留在历史状态里。"""

    messages = [
        HumanMessage(content="上一条用户消息"),
        AIMessage(content=[{"type": "text", "id": "msg_1", "index": -1}]),
        HumanMessage(content="新的用户问题"),
    ]

    validated = validate_messages(messages)

    assert len(validated) == 2
    assert [message.type for message in validated] == ["human", "human"]


def test_validate_messages_should_keep_tool_call_ai_message() -> None:
    """带 tool_calls 的 assistant 消息不能因为空壳文本块被整体丢掉。"""

    ai_message = AIMessage(
        content=[{"type": "text", "id": "msg_1", "index": -1}],
        tool_calls=[{"name": "load_skills", "args": {}, "id": "call_1", "type": "tool_call"}],
    )
    tool_message = ToolMessage(content="{}", tool_call_id="call_1")

    validated = validate_messages([ai_message, tool_message])

    assert len(validated) == 2
    assert validated[0].type == "ai"
    assert validated[0].tool_calls[0]["id"] == "call_1"


def test_preprocess_multimodal_should_strip_malformed_ai_message(monkeypatch) -> None:  # noqa: ANN001
    """预处理节点应在入图前清掉坏 assistant block，避免再次写入 checkpoint。"""

    events = []
    monkeypatch.setattr(multi_agent_graph, "get_stream_writer", lambda: events.append)

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
                "messages": [
                    HumanMessage(content="上一条用户消息"),
                    AIMessage(content=[{"type": "text", "id": "msg_1", "index": -1}]),
                    HumanMessage(content="新的用户问题"),
                ],
                "enable_thinking": False,
                "user_id": 42,
            }
        )
    )

    assert "messages" in updates
    assert [message.type for message in updates["messages"]] == ["human", "human"]
