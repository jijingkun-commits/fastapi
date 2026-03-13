"""Handoff 检测回归测试（中文注释）。

覆盖场景：
- Supervisor 调用 assign_to_* 工具后，模型可能继续输出一条 AIMessage。
  此时 ToolMessage 不一定是最后一条消息，仍必须能识别 handoff 并路由到专家。
"""

from langchain_core.messages import AIMessage, ToolMessage


def test_extract_latest_handoff_from_messages_tool_message_not_last():
    """ToolMessage 不在最后一条时仍能提取 handoff。"""
    from app.ai.protocol import AgentOutputParser, HandoffResult

    handoff_json = HandoffResult(
        target_agent="data_expert",
        frame={"query_text": "查询2025年6月30日的贷款余额"},
    ).model_dump_json(ensure_ascii=False, exclude_none=True)

    delta_messages = [
        ToolMessage(content=handoff_json, tool_call_id="1"),
        AIMessage(content="我需要查询2025年6月30日的贷款余额数据，这属于业务数据查询任务"),
    ]

    handoff = AgentOutputParser.extract_latest_handoff_from_messages(delta_messages)
    assert handoff is not None
    assert handoff["action"] == "handoff"
    assert handoff["target_agent"] == "data_expert"
    assert handoff["frame"]["query_text"] == "查询2025年6月30日的贷款余额"


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
        frame={"query_text": "查询嘉兴天气并补充到分析上下文"},
    ).model_dump_json(ensure_ascii=False, exclude_none=True)
    todo_handoff = HandoffResult(
        target_agent="todo_expert",
        task_description="创建待办：跟进网银功能评审",
    ).model_dump_json(ensure_ascii=False, exclude_none=True)

    delta_messages = [
        ToolMessage(content=data_handoff, tool_call_id="1"),
        ToolMessage(content=todo_handoff, tool_call_id="2"),
        AIMessage(content="两个委派都已生成"),
    ]

    handoffs = AgentOutputParser.extract_all_handoffs_from_messages(delta_messages)
    assert [item["target_agent"] for item in handoffs] == ["data_expert", "todo_expert"]
    assert handoffs[0]["frame"]["query_text"] == "查询嘉兴天气并补充到分析上下文"
    assert "网银功能评审" in handoffs[1]["task_description"]


def test_augment_data_handoff_payload_should_not_backfill_query_text_from_user_message():
    """data handoff 缺失 frame.query_text 时，不应再从用户原问题自动回填。"""
    from app.ai.state import AgentType
    from app.ai.workflow.multi_agent_graph import _augment_data_handoff_payload

    handoff = {
        "action": "handoff",
        "target_agent": AgentType.DATA,
        "task_description": "请执行复杂口径确认后再输出。",
        "frame": None,
        "turn_act_hint": "",
    }

    normalized = _augment_data_handoff_payload(handoff, state={})

    assert normalized["turn_act_hint"] == "NEW_QUERY"
    assert normalized.get("frame") is None
    assert normalized["task_description"] == "请执行复杂口径确认后再输出。"


def test_augment_data_handoff_payload_should_preserve_specific_frame_for_mixed_query():
    """复合问题中若 Supervisor 已生成精确 data frame，不应再受整句原问题污染。"""
    from app.ai.state import AgentType
    from app.ai.workflow.multi_agent_graph import _augment_data_handoff_payload

    handoff = {
        "action": "handoff",
        "target_agent": AgentType.DATA,
        "frame": {
            "query_text": "查看2025-06-30贷款余额前10名客户，按贷款余额降序返回 Top10。",
        },
        "turn_act_hint": "",
    }
    normalized = _augment_data_handoff_payload(handoff, state={})

    assert normalized["turn_act_hint"] == "NEW_QUERY"
    assert "嘉兴" not in normalized["frame"]["query_text"]
    assert "贷款余额前10名" in normalized["frame"]["query_text"]
    assert normalized["frame"]["metric"] == "贷款余额"
    assert normalized["frame"]["time_range"] == "2025-06-30"
    assert normalized["frame"]["query_shape"] == "top_n"
    assert normalized["frame"]["ranking"]["limit"] == 10


def test_augment_data_handoff_payload_should_normalize_existing_frame():
    """已有结构化 frame 时应保持透传，并补齐 query_shape/ranking/turn_act。"""
    from app.ai.state import AgentType
    from app.ai.workflow.multi_agent_graph import _augment_data_handoff_payload

    handoff = {
        "action": "handoff",
        "target_agent": AgentType.DATA,
        "frame": {
            "query_text": "查询2025年6月30日贷款余额前10名的客户",
            "metric": "贷款余额",
            "time_range": "2025-06-30",
        },
        "turn_act_hint": "",
    }

    normalized = _augment_data_handoff_payload(handoff, state={})

    assert normalized["frame"]["metric"] == "贷款余额"
    assert normalized["frame"]["time_range"] == "2025-06-30"
    assert normalized["frame"]["query_text"] == "查询2025年6月30日贷款余额前10名的客户"
    assert normalized["frame"]["query_shape"] == "top_n"
    assert normalized["frame"]["ranking"]["limit"] == 10
    assert normalized["turn_act_hint"] == "NEW_QUERY"



def test_augment_todo_handoff_with_observations_should_skip_query_goal() -> None:
    """todo.query 不应混入 Supervisor 外部观察，否则会把查询待办误伤成 out_of_scope。"""
    from langchain_core.messages import HumanMessage, ToolMessage

    from app.ai.state import AgentType
    from app.ai.workflow.multi_agent_graph import _augment_todo_handoff_with_observations

    handoff = {
        "action": "handoff",
        "target_agent": AgentType.TODO,
        "task_description": "查询待办",
        "frame": {"todo_action": "query"},
    }
    state = {
        "messages": [HumanMessage(content="先查天气，再查询一下我的待办")],
        "current_todo_id": None,
    }
    delta_messages = [
        ToolMessage(
            content='{"results":[{"title":"嘉兴天气预报","content":"今天 晴到多云 明天 晴到多云 5℃~13℃"}]}',
            tool_call_id="t-weather",
            name="tavily_search",
        )
    ]

    normalized = _augment_todo_handoff_with_observations(handoff, delta_messages, state)

    assert normalized["task_description"] == "查询待办"
    assert normalized.get("frame", {}).get("tool_observations") in (None, [])
    assert "todo_fields" not in normalized.get("frame", {})
