"""Supervisor -> Todo handoff 外部信息补全测试。"""

from langchain_core.messages import HumanMessage, ToolMessage

from app.ai.workflow.multi_agent_graph import _augment_todo_handoff_with_observations
from app.ai.workflow.todo_intent_helpers import filter_messages_for_todo


def test_filter_messages_for_todo_should_merge_tool_observation_into_description():
    """handoff 的 tool_observations 应转成待办描述补充。"""
    messages = [HumanMessage(content="描述里加上天气情况")]
    pending_handoff = {
        "task_description": "请把外部信息补充到当前待办",
        "frame": {
            "todo_action": "update",
            "todo_fields": {
                "todo_id": 123,
                "description": "会前确认议程",
            },
            "tool_observations": [
                {
                    "tool": "tavily_search",
                    "topic": "web_search",
                    "summary": "上海明天多云，10~16℃",
                    "status": "ok",
                }
            ],
        },
    }

    filtered, handoff_context, pre_extracted = filter_messages_for_todo(messages, pending_handoff)

    assert len(filtered) == 2
    assert filtered[0].name == "__internal_todo_handoff__"
    assert pre_extracted is not None
    assert pre_extracted.get("action") == "update"
    assert pre_extracted.get("todo_id") == 123
    assert "外部信息补充" in pre_extracted.get("description", "")
    assert "上海明天多云" in pre_extracted.get("description", "")
    assert "外部信息摘要" in handoff_context


def test_filter_messages_for_todo_should_accept_json_string_observations():
    """tool_observations 为 JSON 字符串时也应兼容解析。"""
    messages = [HumanMessage(content="把股价信息加进描述")]
    pending_handoff = {
        "task_description": "更新当前待办",
        "frame": {
            "todo_action": "update",
            "tool_observations": (
                '[{"tool":"tavily_search","topic":"web_search",'
                '"summary":"沪深300收盘上涨0.8%","status":"ok"}]'
            ),
        },
    }

    _, _, pre_extracted = filter_messages_for_todo(messages, pending_handoff)

    assert isinstance(pre_extracted, dict)
    assert isinstance(pre_extracted.get("tool_observations"), list)
    assert "沪深300" in pre_extracted.get("description", "")


def test_augment_todo_handoff_should_inject_tool_observations_and_todo_id():
    """当 supervisor 调用 tavily 后委派 todo，应自动注入 observation 与 todo_id。"""
    handoff = {
        "action": "handoff",
        "target_agent": "todo_expert",
        "task_description": "请更新待办描述",
        "frame": {
            "todo_action": "update",
            "todo_fields": {},
        },
    }

    delta_messages = [
        ToolMessage(
            content='{"answer":"上海明天多云，10~16℃，东南风3级"}',
            tool_call_id="call-1",
            name="tavily_search_results_json",
        )
    ]
    state = {
        "messages": [HumanMessage(content="描述里加上明天上海天气")],
        "current_todo_id": 88,
    }

    enriched = _augment_todo_handoff_with_observations(handoff, delta_messages, state)

    assert enriched.get("target_agent") == "todo_expert"
    frame = enriched.get("frame", {})
    todo_fields = frame.get("todo_fields", {})
    observations = frame.get("tool_observations", [])

    assert todo_fields.get("todo_id") == 88
    assert "外部信息补充" in todo_fields.get("description", "")
    assert observations and observations[0].get("tool") == "tavily_search_results_json"
    assert enriched.get("turn_act_hint") == "SUPPLEMENT"


def test_filter_messages_for_todo_should_build_contract_first_messages():
    """命中 handoff 时应优先生成内部 contract 消息，而不是透传历史消息窗口。"""
    messages = [
        HumanMessage(content="旧问题：帮我查天气"),
        HumanMessage(content="描述里加上天气情况"),
    ]
    pending_handoff = {
        "task_description": "请补充外部信息后更新待办",
        "turn_act_hint": "SUPPLEMENT",
        "frame": {
            "todo_action": "update",
            "todo_fields": {"todo_id": 123, "description": "会前确认议程"},
        },
    }

    filtered, _, pre_extracted = filter_messages_for_todo(messages, pending_handoff)

    assert len(filtered) == 2
    assert filtered[0].name == "__internal_todo_handoff__"
    assert filtered[0].additional_kwargs["expert_input_contract"] == {
        "contract_id": "todo_handoff_frame",
        "contract_version": "v1",
        "target_agent": "todo_expert",
        "state_owner": "supervisor",
        "source_fields": [
            "pending_handoff.frame.todo_action",
            "pending_handoff.frame.todo_fields",
            "pending_handoff.turn_act_hint",
        ],
    }
    assert filtered[1].content == "描述里加上天气情况"
    assert pre_extracted.get("action") == "update"
    assert pre_extracted.get("todo_id") == 123


def test_filter_messages_for_todo_should_prefer_frame_over_task_description_noise():
    """frame 存在时，应优先吃结构化 frame，而不是 task_description 噪声。"""
    messages = [HumanMessage(content="把描述补完整")]
    pending_handoff = {
        "task_description": "删除这个待办",
        "frame": {
            "todo_action": "update",
            "todo_fields": {"todo_id": 99, "description": "保留原待办"},
        },
    }

    _, handoff_context, pre_extracted = filter_messages_for_todo(messages, pending_handoff)

    assert pre_extracted.get("action") == "update"
    assert pre_extracted.get("todo_id") == 99
    assert "删除这个待办" not in handoff_context
