"""multi_agent_graph streaming helper 回归测试。"""

from types import SimpleNamespace
from unittest.mock import patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from app.ai.protocol import (
    AgentOutputParser,
    build_operation_additional_kwargs_payload,
    build_result_additional_kwargs_payload,
    build_streaming_kb_images_payload,
    build_streaming_result_payload,
    build_streaming_result_payload_from_fields,
    build_streaming_tool_start_payload,
    extract_operation_from_ai_message,
)
from app.core.config_contract import TOOL_POLICY_CONTRACT
from app.services.config_resolver import ConfigResolver
from app.services.system_config_service import SystemConfigService

from app.ai.workflow.multi_agent_graph import (
    StreamingContext,
    _apply_router_contract_guard,
    _build_direct_lookup_findings,
    _build_streaming_delta_return,
    _create_streaming_agent_wrapper,
    _dispatch_messages_mode_chunk,
    _dispatch_values_mode_chunk,
    _execute_streaming_wrapper,
    _emit_messages_mode_thinking,
    _emit_messages_mode_token,
    _extract_supervisor_tool_observations,
    fallback_router,
    _handle_streaming_wrapper_exception,
    _handle_messages_mode_tool_message,
    _inject_streaming_context_messages,
    _prefill_emitted_message_ids,
    _record_emitted_message_id,
    _run_streaming_dispatch_loop,
    _prepare_messages_for_supervisor_inference,
    _prepare_streaming_inference_state,
)
from app.services.chat_service import degrade_on_plugin_failure


def _make_ctx(
    *,
    writer=None,
    node_name: str = "supervisor",
    state=None,
    collected_content=None,
    kb_images=None,
    emitted_message_ids=None,
    sent_tool_call_ids=None,
) -> StreamingContext:
    """构造测试用 StreamingContext 实例。"""
    return StreamingContext(
        writer=writer or SimpleNamespace(),
        node_name=node_name,
        state=state if state is not None else {},
        collected_content=collected_content if collected_content is not None else [],
        kb_images=kb_images if kb_images is not None else {},
        emitted_message_ids=emitted_message_ids if emitted_message_ids is not None else set(),
        sent_tool_call_ids=sent_tool_call_ids if sent_tool_call_ids is not None else set(),
    )


def test_record_emitted_message_id_only_tracks_existing_id() -> None:
    """仅当消息包含 id 时应加入去重集合。"""
    emitted_ids: set[str] = set()

    _record_emitted_message_id(SimpleNamespace(id="msg-1"), emitted_ids)
    _record_emitted_message_id(SimpleNamespace(id=None), emitted_ids)
    _record_emitted_message_id(SimpleNamespace(), emitted_ids)

    assert emitted_ids == {"msg-1"}


def test_streaming_context_holds_shared_state() -> None:
    """StreamingContext 应正确封装流式会话共享状态。"""
    ctx = _make_ctx(
        writer=lambda x: x,
        node_name="todo_expert",
        state={"thread_id": "t-1"},
        collected_content=["hello"],
        kb_images={"img-1": "url"},
        emitted_message_ids={"msg-1"},
        sent_tool_call_ids={"tc-1"},
    )

    assert ctx.node_name == "todo_expert"
    assert ctx.state == {"thread_id": "t-1"}
    assert ctx.collected_content == ["hello"]
    assert ctx.kb_images == {"img-1": "url"}
    assert ctx.emitted_message_ids == {"msg-1"}
    assert ctx.sent_tool_call_ids == {"tc-1"}


def test_build_streaming_tool_start_payload_normalizes_invalid_args() -> None:
    """tool_start payload builder 应清洗名称与参数。"""
    payload = build_streaming_tool_start_payload(" search ", ["not", "dict"])

    assert payload == {"name": "search", "input": {}}
    assert build_streaming_tool_start_payload("", {"q": "x"}) is None


def test_build_streaming_result_payload_extracts_structured_result() -> None:
    """result payload builder 应仅在 data_type 存在时返回载荷。"""
    payload = build_streaming_result_payload(
        SimpleNamespace(additional_kwargs={"data_type": "table", "data": {"rows": [1]}}),
        "结果文本",
    )

    assert payload == {"data_type": "table", "data": {"rows": [1]}, "message": "结果文本"}
    assert build_streaming_result_payload(SimpleNamespace(additional_kwargs={}), "x") is None


def test_build_streaming_result_payload_from_fields_normalizes_inputs() -> None:
    """字段模式的 result payload builder 应归一化类型与 data。"""
    payload = build_streaming_result_payload_from_fields(
        data_type=" sql_result ",
        data=[1, 2, 3],
        message=None,
    )

    assert payload == {
        "data_type": "sql_result",
        "data": {},
        "message": "",
    }
    assert build_streaming_result_payload_from_fields(data_type="", data={}, message="x") is None


def test_build_result_additional_kwargs_payload_normalizes_inputs() -> None:
    """result additional_kwargs builder 应复用统一字段归一化。"""
    payload = build_result_additional_kwargs_payload(
        data_type=" sql_result ",
        data=[1, 2],
    )

    assert payload == {
        "data_type": "sql_result",
        "data": {},
    }
    assert build_result_additional_kwargs_payload(data_type="", data={"x": 1}) is None


def test_operation_additional_kwargs_build_and_extract_roundtrip() -> None:
    """operation additional_kwargs 的构建与提取应一致。"""
    additional_kwargs = build_operation_additional_kwargs_payload(
        {
            "action": " create ",
            "data": "invalid",
            "summary": "确认创建",
        }
    )

    assert additional_kwargs == {
        "operation": {
            "action": "create",
            "data": {},
            "summary": "确认创建",
        }
    }

    message = AIMessage(content="ok", additional_kwargs=additional_kwargs)
    assert extract_operation_from_ai_message(message) == additional_kwargs["operation"]
    assert extract_operation_from_ai_message(HumanMessage(content="noop")) is None


def test_build_streaming_kb_images_payload_returns_copy() -> None:
    """kb_images payload builder 应返回隔离副本。"""
    source = {"img-1": "https://example.com/a.png"}

    payload = build_streaming_kb_images_payload(source)
    source["img-2"] = "https://example.com/b.png"

    assert payload == {"images": {"img-1": "https://example.com/a.png"}}


@pytest.mark.asyncio
async def test_prefill_emitted_message_ids_reads_state_and_subgraph() -> None:
    """预填充应同时覆盖主图 state 与子图 checkpoint 消息。"""

    class _FakeAgent:
        async def aget_state(self, _config):
            return SimpleNamespace(
                values={
                    "messages": [
                        SimpleNamespace(id="subgraph-1"),
                        SimpleNamespace(id="state-1"),
                    ]
                }
            )

    emitted_ids: set[str] = set()
    state_messages = [
        SimpleNamespace(id="state-1"),
        SimpleNamespace(id="state-2"),
        SimpleNamespace(id=None),
    ]

    await _prefill_emitted_message_ids(
        agent=_FakeAgent(),
        config=SimpleNamespace(),
        state_messages=state_messages,
        emitted_message_ids=emitted_ids,
        node_name="supervisor",
    )

    assert emitted_ids == {"state-1", "state-2", "subgraph-1"}


def test_handle_messages_mode_tool_message_emits_tool_end_and_kb_images() -> None:
    """ToolMessage 应触发 tool_end，并更新 kb_images。"""
    emitted_events = []
    kb_images: dict[str, str] = {}
    writer = emitted_events.append
    message = ToolMessage(content="tool payload", tool_call_id="tc-1", name="knowledge_search")
    ctx = _make_ctx(writer=writer, node_name="supervisor", kb_images=kb_images)

    with patch("app.ai.workflow.multi_agent_graph.emit_tool_end", side_effect=lambda w, name, output, node: w((name, output, node))), \
         patch("app.ai.workflow.multi_agent_graph.AgentOutputParser") as mock_parser:
        mock_parser.parse_kb_images.return_value = {"img-1": "https://example.com/a.png"}

        handled = _handle_messages_mode_tool_message(
            message=message,
            ctx=ctx,
        )

    assert handled is True
    assert kb_images == {"img-1": "https://example.com/a.png"}
    assert emitted_events == [("knowledge_search", "tool payload", "supervisor")]


def test_prepare_messages_for_supervisor_inference_sets_tool_message_truncation_flag() -> None:
    """压缩后的 ToolMessage 应记录 truncation_flag 诊断字段。"""
    tool_message = ToolMessage(
        content="A" * 5000,
        tool_call_id="tool-call-1",
        name="knowledge_search",
        id="tool-msg-1",
    )

    prepared = _prepare_messages_for_supervisor_inference([tool_message])

    assert prepared[0] is not tool_message
    assert "已省略" in str(prepared[0].content)
    assert prepared[0].additional_kwargs.get("truncation_flag") is True


def test_prepare_messages_for_supervisor_inference_skips_short_tool_message_truncation_flag() -> None:
    """短 ToolMessage 不应被压缩，也不应新增截断标记。"""
    tool_message = ToolMessage(
        content="短结果",
        tool_call_id="tool-call-2",
        name="knowledge_search",
    )

    prepared = _prepare_messages_for_supervisor_inference([tool_message])

    assert prepared[0] is tool_message
    assert prepared[0].additional_kwargs.get("truncation_flag") is None


def test_prepare_streaming_inference_state_tracks_tool_message_diagnostics() -> None:
    """推理态应记录 ToolMessage 压缩前后预算诊断。"""
    state = {
        "messages": [
            HumanMessage(content="请总结检索证据"),
            ToolMessage(
                content="A" * 5000,
                tool_call_id="tool-call-3",
                name="knowledge_search",
            ),
        ],
        "delivery_meta": {"source": "existing"},
    }

    pruned_state, *_ = _prepare_streaming_inference_state(state)

    delivery_meta = pruned_state["delivery_meta"]
    assert delivery_meta["source"] == "existing"
    assert delivery_meta["truncation_flag"] is True
    assert delivery_meta["tool_message_count"] == 1
    assert delivery_meta["truncated_tool_message_count"] == 1
    assert delivery_meta["tool_message_chars_before"] > delivery_meta["tool_message_chars_after"]


def test_prepare_streaming_inference_state_keeps_tool_message_without_truncation() -> None:
    """短 ToolMessage 不压缩时应保持 truncation_flag 为 False。"""
    state = {
        "messages": [
            HumanMessage(content="请总结"),
            ToolMessage(
                content="短结果",
                tool_call_id="tool-call-4",
                name="knowledge_search",
            ),
        ],
    }

    pruned_state, *_ = _prepare_streaming_inference_state(state)

    delivery_meta = pruned_state["delivery_meta"]
    assert delivery_meta["truncation_flag"] is False
    assert delivery_meta["tool_message_count"] == 1
    assert delivery_meta["truncated_tool_message_count"] == 0
    assert delivery_meta["tool_message_chars_before"] == delivery_meta["tool_message_chars_after"]


def test_emit_messages_mode_token_filters_internal_content() -> None:
    """内部协议文本不应向前端发送 token。"""
    emitted_tokens = []
    collected_content: list[str] = []
    ctx = _make_ctx(
        node_name="todo_expert",
        collected_content=collected_content,
    )

    with patch("app.ai.workflow.multi_agent_graph.AgentOutputParser") as mock_parser, \
         patch("app.ai.workflow.multi_agent_graph.emit_token", side_effect=lambda _w, content, node: emitted_tokens.append((content, node))):
        mock_parser.should_filter_content.side_effect = lambda c: c == "[[internal]]"

        _emit_messages_mode_token(
            message=SimpleNamespace(content="正常输出"),
            ctx=ctx,
        )
        _emit_messages_mode_token(
            message=SimpleNamespace(content="[[internal]]"),
            ctx=ctx,
        )

    assert collected_content == ["正常输出"]
    assert emitted_tokens == [("正常输出", "todo_expert")]


def test_emit_messages_mode_thinking_prefers_reasoning_content() -> None:
    """思考内容应按 reasoning -> thinking_content -> thinking 顺序输出。"""
    emitted = []
    ctx = _make_ctx(node_name="supervisor")

    with patch("app.ai.workflow.multi_agent_graph.emit_thinking", side_effect=lambda _w, content, node: emitted.append((content, node))):
        _emit_messages_mode_thinking(
            message=SimpleNamespace(additional_kwargs={"reasoning_content": "step by step"}),
            ctx=ctx,
        )

    assert emitted == [("step by step", "supervisor")]


def test_inject_streaming_context_messages_inserts_after_system_prefix() -> None:
    """系统/技能上下文应插入在原始 SystemMessage 之后。"""
    base_system = SystemMessage(content="base-system")
    user_message = HumanMessage(content="用户问题")
    pruned_messages = [base_system, user_message]

    merged = _inject_streaming_context_messages(
        pruned_messages=pruned_messages,
        state={"system_context": "now=2026-02-18", "skill_context": "skill=todo"},
    )

    assert merged[0] is base_system
    assert merged[1].content == "now=2026-02-18"
    assert merged[2].content == "skill=todo"
    assert merged[3] is user_message


def test_build_streaming_delta_return_keeps_non_message_keys() -> None:
    """增量返回应保留其他状态字段并仅返回新增消息。"""
    final_state = {
        "messages": ["m1", "m2", "m3"],
        "thread_id": "thread-1",
        "user_id": 1001,
    }

    ret = _build_streaming_delta_return(
        final_state=final_state,
        initial_input_count=2,
        node_name="supervisor",
    )

    assert ret["messages"] == ["m3"]
    assert ret["thread_id"] == "thread-1"
    assert ret["user_id"] == 1001


def test_dispatch_messages_mode_chunk_emits_token_and_thinking() -> None:
    """messages dispatcher 应处理 AIMessage 并发出 token/thinking。"""
    emitted_ids: set[str] = set()
    collected_content: list[str] = []
    token_events = []
    thinking_events = []
    ctx = _make_ctx(
        node_name="supervisor",
        state={"multi_intent_mode": False},
        collected_content=collected_content,
        emitted_message_ids=emitted_ids,
    )

    message = AIMessage(
        content="这是回答",
        additional_kwargs={"thinking": "这是思考"},
        id="ai-msg-1",
    )

    with patch("app.ai.workflow.multi_agent_graph.AgentOutputParser") as mock_parser, \
         patch("app.ai.workflow.multi_agent_graph.emit_token", side_effect=lambda _w, content, node: token_events.append((content, node))), \
         patch("app.ai.workflow.multi_agent_graph.emit_thinking", side_effect=lambda _w, content, node: thinking_events.append((content, node))):
        mock_parser.should_filter_content.return_value = False

        _dispatch_messages_mode_chunk(
            chunk=(message, {"node": "supervisor"}),
            ctx=ctx,
        )

    assert emitted_ids == {"ai-msg-1"}
    assert collected_content == ["这是回答"]
    assert token_events == [("这是回答", "supervisor")]
    assert thinking_events == [("这是思考", "supervisor")]


def test_dispatch_values_mode_chunk_emits_values_text_message() -> None:
    """values dispatcher 应处理新增 AI 消息并补发文本。"""
    emitted_ids: set[str] = set()
    collected_content: list[str] = []
    token_events = []
    ctx = _make_ctx(
        node_name="todo_expert",
        state={"messages": [HumanMessage(content="测试")], "thread_id": "thread-1"},
        collected_content=collected_content,
        emitted_message_ids=emitted_ids,
    )

    final_state = {
        "messages": [AIMessage(content="values补发", id="ai-values-1")],
        "thread_id": "thread-1",
    }

    with patch("app.ai.workflow.multi_agent_graph.AgentOutputParser") as mock_parser, \
         patch("app.ai.workflow.multi_agent_graph.emit_token", side_effect=lambda _w, content, node: token_events.append((content, node))):
        mock_parser.should_filter_content.return_value = False
        mock_parser.parse_kb_images.return_value = {}
        mock_parser.extract_all_handoffs_from_messages.return_value = []

        updated_count, handoff_return = _dispatch_values_mode_chunk(
            final_state=final_state,
            initial_input_count=0,
            input_message_count=0,
            ctx=ctx,
        )

    assert handoff_return is None
    assert updated_count == 1
    assert collected_content == ["values补发"]
    assert emitted_ids == {"ai-values-1"}
    assert token_events == [("values补发", "todo_expert")]


def test_dispatch_values_mode_chunk_uses_result_emitter_for_structured_payload() -> None:
    """values dispatcher 遇到结构化载荷时应通过 emit_result 发送。"""
    emitted_ids: set[str] = set()
    collected_content: list[str] = []
    token_events = []
    result_events = []
    ctx = _make_ctx(
        node_name="todo_expert",
        state={"messages": [HumanMessage(content="测试")], "thread_id": "thread-1"},
        collected_content=collected_content,
        emitted_message_ids=emitted_ids,
    )

    final_state = {
        "messages": [
            AIMessage(
                content="结构化结果",
                additional_kwargs={"data_type": "table", "data": {"rows": [{"id": 1}]}},
                id="ai-values-result-1",
            )
        ],
        "thread_id": "thread-1",
    }

    with patch("app.ai.workflow.multi_agent_graph.AgentOutputParser") as mock_parser, \
         patch("app.ai.workflow.multi_agent_graph.emit_token", side_effect=lambda _w, content, node: token_events.append((content, node))), \
         patch("app.ai.workflow.multi_agent_graph.emit_result", side_effect=lambda _w, data_type, data, message, node: result_events.append((data_type, data, message, node))):
        mock_parser.should_filter_content.return_value = False
        mock_parser.parse_kb_images.return_value = {}
        mock_parser.extract_all_handoffs_from_messages.return_value = []

        updated_count, handoff_return = _dispatch_values_mode_chunk(
            final_state=final_state,
            initial_input_count=0,
            input_message_count=0,
            ctx=ctx,
        )

    assert handoff_return is None
    assert updated_count == 1
    assert token_events == []
    assert result_events == [("table", {"rows": [{"id": 1}]}, "结构化结果", "todo_expert")]
    assert collected_content == ["结构化结果"]
    assert emitted_ids == {"ai-values-result-1"}


def test_dispatch_values_mode_chunk_emits_kb_images_from_tool_delta() -> None:
    """values dispatcher 应从增量 ToolMessage 提取并发送 kb_images。"""
    kb_images: dict[str, str] = {}
    kb_image_events = []
    ctx = _make_ctx(
        node_name="todo_expert",
        state={"messages": [HumanMessage(content="测试")], "thread_id": "thread-1"},
        kb_images=kb_images,
    )

    final_state = {
        "messages": [ToolMessage(content="tool payload", tool_call_id="tc-1", name="knowledge_search")],
        "thread_id": "thread-1",
    }

    with patch("app.ai.workflow.multi_agent_graph.AgentOutputParser") as mock_parser, \
         patch("app.ai.workflow.multi_agent_graph.emit_kb_images", side_effect=lambda _w, images, node: kb_image_events.append((dict(images), node))):
        mock_parser.parse_kb_images.return_value = {"img-1": "https://example.com/kb.png"}
        mock_parser.should_filter_content.return_value = False
        mock_parser.extract_all_handoffs_from_messages.return_value = []

        updated_count, handoff_return = _dispatch_values_mode_chunk(
            final_state=final_state,
            initial_input_count=0,
            input_message_count=1,
            ctx=ctx,
        )

    assert handoff_return is None
    assert updated_count == 1
    assert kb_images == {"img-1": "https://example.com/kb.png"}
    assert kb_image_events == [({"img-1": "https://example.com/kb.png"}, "todo_expert")]


def test_dispatch_values_mode_chunk_builds_handoff_queue_for_multi_intent() -> None:
    """supervisor values 模式应保留 handoff 顺序并构造队列。"""
    ctx = _make_ctx(
        node_name="supervisor",
        state={
            "messages": [HumanMessage(content="复合任务")],
            "thread_id": "thread-1",
            "decomposed_goals": [
                {
                    "goal_id": "GOAL-01",
                    "order": 1,
                    "kind": "data.query",
                    "title": "数据查询",
                    "must_answer": True,
                    "allowed_agents": ["data_expert"],
                },
                {
                    "goal_id": "GOAL-02",
                    "order": 2,
                    "kind": "todo.query",
                    "title": "待办事项",
                    "must_answer": True,
                    "allowed_agents": ["todo_expert"],
                },
            ],
        },
    )

    final_state = {
        "messages": [ToolMessage(content="handoff-json", tool_call_id="tc-1", name="assign_to_data_expert")],
        "thread_id": "thread-1",
    }

    with patch("app.ai.workflow.multi_agent_graph.AgentOutputParser") as mock_parser:
        mock_parser.extract_all_handoffs_from_messages.return_value = [
            {
                "action": "handoff",
                "target_agent": "data_expert",
                "task_description": "查询网银功能",
            },
            {
                "action": "handoff",
                "target_agent": "todo_expert",
                "task_description": "创建待办提醒输出网银汇总",
            },
        ]
        mock_parser.parse_kb_images.return_value = {}
        mock_parser.should_filter_content.return_value = False

        updated_count, handoff_return = _dispatch_values_mode_chunk(
            final_state=final_state,
            initial_input_count=0,
            input_message_count=0,
            ctx=ctx,
        )

    assert updated_count == 0
    assert handoff_return is not None
    assert handoff_return["pending_handoff"]["target_agent"] == "data_expert"
    assert handoff_return["handoff_queue"][0]["target_agent"] == "todo_expert"
    assert handoff_return["multi_intent_mode"] is True


def test_apply_router_contract_guard_blocks_disallowed_targets() -> None:
    """Router 合同门禁应拦截不在 allowed_agents 内的委派。"""
    handoffs = [
        {"target_agent": "data_expert", "task_description": "先查数据"},
        {"target_agent": "todo_expert", "task_description": "再查待办"},
    ]
    state = {
        "decomposed_goals": [
            {
                "goal_id": "GOAL-01",
                "order": 1,
                "kind": "todo.query",
                "title": "待办事项",
                "must_answer": True,
                "allowed_agents": ["todo_expert"],
            }
        ]
    }

    accepted, blocked, pending = _apply_router_contract_guard(handoffs, state=state)

    assert len(accepted) == 1
    assert accepted[0]["target_agent"] == "todo_expert"
    assert accepted[0]["goal_id"] == "GOAL-01"
    assert len(blocked) == 1
    assert blocked[0]["reason"] == "target_not_in_allowed_agents"
    assert blocked[0]["allowed_agents"] == ["todo_expert"]
    assert pending == []


def test_dispatch_values_mode_chunk_filters_disallowed_handoff_by_contract() -> None:
    """values dispatcher 应基于 allowed_agents 过滤无效 handoff 并继续可用委派。"""
    ctx = _make_ctx(
        writer=lambda _event: None,
        node_name="supervisor",
        state={
            "messages": [HumanMessage(content="先查待办")],
            "thread_id": "thread-1",
            "decomposed_goals": [
                {
                    "goal_id": "GOAL-01",
                    "order": 1,
                    "kind": "todo.query",
                    "title": "待办事项",
                    "must_answer": True,
                    "allowed_agents": ["todo_expert"],
                }
            ],
        },
    )

    final_state = {
        "messages": [ToolMessage(content="handoff-json", tool_call_id="tc-1", name="assign_to_data_expert")],
        "thread_id": "thread-1",
    }

    with patch("app.ai.workflow.multi_agent_graph.AgentOutputParser") as mock_parser:
        mock_parser.extract_all_handoffs_from_messages.return_value = [
            {
                "action": "handoff",
                "target_agent": "data_expert",
                "task_description": "误派到 data",
            },
            {
                "action": "handoff",
                "target_agent": "todo_expert",
                "task_description": "回到待办",
            },
        ]
        mock_parser.parse_kb_images.return_value = {}
        mock_parser.should_filter_content.return_value = False

        updated_count, handoff_return = _dispatch_values_mode_chunk(
            final_state=final_state,
            initial_input_count=0,
            input_message_count=0,
            ctx=ctx,
        )

    assert updated_count == 0
    assert handoff_return is not None
    assert handoff_return["pending_handoff"]["target_agent"] == "todo_expert"
    assert handoff_return["pending_handoff"]["goal_id"] == "GOAL-01"
    assert handoff_return["delivery_meta"]["router_contract_blocked_count"] == 1
    assert handoff_return["router_result_v2"]["version"] == "v2"
    assert handoff_return["router_result_v2"]["route_decisions"][0]["target_agent"] == "todo_expert"


def test_dispatch_values_mode_chunk_marks_retry_when_all_handoffs_blocked() -> None:
    """当 handoff 全部被门禁拦截时，应保留补齐上下文并等待下一轮重试。"""
    ctx = _make_ctx(
        writer=lambda _event: None,
        node_name="supervisor",
        state={
            "messages": [HumanMessage(content="先查待办")],
            "thread_id": "thread-1",
            "decomposed_goals": [
                {
                    "goal_id": "GOAL-01",
                    "order": 1,
                    "kind": "todo.query",
                    "title": "待办事项",
                    "must_answer": True,
                    "allowed_agents": ["todo_expert"],
                }
            ],
            "system_context": "当前时间: 2026-02-28",
        },
    )

    final_state = {
        "messages": [ToolMessage(content="handoff-json", tool_call_id="tc-1", name="assign_to_data_expert")],
        "thread_id": "thread-1",
    }

    with patch("app.ai.workflow.multi_agent_graph.AgentOutputParser") as mock_parser:
        mock_parser.extract_all_handoffs_from_messages.return_value = [
            {
                "action": "handoff",
                "target_agent": "data_expert",
                "task_description": "误派到 data",
            }
        ]
        mock_parser.parse_kb_images.return_value = {}
        mock_parser.should_filter_content.return_value = False

        updated_count, handoff_return = _dispatch_values_mode_chunk(
            final_state=final_state,
            initial_input_count=0,
            input_message_count=0,
            ctx=ctx,
        )

    assert updated_count == 0
    assert handoff_return is None
    assert final_state["multi_intent_mode"] is True
    assert final_state["delivery_meta"]["router_contract_blocked_count"] == 1
    assert final_state["router_result_v2"]["event"] == "intent_router_handoff_blocked"
    assert "【交付补齐提示】" in final_state["system_context"]


def test_dispatch_values_mode_chunk_marks_multi_intent_for_direct_lookup_plus_single_handoff() -> None:
    """supervisor 仅 1 个 handoff + 直连检索结果时也应进入 multi_intent_mode。"""
    ctx = _make_ctx(
        node_name="supervisor",
        state={
            "messages": [HumanMessage(content="查待办并看天气")],
            "thread_id": "thread-1",
            "decomposed_goals": [
                {
                    "goal_id": "GOAL-01",
                    "order": 1,
                    "kind": "todo.query",
                    "title": "待办事项",
                    "must_answer": True,
                    "allowed_agents": ["todo_expert"],
                }
            ],
        },
    )

    final_state = {
        "messages": [
            ToolMessage(
                content='{"answer":"嘉兴今天多云，气温 18-24 摄氏度"}',
                tool_call_id="tc-1",
                name="tavily_search",
            ),
            ToolMessage(content="handoff-json", tool_call_id="tc-2", name="assign_to_todo_expert"),
        ],
        "thread_id": "thread-1",
    }

    with patch("app.ai.workflow.multi_agent_graph.AgentOutputParser") as mock_parser:
        mock_parser.extract_all_handoffs_from_messages.return_value = [
            {
                "action": "handoff",
                "target_agent": "todo_expert",
                "task_description": "查询待办并结合天气结果回复用户",
            }
        ]
        mock_parser.parse_kb_images.return_value = {}
        mock_parser.should_filter_content.return_value = False

        updated_count, handoff_return = _dispatch_values_mode_chunk(
            final_state=final_state,
            initial_input_count=0,
            input_message_count=0,
            ctx=ctx,
        )

    assert updated_count == 0
    assert handoff_return is not None
    assert handoff_return["pending_handoff"]["target_agent"] == "todo_expert"
    assert handoff_return["multi_intent_mode"] is True
    assert handoff_return["pending_handoff"]["frame"]["tool_observations"][0]["tool"] == "tavily_search"


def test_build_direct_lookup_findings_ignores_tavily_error_output() -> None:
    """Tavily 错误输出不应进入用户可见的外部信息摘要。"""
    messages = [
        ToolMessage(
            content="No search results found for '嘉兴 未来7天 天气 预报'. Suggestions: Remove time_range argument",
            tool_call_id="tc-err",
            name="tavily_search",
            status="error",
        )
    ]

    findings = _build_direct_lookup_findings(messages)

    assert findings == []




def test_build_direct_lookup_findings_sanitizes_tavily_raw_markup_noise() -> None:
    """Tavily 原始搜索文本含 HTML/站点噪声时，不应直接透传到最终答复。"""
    messages = [
        ToolMessage(
            content='嘉兴天气: " alt="" style="height:0.4rem;line-height:0.4rem;"> # 嘉兴天气 精细化预报 7天天气预报 2.3mm 3.3m/s 17:00 10.1℃；【嘉兴天气预报】 嘉兴天气预报7天_全国天气网: # 全国天气网 首页 国内天气 空气质量',
            tool_call_id="tc-raw",
            name="tavily_search",
        )
    ]

    findings = _build_direct_lookup_findings(messages)

    assert findings
    summary = findings[0]["summary"]
    assert "alt=" not in summary
    assert "style=" not in summary
    assert "#" not in summary
    assert "首页" not in summary
    assert "嘉兴天气" in summary

def test_extract_supervisor_tool_observations_ignores_tavily_error_output() -> None:
    """handoff frame 不应携带 Tavily 错误文本。"""
    messages = [
        ToolMessage(
            content="No search results found for '嘉兴 未来7天 天气 预报'. Suggestions: Remove time_range argument",
            tool_call_id="tc-err",
            name="tavily_search",
            status="error",
        )
    ]

    observations = _extract_supervisor_tool_observations(messages)

    assert observations == []


def test_dispatch_values_mode_chunk_uses_decomposed_goals_to_enable_multi_intent_mode() -> None:
    """当 decomposed_goals 含多个必答目标时，单 handoff 也应进入 multi_intent_mode。"""
    ctx = _make_ctx(
        node_name="supervisor",
        state={
            "messages": [HumanMessage(content="先查待办，再看天气")],
            "thread_id": "thread-1",
            "decomposed_goals": [
                {"goal_id": "GOAL-01", "kind": "todo.query", "must_answer": True},
                {"goal_id": "GOAL-02", "kind": "external.lookup", "must_answer": True},
            ],
        },
    )

    final_state = {
        "messages": [ToolMessage(content="handoff-json", tool_call_id="tc-1", name="assign_to_todo_expert")],
        "thread_id": "thread-1",
    }

    with patch("app.ai.workflow.multi_agent_graph.AgentOutputParser") as mock_parser:
        mock_parser.extract_all_handoffs_from_messages.return_value = [
            {
                "action": "handoff",
                "target_agent": "todo_expert",
                "task_description": "先查询待办",
            }
        ]
        mock_parser.parse_kb_images.return_value = {}
        mock_parser.should_filter_content.return_value = False

        updated_count, handoff_return = _dispatch_values_mode_chunk(
            final_state=final_state,
            initial_input_count=0,
            input_message_count=0,
            ctx=ctx,
        )

    assert updated_count == 0
    assert handoff_return is not None
    assert handoff_return["pending_handoff"]["target_agent"] == "todo_expert"
    assert handoff_return["multi_intent_mode"] is True


@pytest.mark.asyncio
async def test_run_streaming_dispatch_loop_routes_messages_and_values() -> None:
    """streaming 分发循环应按 messages/values 顺序处理并返回最终状态。"""

    class _FakeAgent:
        async def astream(self, _pruned_state, _config, stream_mode):
            assert stream_mode == ["messages", "values", "custom"]
            yield (
                "messages",
                (
                    AIMessage(
                        content="messages-token",
                        additional_kwargs={"thinking": "messages-thinking"},
                        id="msg-1",
                    ),
                    {},
                ),
            )
            yield ("values", {"messages": [AIMessage(content="values-token", id="msg-2")]})

    emitted_ids: set[str] = set()
    sent_tool_call_ids: set[str] = set()
    collected_content: list[str] = []
    token_events = []
    thinking_events = []
    ctx = _make_ctx(
        node_name="supervisor",
        state={"messages": [HumanMessage(content="测试消息")]},
        collected_content=collected_content,
        emitted_message_ids=emitted_ids,
        sent_tool_call_ids=sent_tool_call_ids,
    )

    with patch("app.ai.workflow.multi_agent_graph.AgentOutputParser") as mock_parser, \
         patch("app.ai.workflow.multi_agent_graph.emit_token", side_effect=lambda _w, content, node: token_events.append((content, node))), \
         patch("app.ai.workflow.multi_agent_graph.emit_thinking", side_effect=lambda _w, content, node: thinking_events.append((content, node))):
        mock_parser.should_filter_content.return_value = False
        mock_parser.parse_kb_images.return_value = {}
        mock_parser.extract_all_handoffs_from_messages.return_value = []

        final_state, handoff_return = await _run_streaming_dispatch_loop(
            agent=_FakeAgent(),
            pruned_state={"messages": []},
            config=SimpleNamespace(),
            input_message_count=0,
            ctx=ctx,
        )

    assert handoff_return is None
    assert final_state is not None
    assert len(final_state["messages"]) == 1
    assert collected_content == ["messages-token", "values-token"]
    assert emitted_ids == {"msg-1", "msg-2"}
    assert token_events == [
        ("messages-token", "supervisor"),
        ("values-token", "supervisor"),
    ]
    assert thinking_events == [("messages-thinking", "supervisor")]


@pytest.mark.asyncio
async def test_run_streaming_dispatch_loop_filters_invalid_custom_chunks() -> None:
    """custom 分发应忽略非标准 chunk，仅透传标准事件。"""

    class _FakeAgent:
        async def astream(self, _pruned_state, _config, stream_mode):
            assert stream_mode == ["messages", "values", "custom"]
            yield ("custom", {"not_type": "bad"})
            yield ("custom", "invalid-string")
            yield (
                "custom",
                {"type": "status", "data": {"stage": "ok"}, "node": "supervisor"},
            )
            yield ("values", {"messages": []})

    custom_events = []
    ctx = _make_ctx(
        writer=custom_events.append,
        node_name="supervisor",
        state={"messages": [HumanMessage(content="测试 custom")], "thread_id": "thread-1"},
    )

    with patch("app.ai.workflow.multi_agent_graph.AgentOutputParser") as mock_parser:
        mock_parser.extract_all_handoffs_from_messages.return_value = []
        mock_parser.parse_kb_images.return_value = {}
        mock_parser.should_filter_content.return_value = False

        final_state, handoff_return = await _run_streaming_dispatch_loop(
            agent=_FakeAgent(),
            pruned_state={"messages": []},
            config=SimpleNamespace(),
            input_message_count=0,
            ctx=ctx,
        )

    assert handoff_return is None
    assert final_state == {"messages": [], "decomposed_goals": []}
    assert custom_events == [{"type": "status", "data": {"stage": "ok"}, "node": "supervisor"}]


def test_handle_streaming_wrapper_exception_uses_supervisor_fallback(monkeypatch) -> None:
    """supervisor 命中模型权限错误时应回到 supervisor_fallback，而非专家兜底。"""
    monkeypatch.setenv("ENABLE_RUNTIME_RECOVERY", "true")
    monkeypatch.delenv("ENABLE_PLUGIN_REGISTRY", raising=False)

    status_events = []
    token_events = []
    ctx = _make_ctx(
        writer=status_events.append,
        node_name="supervisor",
        state={"messages": [HumanMessage(content="请帮我查看待办列表")]},
    )

    with patch("app.ai.workflow.multi_agent_graph.emit_status", side_effect=lambda writer, message, node: writer((message, node))), \
         patch("app.ai.workflow.multi_agent_graph.emit_token", side_effect=lambda _w, content, node: token_events.append((content, node))):
        result = _handle_streaming_wrapper_exception(
            error_text="Error Code: 403, subscription_not_found",
            ctx=ctx,
        )

    assert len(result["messages"]) == 1
    assert result["messages"][0].content.startswith("模型服务当前不可用")
    assert result["runtime_recovery_state"]["fallback_route"] == "supervisor_fallback"
    assert result["runtime_recovery_state"]["plugin_lifecycle_status"] == "disabled"
    assert result["runtime_recovery_state"]["recovery_metrics"]["fallback_count"] == 1
    assert status_events == []
    assert token_events == [(result["messages"][0].content, "supervisor")]


def test_handle_streaming_wrapper_exception_plugin_unhealthy_fallback(monkeypatch) -> None:
    """插件链路异常时应走核心能力降级路径并返回可见 token。"""
    monkeypatch.setenv("ENABLE_RUNTIME_RECOVERY", "true")
    monkeypatch.setenv("ENABLE_PLUGIN_REGISTRY", "true")

    status_events = []
    token_events = []
    ctx = _make_ctx(
        writer=status_events.append,
        node_name="data_expert",
        state={
            "messages": [HumanMessage(content="帮我查下贷款余额")],
            "runtime_recovery_state": {
                "plugin_lifecycle_status": "unhealthy",
                "fallback_route": "none",
                "recovery_metrics": {"recovery_attempts": 0, "fallback_count": 0},
            },
        },
    )

    with patch("app.ai.workflow.multi_agent_graph.emit_status", side_effect=lambda writer, message, node: writer((message, node))), \
         patch("app.ai.workflow.multi_agent_graph.emit_token", side_effect=lambda _w, content, node: token_events.append((content, node))):
        result = _handle_streaming_wrapper_exception(
            error_text="Plugin registry load failed: timeout",
            ctx=ctx,
        )

    assert len(result["messages"]) == 1
    assert result["messages"][0].content == "插件能力暂不可用，已自动降级为核心能力回答。"
    assert result["runtime_recovery_state"]["fallback_route"] == "core_tools_only"
    assert result["runtime_recovery_state"]["plugin_lifecycle_status"] == "unhealthy"
    assert result["runtime_recovery_state"]["recovery_metrics"]["recovery_attempts"] == 1
    assert result["runtime_recovery_state"]["recovery_metrics"]["fallback_count"] == 1
    assert token_events == [("插件能力暂不可用，已自动降级为核心能力回答。", "data_expert")]
    assert status_events


def test_fallback_router_respects_runtime_recovery_flag(monkeypatch) -> None:
    """关闭运行时恢复开关后，应回退到友好错误路径。"""
    monkeypatch.setenv("ENABLE_RUNTIME_RECOVERY", "false")
    monkeypatch.delenv("ENABLE_PLUGIN_REGISTRY", raising=False)

    route_decision = fallback_router(
        node_name="supervisor",
        state={"messages": [HumanMessage(content="请查看我的待办")]},
        error_text="Error Code: 403, subscription_not_found",
    )

    assert route_decision["route"] == "friendly_error"
    assert route_decision["runtime_recovery_state"]["fallback_route"] == "recovery_disabled"
    assert "模型服务" in route_decision["message"]


def test_degrade_on_plugin_failure_fallback_enabled(monkeypatch) -> None:
    """开启插件注册表且命中插件异常时，应返回降级文案。"""
    monkeypatch.setenv("ENABLE_RUNTIME_RECOVERY", "true")
    monkeypatch.setenv("ENABLE_PLUGIN_REGISTRY", "true")

    fallback_message = degrade_on_plugin_failure("plugin registry init failed")

    assert fallback_message is not None
    assert "核心能力" in fallback_message


def test_degrade_on_plugin_failure_fallback_disabled(monkeypatch) -> None:
    """关闭插件注册表开关时，不应触发插件降级文案。"""
    monkeypatch.setenv("ENABLE_RUNTIME_RECOVERY", "true")
    monkeypatch.setenv("ENABLE_PLUGIN_REGISTRY", "false")

    fallback_message = degrade_on_plugin_failure("plugin registry init failed")

    assert fallback_message is None


@pytest.mark.asyncio
async def test_execute_streaming_wrapper_returns_delta_messages() -> None:
    """执行器应返回增量消息，并保留 values 模式补发行为。"""

    class _FakeAgent:
        async def aget_state(self, _config):
            return None

        async def astream(self, pruned_state, _config, stream_mode):
            assert stream_mode == ["messages", "values", "custom"]
            yield (
                "values",
                {
                    "messages": list(pruned_state.get("messages", []))
                    + [AIMessage(content="execute-token", id="exec-1")]
                },
            )

    token_events = []

    with patch("app.ai.workflow.multi_agent_graph.AgentOutputParser") as mock_parser, \
         patch("app.ai.workflow.multi_agent_graph.emit_token", side_effect=lambda _w, content, node: token_events.append((content, node))):
        mock_parser.should_filter_content.return_value = False
        mock_parser.parse_kb_images.return_value = {}
        mock_parser.extract_all_handoffs_from_messages.return_value = []

        result = await _execute_streaming_wrapper(
            agent=_FakeAgent(),
            node_name="todo_expert",
            state={"messages": [HumanMessage(content="继续")], "thread_id": "thread-1"},
            config=SimpleNamespace(),
            writer=SimpleNamespace(),
        )

    assert len(result.get("messages", [])) == 1
    assert result["messages"][0].content == "execute-token"
    assert token_events == [("execute-token", "todo_expert")]


@pytest.mark.asyncio
async def test_create_streaming_agent_wrapper_uses_module_stream_writer(monkeypatch) -> None:
    """模块级 wrapper 工厂应通过 get_stream_writer 输出事件。"""
    writer_events = []

    class _FakeAgent:
        async def aget_state(self, _config):
            return None

        async def astream(self, pruned_state, _config, stream_mode):
            assert stream_mode == ["messages", "values", "custom"]
            yield (
                "values",
                {
                    "messages": list(pruned_state.get("messages", []))
                    + [AIMessage(content="wrapper-token", id="wrap-1")]
                },
            )

    from app.ai.workflow import multi_agent_graph

    monkeypatch.setattr(multi_agent_graph, "get_stream_writer", lambda: writer_events.append)
    wrapper = _create_streaming_agent_wrapper(_FakeAgent(), "todo_expert")

    result = await wrapper(
        {"messages": [HumanMessage(content="测试")], "thread_id": "thread-1"},
        SimpleNamespace(),
    )

    assert len(result.get("messages", [])) == 1
    assert result["messages"][0].content == "wrapper-token"
    assert writer_events


def test_config_resolver_tool_governance_settings_enables_evidence_gate(monkeypatch) -> None:
    """执行型任务且要求证据时，应启用 evidence gate。"""

    monkeypatch.setattr(SystemConfigService, "_initialized", True)
    monkeypatch.setattr(
        SystemConfigService,
        "_cache",
        {
            TOOL_POLICY_CONTRACT.enabled_key: True,
            TOOL_POLICY_CONTRACT.fail_mode_key: "minimal",
            TOOL_POLICY_CONTRACT.task_mode_key: "implementation-card",
            TOOL_POLICY_CONTRACT.requires_evidence_key: True,
        },
    )

    settings = ConfigResolver.get_tool_governance_settings()
    chat_mode_settings = ConfigResolver.get_tool_governance_settings(
        task_mode="chat",
        requires_evidence=True,
    )

    assert settings == {
        "enabled": True,
        "fail_mode": "minimal",
        "task_mode": "implementation-card",
        "requires_evidence": True,
        "evidence_gate_enabled": True,
    }
    assert chat_mode_settings["evidence_gate_enabled"] is False


def test_config_resolver_tool_policy_layers_merge_global_and_agent(monkeypatch) -> None:
    """全局策略与 Agent 策略应按契约合并。"""

    global_policy = {
        "allow": ["group:file", "knowledge_search"],
        "deny": ["group:web"],
        "meta": {"source": "global", "priority": 1},
    }
    supervisor_policy = {
        "allow": ["knowledge_search", "fig_inter"],
        "deny": ["read"],
        "meta": {"priority": 2, "agent": "supervisor"},
    }
    monkeypatch.setattr(SystemConfigService, "_initialized", True)
    monkeypatch.setattr(
        SystemConfigService,
        "_cache",
        {
            TOOL_POLICY_CONTRACT.global_policy_key: global_policy,
            TOOL_POLICY_CONTRACT.agent_policy_key("supervisor"): supervisor_policy,
        },
    )

    layers = ConfigResolver.get_tool_policy_layers("supervisor")

    assert layers["global_policy"] == global_policy
    assert layers["agent_policy"] == supervisor_policy
    assert layers["merged_policy"] == {
        "allow": ["group:file", "knowledge_search", "fig_inter"],
        "deny": ["group:web", "read"],
        "meta": {"source": "global", "priority": 2, "agent": "supervisor"},
    }
    assert layers["agent_policy_key"] == TOOL_POLICY_CONTRACT.agent_policy_key("supervisor")
