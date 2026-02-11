"""ChatService 轮次切片单元测试。"""

from langchain_core.messages import HumanMessage

from app.ai.utils.message_factory import create_ai_message
from app.services.chat_service import _slice_current_turn_messages


def test_slice_current_turn_messages_returns_only_current_turn_when_id_exists():
    """命中当前 human ID 时，只返回当前轮次消息。"""
    old_human = HumanMessage(content="上一轮", id="human-old")
    old_ai = create_ai_message(
        "上一轮待办列表",
        additional_kwargs={"data_type": "todo_list", "data": {"todos": [1]}}
    )

    current_human = HumanMessage(content="全部完成", id="human-current")
    current_ai = create_ai_message("❌ 请指定待办 ID，或先选中一个待办事项")

    messages = [old_human, old_ai, current_human, current_ai]
    sliced = _slice_current_turn_messages(messages, "human-current")

    assert len(sliced) == 2
    assert sliced[0] is current_human
    assert sliced[1] is current_ai


def test_slice_current_turn_messages_fallback_when_id_not_found():
    """找不到 human ID 时，保留原消息列表（兼容行为）。"""
    m1 = HumanMessage(content="hi", id="human-1")
    m2 = create_ai_message("hello")
    messages = [m1, m2]

    sliced = _slice_current_turn_messages(messages, "missing-id")

    assert sliced == messages

