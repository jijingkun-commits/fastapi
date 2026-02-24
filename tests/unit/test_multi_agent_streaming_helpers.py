"""multi_agent_graph streaming helper 回归测试。"""

from types import SimpleNamespace

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from app.ai.protocol import (
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
    _build_streaming_event_emitter_adapter,
    _build_streaming_protocol_adapter,
    _build_streaming_delta_return,
    _create_streaming_agent_wrapper,
    _dispatch_messages_mode_chunk,
    _dispatch_values_mode_chunk,
    _execute_streaming_wrapper,
    _emit_messages_mode_thinking,
    _emit_messages_mode_token,
    _handle_streaming_wrapper_exception,
    _handle_messages_mode_tool_message,
    _inject_streaming_context_messages,
    _prefill_emitted_message_ids,
    _record_emitted_message_id,
    _run_streaming_dispatch_loop,
)


def test_record_emitted_message_id_only_tracks_existing_id() -> None:
    """仅当消息包含 id 时应加入去重集合。"""
    emitted_ids: set[str] = set()

    _record_emitted_message_id(SimpleNamespace(id="msg-1"), emitted_ids)
    _record_emitted_message_id(SimpleNamespace(id=None), emitted_ids)
    _record_emitted_message_id(SimpleNamespace(), emitted_ids)

    assert emitted_ids == {"msg-1"}


def test_build_streaming_protocol_adapter_maps_parser_functions() -> None:
    """协议适配器应暴露 parser 的三类能力函数。"""

    class _FakeParser:
        @staticmethod
        def parse_kb_images(_text: str):
            return {"img": "https://example.com/a.png"}

        @staticmethod
        def should_filter_content(content):
            return content == "internal"

        @staticmethod
        def extract_latest_handoff_from_messages(_messages):
            return {"target_agent": "todo_expert"}

        @staticmethod
        def extract_all_handoffs_from_messages(_messages):
            return [{"target_agent": "todo_expert"}]

    adapter = _build_streaming_protocol_adapter(_FakeParser)

    assert adapter["parse_kb_images"]("x") == {"img": "https://example.com/a.png"}
    assert adapter["should_filter_content"]("internal") is True
    assert adapter["extract_latest_handoff_from_messages"]([])["target_agent"] == "todo_expert"
    assert adapter["extract_all_handoffs_from_messages"]([])[0]["target_agent"] == "todo_expert"


def test_build_streaming_event_emitter_adapter_maps_event_emitters() -> None:
    """事件适配器应暴露统一事件出口。"""
    events = []

    adapter = _build_streaming_event_emitter_adapter(
        emit_token=lambda writer, content, node: writer(("token", content, node)),
        emit_thinking=lambda writer, content, node: writer(("thinking", content, node)),
        emit_tool_start=lambda writer, name, args, node: writer(("tool_start", name, args, node)),
        emit_tool_end=lambda writer, name, output, node: writer(("tool_end", name, output, node)),
        emit_status=lambda writer, message, node: writer(("status", message, node)),
        emit_result=lambda writer, data_type, data, message, node: writer(("result", data_type, data, message, node)),
        emit_kb_images=lambda writer, images, node: writer(("kb_images", images, node)),
    )

    writer = events.append
    adapter["emit_token"](writer, "内容", node="supervisor")
    adapter["emit_thinking"](writer, "思考", node="supervisor")
    adapter["emit_tool_start"](writer, {"name": "search", "input": {"q": "x"}}, node="supervisor")
    adapter["emit_tool_end"](writer, "search", "ok", node="supervisor")
    adapter["emit_status"](writer, message="处理中", node="supervisor")
    adapter["emit_result"](
        writer,
        {"data_type": "table", "data": {"rows": []}, "message": "结果"},
        node="supervisor",
    )
    adapter["emit_kb_images"](writer, {"images": {"img-1": "https://example.com/a.png"}}, node="supervisor")

    assert events == [
        ("token", "内容", "supervisor"),
        ("thinking", "思考", "supervisor"),
        ("tool_start", "search", {"q": "x"}, "supervisor"),
        ("tool_end", "search", "ok", "supervisor"),
        ("status", "处理中", "supervisor"),
        ("result", "table", {"rows": []}, "结果", "supervisor"),
        ("kb_images", {"img-1": "https://example.com/a.png"}, "supervisor"),
    ]


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

    class _FakeParser:
        @staticmethod
        def parse_kb_images(_tool_content: str):
            return {"img-1": "https://example.com/a.png"}

        @staticmethod
        def should_filter_content(_content):
            return False

        @staticmethod
        def extract_latest_handoff_from_messages(_messages):
            return None

        @staticmethod
        def extract_all_handoffs_from_messages(_messages):
            return []

    emitted_events = []

    def _fake_emit_tool_end(writer, tool_name, tool_output, node):
        writer((tool_name, tool_output, node))

    kb_images: dict[str, str] = {}
    writer = emitted_events.append
    message = ToolMessage(content="tool payload", tool_call_id="tc-1", name="knowledge_search")
    protocol_adapter = _build_streaming_protocol_adapter(_FakeParser)
    event_emitter_adapter = _build_streaming_event_emitter_adapter(
        emit_token=lambda *_args, **_kwargs: None,
        emit_thinking=lambda *_args, **_kwargs: None,
        emit_tool_start=lambda *_args, **_kwargs: None,
        emit_tool_end=_fake_emit_tool_end,
        emit_status=lambda *_args, **_kwargs: None,
        emit_result=lambda *_args, **_kwargs: None,
        emit_kb_images=lambda *_args, **_kwargs: None,
    )

    handled = _handle_messages_mode_tool_message(
        message=message,
        protocol_adapter=protocol_adapter,
        kb_images=kb_images,
        event_emitter_adapter=event_emitter_adapter,
        writer=writer,
        node_name="supervisor",
    )

    assert handled is True
    assert kb_images == {"img-1": "https://example.com/a.png"}
    assert emitted_events == [("knowledge_search", "tool payload", "supervisor")]


def test_emit_messages_mode_token_filters_internal_content() -> None:
    """内部协议文本不应向前端发送 token。"""

    class _FakeParser:
        @staticmethod
        def should_filter_content(content):
            return content == "[[internal]]"

        @staticmethod
        def parse_kb_images(_tool_content: str):
            return {}

        @staticmethod
        def extract_latest_handoff_from_messages(_messages):
            return None

        @staticmethod
        def extract_all_handoffs_from_messages(_messages):
            return []

    emitted_tokens = []
    collected_content: list[str] = []
    protocol_adapter = _build_streaming_protocol_adapter(_FakeParser)
    event_emitter_adapter = _build_streaming_event_emitter_adapter(
        emit_token=lambda _writer, content, node: emitted_tokens.append((content, node)),
        emit_thinking=lambda *_args, **_kwargs: None,
        emit_tool_start=lambda *_args, **_kwargs: None,
        emit_tool_end=lambda *_args, **_kwargs: None,
        emit_status=lambda *_args, **_kwargs: None,
        emit_result=lambda *_args, **_kwargs: None,
        emit_kb_images=lambda *_args, **_kwargs: None,
    )

    _emit_messages_mode_token(
        message=SimpleNamespace(content="正常输出"),
        protocol_adapter=protocol_adapter,
        collected_content=collected_content,
        event_emitter_adapter=event_emitter_adapter,
        writer=SimpleNamespace(),
        node_name="todo_expert",
    )
    _emit_messages_mode_token(
        message=SimpleNamespace(content="[[internal]]"),
        protocol_adapter=protocol_adapter,
        collected_content=collected_content,
        event_emitter_adapter=event_emitter_adapter,
        writer=SimpleNamespace(),
        node_name="todo_expert",
    )

    assert collected_content == ["正常输出"]
    assert emitted_tokens == [("正常输出", "todo_expert")]


def test_emit_messages_mode_thinking_prefers_reasoning_content() -> None:
    """思考内容应按 reasoning -> thinking_content -> thinking 顺序输出。"""
    emitted = []
    event_emitter_adapter = _build_streaming_event_emitter_adapter(
        emit_token=lambda *_args, **_kwargs: None,
        emit_thinking=lambda _writer, content, node: emitted.append((content, node)),
        emit_tool_start=lambda *_args, **_kwargs: None,
        emit_tool_end=lambda *_args, **_kwargs: None,
        emit_status=lambda *_args, **_kwargs: None,
        emit_result=lambda *_args, **_kwargs: None,
        emit_kb_images=lambda *_args, **_kwargs: None,
    )

    _emit_messages_mode_thinking(
        message=SimpleNamespace(additional_kwargs={"reasoning_content": "step by step"}),
        event_emitter_adapter=event_emitter_adapter,
        writer=SimpleNamespace(),
        node_name="supervisor",
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

    class _FakeParser:
        @staticmethod
        def should_filter_content(_content):
            return False

        @staticmethod
        def parse_kb_images(_tool_content: str):
            return {}

        @staticmethod
        def extract_latest_handoff_from_messages(_messages):
            return None

        @staticmethod
        def extract_all_handoffs_from_messages(_messages):
            return []

    emitted_ids: set[str] = set()
    collected_content: list[str] = []
    token_events = []
    thinking_events = []
    protocol_adapter = _build_streaming_protocol_adapter(_FakeParser)
    event_emitter_adapter = _build_streaming_event_emitter_adapter(
        emit_token=lambda _writer, content, node: token_events.append((content, node)),
        emit_thinking=lambda _writer, content, node: thinking_events.append((content, node)),
        emit_tool_start=lambda *_args, **_kwargs: None,
        emit_tool_end=lambda *_args, **_kwargs: None,
        emit_status=lambda *_args, **_kwargs: None,
        emit_result=lambda *_args, **_kwargs: None,
        emit_kb_images=lambda *_args, **_kwargs: None,
    )

    message = AIMessage(
        content="这是回答",
        additional_kwargs={"thinking": "这是思考"},
        id="ai-msg-1",
    )

    _dispatch_messages_mode_chunk(
        chunk=(message, {"node": "supervisor"}),
        protocol_adapter=protocol_adapter,
        emitted_message_ids=emitted_ids,
        collected_content=collected_content,
        kb_images={},
        event_emitter_adapter=event_emitter_adapter,
        writer=SimpleNamespace(),
        node_name="supervisor",
        state={"multi_intent_mode": False},
    )

    assert emitted_ids == {"ai-msg-1"}
    assert collected_content == ["这是回答"]
    assert token_events == [("这是回答", "supervisor")]
    assert thinking_events == [("这是思考", "supervisor")]


def test_dispatch_values_mode_chunk_emits_values_text_message() -> None:
    """values dispatcher 应处理新增 AI 消息并补发文本。"""

    class _FakeParser:
        @staticmethod
        def extract_latest_handoff_from_messages(_messages):
            return None

        @staticmethod
        def extract_all_handoffs_from_messages(_messages):
            return []

        @staticmethod
        def parse_kb_images(_tool_content: str):
            return {}

        @staticmethod
        def should_filter_content(_content):
            return False

    emitted_ids: set[str] = set()
    collected_content: list[str] = []
    token_events = []
    protocol_adapter = _build_streaming_protocol_adapter(_FakeParser)
    event_emitter_adapter = _build_streaming_event_emitter_adapter(
        emit_token=lambda _writer, content, node: token_events.append((content, node)),
        emit_thinking=lambda *_args, **_kwargs: None,
        emit_tool_start=lambda *_args, **_kwargs: None,
        emit_tool_end=lambda *_args, **_kwargs: None,
        emit_status=lambda *_args, **_kwargs: None,
        emit_result=lambda *_args, **_kwargs: None,
        emit_kb_images=lambda *_args, **_kwargs: None,
    )

    final_state = {
        "messages": [AIMessage(content="values补发", id="ai-values-1")],
        "thread_id": "thread-1",
    }

    updated_count, handoff_return = _dispatch_values_mode_chunk(
        final_state=final_state,
        protocol_adapter=protocol_adapter,
        state={"messages": [HumanMessage(content="测试")], "thread_id": "thread-1"},
        initial_input_count=0,
        input_message_count=0,
        kb_images={},
        sent_tool_call_ids=set(),
        emitted_message_ids=emitted_ids,
        collected_content=collected_content,
        event_emitter_adapter=event_emitter_adapter,
        writer=SimpleNamespace(),
        node_name="todo_expert",
    )

    assert handoff_return is None
    assert updated_count == 1
    assert collected_content == ["values补发"]
    assert emitted_ids == {"ai-values-1"}
    assert token_events == [("values补发", "todo_expert")]


def test_dispatch_values_mode_chunk_uses_result_emitter_for_structured_payload() -> None:
    """values dispatcher 遇到结构化载荷时应通过 emit_result 发送。"""

    class _FakeParser:
        @staticmethod
        def extract_latest_handoff_from_messages(_messages):
            return None

        @staticmethod
        def extract_all_handoffs_from_messages(_messages):
            return []

        @staticmethod
        def parse_kb_images(_tool_content: str):
            return {}

        @staticmethod
        def should_filter_content(_content):
            return False

    emitted_ids: set[str] = set()
    collected_content: list[str] = []
    token_events = []
    result_events = []
    protocol_adapter = _build_streaming_protocol_adapter(_FakeParser)
    event_emitter_adapter = _build_streaming_event_emitter_adapter(
        emit_token=lambda _writer, content, node: token_events.append((content, node)),
        emit_thinking=lambda *_args, **_kwargs: None,
        emit_tool_start=lambda *_args, **_kwargs: None,
        emit_tool_end=lambda *_args, **_kwargs: None,
        emit_status=lambda *_args, **_kwargs: None,
        emit_result=lambda _writer, data_type, data, message, node: result_events.append((data_type, data, message, node)),
        emit_kb_images=lambda *_args, **_kwargs: None,
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

    updated_count, handoff_return = _dispatch_values_mode_chunk(
        final_state=final_state,
        protocol_adapter=protocol_adapter,
        state={"messages": [HumanMessage(content="测试")], "thread_id": "thread-1"},
        initial_input_count=0,
        input_message_count=0,
        kb_images={},
        sent_tool_call_ids=set(),
        emitted_message_ids=emitted_ids,
        collected_content=collected_content,
        event_emitter_adapter=event_emitter_adapter,
        writer=SimpleNamespace(),
        node_name="todo_expert",
    )

    assert handoff_return is None
    assert updated_count == 1
    assert token_events == []
    assert result_events == [("table", {"rows": [{"id": 1}]}, "结构化结果", "todo_expert")]
    assert collected_content == ["结构化结果"]
    assert emitted_ids == {"ai-values-result-1"}


def test_dispatch_values_mode_chunk_emits_kb_images_from_tool_delta() -> None:
    """values dispatcher 应从增量 ToolMessage 提取并发送 kb_images。"""

    class _FakeParser:
        @staticmethod
        def extract_latest_handoff_from_messages(_messages):
            return None

        @staticmethod
        def extract_all_handoffs_from_messages(_messages):
            return []

        @staticmethod
        def parse_kb_images(_tool_content: str):
            return {"img-1": "https://example.com/kb.png"}

        @staticmethod
        def should_filter_content(_content):
            return False

    kb_images: dict[str, str] = {}
    kb_image_events = []
    protocol_adapter = _build_streaming_protocol_adapter(_FakeParser)
    event_emitter_adapter = _build_streaming_event_emitter_adapter(
        emit_token=lambda *_args, **_kwargs: None,
        emit_thinking=lambda *_args, **_kwargs: None,
        emit_tool_start=lambda *_args, **_kwargs: None,
        emit_tool_end=lambda *_args, **_kwargs: None,
        emit_status=lambda *_args, **_kwargs: None,
        emit_result=lambda *_args, **_kwargs: None,
        emit_kb_images=lambda _writer, images, node: kb_image_events.append((dict(images), node)),
    )

    final_state = {
        "messages": [ToolMessage(content="tool payload", tool_call_id="tc-1", name="knowledge_search")],
        "thread_id": "thread-1",
    }

    updated_count, handoff_return = _dispatch_values_mode_chunk(
        final_state=final_state,
        protocol_adapter=protocol_adapter,
        state={"messages": [HumanMessage(content="测试")], "thread_id": "thread-1"},
        initial_input_count=0,
        input_message_count=1,
        kb_images=kb_images,
        sent_tool_call_ids=set(),
        emitted_message_ids=set(),
        collected_content=[],
        event_emitter_adapter=event_emitter_adapter,
        writer=SimpleNamespace(),
        node_name="todo_expert",
    )

    assert handoff_return is None
    assert updated_count == 1
    assert kb_images == {"img-1": "https://example.com/kb.png"}
    assert kb_image_events == [({"img-1": "https://example.com/kb.png"}, "todo_expert")]


def test_dispatch_values_mode_chunk_builds_handoff_queue_for_multi_intent() -> None:
    """supervisor values 模式应保留 handoff 顺序并构造队列。"""

    class _FakeParser:
        @staticmethod
        def extract_latest_handoff_from_messages(_messages):
            return None

        @staticmethod
        def extract_all_handoffs_from_messages(_messages):
            return [
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

        @staticmethod
        def parse_kb_images(_tool_content: str):
            return {}

        @staticmethod
        def should_filter_content(_content):
            return False

    protocol_adapter = _build_streaming_protocol_adapter(_FakeParser)
    event_emitter_adapter = _build_streaming_event_emitter_adapter(
        emit_token=lambda *_args, **_kwargs: None,
        emit_thinking=lambda *_args, **_kwargs: None,
        emit_tool_start=lambda *_args, **_kwargs: None,
        emit_tool_end=lambda *_args, **_kwargs: None,
        emit_status=lambda *_args, **_kwargs: None,
        emit_result=lambda *_args, **_kwargs: None,
        emit_kb_images=lambda *_args, **_kwargs: None,
    )

    final_state = {
        "messages": [ToolMessage(content="handoff-json", tool_call_id="tc-1", name="assign_to_data_expert")],
        "thread_id": "thread-1",
    }

    updated_count, handoff_return = _dispatch_values_mode_chunk(
        final_state=final_state,
        protocol_adapter=protocol_adapter,
        state={"messages": [HumanMessage(content="复合任务")], "thread_id": "thread-1"},
        initial_input_count=0,
        input_message_count=0,
        kb_images={},
        sent_tool_call_ids=set(),
        emitted_message_ids=set(),
        collected_content=[],
        event_emitter_adapter=event_emitter_adapter,
        writer=SimpleNamespace(),
        node_name="supervisor",
    )

    assert updated_count == 0
    assert handoff_return is not None
    assert handoff_return["pending_handoff"]["target_agent"] == "data_expert"
    assert handoff_return["handoff_queue"][0]["target_agent"] == "todo_expert"
    assert handoff_return["multi_intent_mode"] is True


@pytest.mark.asyncio
async def test_run_streaming_dispatch_loop_routes_messages_and_values() -> None:
    """streaming 分发循环应按 messages/values 顺序处理并返回最终状态。"""

    class _FakeParser:
        @staticmethod
        def extract_latest_handoff_from_messages(_messages):
            return None

        @staticmethod
        def extract_all_handoffs_from_messages(_messages):
            return []

        @staticmethod
        def parse_kb_images(_tool_content: str):
            return {}

        @staticmethod
        def should_filter_content(_content):
            return False

    class _FakeAgent:
        async def astream(self, _pruned_state, _config, stream_mode):
            assert stream_mode == ["messages", "values"]
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
    protocol_adapter = _build_streaming_protocol_adapter(_FakeParser)
    event_emitter_adapter = _build_streaming_event_emitter_adapter(
        emit_token=lambda _writer, content, node: token_events.append((content, node)),
        emit_thinking=lambda _writer, content, node: thinking_events.append((content, node)),
        emit_tool_start=lambda *_args, **_kwargs: None,
        emit_tool_end=lambda *_args, **_kwargs: None,
        emit_status=lambda *_args, **_kwargs: None,
        emit_result=lambda *_args, **_kwargs: None,
        emit_kb_images=lambda *_args, **_kwargs: None,
    )

    final_state, handoff_return = await _run_streaming_dispatch_loop(
        agent=_FakeAgent(),
        pruned_state={"messages": []},
        config=SimpleNamespace(),
        protocol_adapter=protocol_adapter,
        initial_input_count=0,
        input_message_count=0,
        emitted_message_ids=emitted_ids,
        sent_tool_call_ids=sent_tool_call_ids,
        collected_content=collected_content,
        kb_images={},
        state={"messages": [HumanMessage(content="测试消息")]},
        event_emitter_adapter=event_emitter_adapter,
        writer=SimpleNamespace(),
        node_name="supervisor",
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


def test_handle_streaming_wrapper_exception_uses_supervisor_fallback() -> None:
    """supervisor 命中模型权限错误时应优先返回待办兜底 handoff。"""
    status_events = []
    token_events = []
    event_emitter_adapter = _build_streaming_event_emitter_adapter(
        emit_token=lambda _writer, content, node: token_events.append((content, node)),
        emit_thinking=lambda *_args, **_kwargs: None,
        emit_tool_start=lambda *_args, **_kwargs: None,
        emit_tool_end=lambda *_args, **_kwargs: None,
        emit_status=lambda writer, message, node: writer((message, node)),
        emit_result=lambda *_args, **_kwargs: None,
        emit_kb_images=lambda *_args, **_kwargs: None,
    )

    result = _handle_streaming_wrapper_exception(
        node_name="supervisor",
        state={"messages": [HumanMessage(content="请帮我查看待办列表")]},
        error_text="Error Code: 403, subscription_not_found",
        event_emitter_adapter=event_emitter_adapter,
        writer=status_events.append,
    )

    assert result["messages"] == []
    assert result["pending_handoff"]["target_agent"] == "todo_expert"
    assert status_events
    assert token_events == []


@pytest.mark.asyncio
async def test_execute_streaming_wrapper_returns_delta_messages() -> None:
    """执行器应返回增量消息，并保留 values 模式补发行为。"""

    class _FakeAgent:
        async def aget_state(self, _config):
            return None

        async def astream(self, pruned_state, _config, stream_mode):
            assert stream_mode == ["messages", "values"]
            yield (
                "values",
                {
                    "messages": list(pruned_state.get("messages", []))
                    + [AIMessage(content="execute-token", id="exec-1")]
                },
            )

    token_events = []
    event_emitter_adapter = _build_streaming_event_emitter_adapter(
        emit_token=lambda _writer, content, node: token_events.append((content, node)),
        emit_thinking=lambda *_args, **_kwargs: None,
        emit_tool_start=lambda *_args, **_kwargs: None,
        emit_tool_end=lambda *_args, **_kwargs: None,
        emit_status=lambda *_args, **_kwargs: None,
        emit_result=lambda *_args, **_kwargs: None,
        emit_kb_images=lambda *_args, **_kwargs: None,
    )

    result = await _execute_streaming_wrapper(
        agent=_FakeAgent(),
        node_name="todo_expert",
        state={"messages": [HumanMessage(content="继续")], "thread_id": "thread-1"},
        config=SimpleNamespace(),
        event_emitter_adapter=event_emitter_adapter,
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
            assert stream_mode == ["messages", "values"]
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
