"""Handoff 检测回归测试（中文注释）。

覆盖场景：
- Supervisor 调用 assign_to_* 工具后，模型可能继续输出一条 AIMessage。
  此时 ToolMessage 不一定是最后一条消息，仍必须能识别 handoff 并路由到专家。
"""

import sys
from pathlib import Path

import pytest
from langchain_core.messages import AIMessage, ToolMessage


# 添加项目根目录到 path（与 app/tests 其他用例保持一致）
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def test_extract_latest_handoff_from_messages_tool_message_not_last():
    """ToolMessage 不在最后一条时仍能提取 handoff。"""
    from app.ai.protocol import AgentOutputParser, HandoffResult

    handoff_json = HandoffResult(
        target_agent="data_expert",
        task_description="查询2025年6月30日的贷款余额",
    ).model_dump_json(ensure_ascii=False)

    delta_messages = [
        ToolMessage(content=handoff_json, tool_call_id="1"),
        AIMessage(content="我需要查询2025年6月30日的贷款余额数据，这属于业务数据查询任务"),
    ]

    handoff = AgentOutputParser.extract_latest_handoff_from_messages(delta_messages)
    assert handoff is not None
    assert handoff["action"] == "handoff"
    assert handoff["target_agent"] == "data_expert"
    assert "贷款余额" in handoff["task_description"]


def test_extract_latest_handoff_from_messages_returns_none_when_missing():
    """没有 ToolMessage 或没有 handoff 协议时返回 None。"""
    from app.ai.protocol import AgentOutputParser

    delta_messages = [AIMessage(content="只是普通回复，没有工具调用")]
    assert AgentOutputParser.extract_latest_handoff_from_messages(delta_messages) is None


def test_extract_all_handoffs_from_messages_preserves_order():
    """应按 ToolMessage 出现顺序返回全部 handoff。"""
    from app.ai.protocol import AgentOutputParser, HandoffResult

    data_handoff = HandoffResult(
        target_agent="data_expert",
        task_description="先查询嘉兴天气并补充到分析上下文",
    ).model_dump_json(ensure_ascii=False)
    todo_handoff = HandoffResult(
        target_agent="todo_expert",
        task_description="创建待办：跟进网银功能评审",
    ).model_dump_json(ensure_ascii=False)

    delta_messages = [
        ToolMessage(content=data_handoff, tool_call_id="1"),
        ToolMessage(content=todo_handoff, tool_call_id="2"),
        AIMessage(content="两个委派都已生成"),
    ]

    handoffs = AgentOutputParser.extract_all_handoffs_from_messages(delta_messages)
    assert [item["target_agent"] for item in handoffs] == ["data_expert", "todo_expert"]
    assert "嘉兴天气" in handoffs[0]["task_description"]
    assert "网银功能评审" in handoffs[1]["task_description"]


def test_augment_data_handoff_payload_should_use_user_raw_question():
    """data handoff 规范化应保留用户原始问题并避免过度推断。"""
    from app.ai.state import AgentType
    from app.ai.workflow.multi_agent_graph import _augment_data_handoff_payload
    from langchain_core.messages import HumanMessage

    handoff = {
        "action": "handoff",
        "target_agent": AgentType.DATA,
        "task_description": "请执行复杂口径确认后再输出。",
        "frame": None,
        "turn_act_hint": "",
    }
    state = {
        "messages": [HumanMessage(content="查询2025年6月30日贷款余额前10名的客户")],
    }

    normalized = _augment_data_handoff_payload(handoff, state)

    assert normalized["task_description"] == "用户原始问题：查询2025年6月30日贷款余额前10名的客户"
    assert normalized["turn_act_hint"] == "NEW_QUERY"
    assert normalized.get("frame") is None




def test_augment_data_handoff_payload_should_preserve_specific_task_for_mixed_query():
    """当 Supervisor 已生成精确 data 任务时，不应被复合原问题覆盖掉。"""
    from app.ai.state import AgentType
    from app.ai.workflow.multi_agent_graph import _augment_data_handoff_payload
    from langchain_core.messages import HumanMessage

    handoff = {
        "action": "handoff",
        "target_agent": AgentType.DATA,
        "task_description": "查看2025-06-30时点贷款余额前10名的客户，按贷款余额降序返回Top10。",
        "frame": None,
        "turn_act_hint": "",
    }
    state = {
        "messages": [HumanMessage(content="查询嘉兴近一周的天气，再看看2025年6月30日贷款余额前10名的客户")],
    }

    normalized = _augment_data_handoff_payload(handoff, state)

    assert "嘉兴" not in normalized["task_description"]
    assert "贷款余额前10名" in normalized["task_description"]
    assert normalized["turn_act_hint"] == "NEW_QUERY"

def test_augment_data_handoff_payload_should_keep_existing_frame():
    """已有结构化 frame 时应保持透传，仅补齐描述与 turn_act。"""
    from app.ai.state import AgentType
    from app.ai.workflow.multi_agent_graph import _augment_data_handoff_payload
    from langchain_core.messages import HumanMessage

    handoff = {
        "action": "handoff",
        "target_agent": AgentType.DATA,
        "task_description": "请按模型建议处理",
        "frame": {"metric": "贷款余额", "time_range": "2025-06-30"},
        "turn_act_hint": "",
    }
    state = {
        "messages": [HumanMessage(content="查询2025年6月30日贷款余额")],
    }

    normalized = _augment_data_handoff_payload(handoff, state)

    assert normalized["frame"] == {"metric": "贷款余额", "time_range": "2025-06-30"}
    assert normalized["turn_act_hint"] == "NEW_QUERY"
    assert normalized["task_description"] == "用户原始问题：查询2025年6月30日贷款余额"
