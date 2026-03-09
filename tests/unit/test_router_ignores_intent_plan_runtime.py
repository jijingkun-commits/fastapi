"""运行态契约回归：禁止读取 intent_plan + canonical router_result_v2。"""

from unittest.mock import patch

from langchain_core.messages import HumanMessage, ToolMessage

from app.ai.workflow.multi_agent_graph import (
    StreamingContext,
    _apply_router_contract_guard,
    _dispatch_values_mode_chunk,
    _resolve_handoff_display_text,
)


def _make_ctx(state: dict) -> StreamingContext:
    return StreamingContext(
        writer=lambda _event: None,
        node_name="supervisor",
        state=state,
        collected_content=[],
        kb_images={},
        emitted_message_ids=set(),
        sent_tool_call_ids=set(),
    )


def test_apply_router_contract_guard_ignores_intent_plan_runtime_input() -> None:
    """运行态缺少 decomposed_goals 时，不应回退读取 intent_plan。"""
    handoffs = [{"target_agent": "todo_expert", "task_description": "查询待办"}]
    state = {
        "intent_plan": {
            "goals": [
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
    }

    accepted, blocked, pending = _apply_router_contract_guard(handoffs, state=state)

    assert accepted == []
    assert len(blocked) == 1
    assert blocked[0]["reason"] == "no_pending_goal"
    assert pending == []


def test_apply_router_contract_guard_blocks_invalid_task_description() -> None:
    """handoff 缺失 task_description 时应直接阻塞。"""
    handoffs = [{"target_agent": "todo_expert", "task_description": "   "}]
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

    assert accepted == []
    assert len(blocked) == 1
    assert blocked[0]["reason"] == "invalid_task_description"
    assert pending and pending[0]["goal_id"] == "GOAL-01"


def test_dispatch_values_mode_chunk_fail_fast_when_legacy_router_field_detected() -> None:
    """检测到旧字段时应 fail-fast 并写入 router_result_v2。"""
    ctx = _make_ctx(
        {
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
            "route_decisions": [],
        }
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
                "task_description": "查询待办",
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
    assert final_state["router_result_v2"]["event"] == "intent_router_legacy_field_detected"
    assert final_state["router_result_v2"]["reason"] == "legacy_field_detected"
    assert final_state["router_result_v2"]["router_contract_blocked_count"] == 1


def test_apply_router_contract_guard_blocks_data_query_without_query_text() -> None:
    """data.query handoff 缺失结构化 query_text 时应在 router_guard 阻断。"""
    handoffs = [{
        "target_agent": "data_expert",
        "frame": {"metric": "贷款余额", "query_shape": "top_n", "ranking": {"limit": 10}},
    }]
    state = {
        "decomposed_goals": [
            {
                "goal_id": "GOAL-01",
                "order": 1,
                "kind": "data.query",
                "title": "数据查询",
                "must_answer": True,
                "allowed_agents": ["data_expert"],
            }
        ]
    }

    accepted, blocked, pending = _apply_router_contract_guard(handoffs, state=state)

    assert accepted == []
    assert len(blocked) == 1
    assert blocked[0]["reason"] == "invalid_data_query_contract"
    assert pending and pending[0]["goal_id"] == "GOAL-01"


def test_apply_router_contract_guard_blocks_data_query_with_sql_like_query_text() -> None:
    """data.query 的 frame.query_text 若被写成 SQL，应在 router_guard 阻断。"""
    handoffs = [{
        "target_agent": "data_expert",
        "frame": {
            "query_text": "SELECT cust_no, cust_name FROM loan_table ORDER BY loan_balance DESC LIMIT 10",
            "metric": "贷款余额",
            "time_range": "2025-06-30",
            "dimensions": ["客户"],
            "query_shape": "top_n",
            "ranking": {"limit": 10},
        },
    }]
    state = {
        "decomposed_goals": [
            {
                "goal_id": "GOAL-01",
                "order": 1,
                "kind": "data.query",
                "title": "数据查询",
                "must_answer": True,
                "allowed_agents": ["data_expert"],
            }
        ]
    }

    accepted, blocked, pending = _apply_router_contract_guard(handoffs, state=state)

    assert accepted == []
    assert len(blocked) == 1
    assert blocked[0]["reason"] == "invalid_data_query_contract"
    assert blocked[0]["contract_error"] == "query_text_sql_like"
    assert pending and pending[0]["goal_id"] == "GOAL-01"



def test_resolve_handoff_display_text_prefers_frame_for_data_query() -> None:
    """data.query 展示摘要只允许读取 frame.query_text，不回退 task_description。"""
    text = _resolve_handoff_display_text(
        {
            "target_agent": "data_expert",
            "task_description": "旧字段：请查询整句复合问题",
            "frame": {"query_text": "查询 2025-06-30 贷款余额前 10 名客户"},
        }
    )

    assert text == "查询 2025-06-30 贷款余额前 10 名客户"
