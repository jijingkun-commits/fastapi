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

