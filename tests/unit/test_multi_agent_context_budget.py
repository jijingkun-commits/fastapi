"""Supervisor 上下文预算与工具输出压缩测试。"""

from langchain_core.messages import AIMessage, ToolMessage

from app.ai.workflow.multi_agent_graph import (
    SUPERVISOR_CONTEXT_MIN_TOKENS,
    _calculate_supervisor_context_budget,
    _prepare_messages_for_supervisor_inference,
    _truncate_tool_message_text,
)


def test_calculate_supervisor_context_budget_has_floor() -> None:
    """预算计算应有最小值保护，避免极端配置导致上下文为空。"""
    budget = _calculate_supervisor_context_budget(128)
    assert budget == SUPERVISOR_CONTEXT_MIN_TOKENS


def test_calculate_supervisor_context_budget_uses_ratio() -> None:
    """预算计算应按比例裁剪。"""
    budget = _calculate_supervisor_context_budget(4000)
    assert budget == 3400


def test_truncate_tool_message_text_keeps_head_and_tail() -> None:
    """超长工具输出应保留首尾关键信息并添加省略提示。"""
    raw = "A" * 5000
    compacted = _truncate_tool_message_text(
        raw,
        char_limit=1000,
        head_chars=300,
        tail_chars=200,
    )

    assert len(compacted) < len(raw)
    assert compacted.startswith("A" * 300)
    assert compacted.endswith("A" * 200)
    assert "已省略" in compacted


def test_prepare_messages_compacts_only_tool_message() -> None:
    """仅 ToolMessage 参与压缩，普通消息保持原对象引用。"""
    ai_message = AIMessage(content="正常回复", id="ai-msg-1")
    tool_message = ToolMessage(
        content="B" * 5000,
        tool_call_id="tool-1",
        name="knowledge_search",
        id="tool-msg-1",
    )

    prepared = _prepare_messages_for_supervisor_inference([ai_message, tool_message])

    assert prepared[0] is ai_message
    assert prepared[1] is not tool_message
    assert prepared[1].tool_call_id == tool_message.tool_call_id
    assert prepared[1].name == tool_message.name
    assert prepared[1].id == tool_message.id
    assert "已省略" in str(prepared[1].content)


def test_prepare_messages_keeps_short_tool_message() -> None:
    """短工具结果不应被无谓改写。"""
    tool_message = ToolMessage(content="短结果", tool_call_id="tool-2", name="search")
    prepared = _prepare_messages_for_supervisor_inference([tool_message])
    assert prepared[0] is tool_message
