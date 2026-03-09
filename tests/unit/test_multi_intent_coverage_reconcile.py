"""运行时证据对账与覆盖率收敛测试。"""

from langchain_core.messages import AIMessage, HumanMessage

from app.ai.state import AgentType
from app.ai.workflow.multi_agent_graph import (
    _build_delivery_artifacts,
    _compute_coverage_report,
    _resolve_coverage_gate_route,
)


def _active_goals_todo_only() -> list[dict]:
    return [
        {
            "goal_id": "GOAL-01",
            "order": 1,
            "kind": "todo.query",
            "title": "待办事项",
            "must_answer": True,
        }
    ]


def _todo_trace() -> list[dict]:
    return [
        {
            "goal_id": "GOAL-01",
            "target_agent": AgentType.TODO,
            "task_description": "查询待办",
        }
    ]


def test_coverage_reconcile_marks_missing_goal_without_runtime_evidence() -> None:
    """缺少运行时证据时，coverage 必须判定未覆盖。"""
    state = {
        "messages": [
            HumanMessage(content="帮我看看待办"),
            AIMessage(content="我去查询一下"),
        ],
        "handoff_execution_trace": _todo_trace(),
    }

    deliverables = _build_delivery_artifacts(state)
    report = _compute_coverage_report(_active_goals_todo_only(), deliverables)
    route = _resolve_coverage_gate_route(state={"coverage_retry_count": 0}, coverage_report=report)

    assert deliverables[0]["status"] == "missing"
    assert report["pass"] is False
    assert report["missing_goals"][0]["goal_id"] == "GOAL-01"
    assert route["route"] == "supervisor"


def test_coverage_reconcile_accepts_todo_structured_result_as_evidence() -> None:
    """有结构化待办结果时应视为有效交付，coverage 通过。"""
    state = {
        "messages": [
            HumanMessage(content="帮我看看待办"),
            AIMessage(
                content="查到 1 条待办",
                additional_kwargs={
                    "data_type": "todo_list",
                    "data": {"todos": [{"title": "提交周报", "status": "todo"}]},
                },
            ),
        ],
        "handoff_execution_trace": _todo_trace(),
    }

    deliverables = _build_delivery_artifacts(state)
    report = _compute_coverage_report(_active_goals_todo_only(), deliverables)

    assert deliverables[0]["status"] == "success"
    assert report["pass"] is True
    assert report["missing_goals"] == []


def test_replay_consistency_test_prefers_canonical_result_events_over_legacy_pair() -> None:
    """存在 canonical result_events 时，必须优先于 legacy data_type/data。"""
    state = {
        "messages": [
            HumanMessage(content="帮我看看待办"),
            AIMessage(
                content="已整理待办",
                additional_kwargs={
                    "data_type": "todo_list",
                    "data": {"todos": [{"title": "legacy", "status": "todo"}]},
                    "result_events": [
                        {
                            "data_type": "todo_list",
                            "data": {"todos": [{"title": "canonical", "status": "done"}]},
                            "message": "canonical-result",
                            "sequence_number": 3,
                        }
                    ],
                },
            ),
        ],
        "handoff_execution_trace": _todo_trace(),
    }

    deliverables = _build_delivery_artifacts(state)
    todo_deliverable = next(item for item in deliverables if item.get("kind") == "todo.query")

    todos = todo_deliverable["payload"]["todos"]
    assert todos[0]["title"] == "canonical"


def test_multi_result_ordering_test_sorts_result_events_by_sequence_number() -> None:
    """result_events 必须按 sequence_number 保序，且取最新事件作为交付依据。"""
    state = {
        "messages": [
            HumanMessage(content="帮我看看待办"),
            AIMessage(
                content="已完成排序",
                additional_kwargs={
                    "result_events": [
                        {
                            "data_type": "todo_list",
                            "data": {"todos": [{"title": "older", "status": "todo"}]},
                            "message": "旧事件",
                            "sequence_number": 10,
                        },
                        {
                            "data_type": "todo_list",
                            "data": {"todos": [{"title": "newer", "status": "done"}]},
                            "message": "新事件",
                            "sequence_number": 12,
                        },
                    ]
                },
            ),
        ],
        "handoff_execution_trace": _todo_trace(),
    }

    deliverables = _build_delivery_artifacts(state)
    todo_deliverable = next(item for item in deliverables if item.get("kind") == "todo.query")

    assert todo_deliverable["summary"] == "新事件"
    assert todo_deliverable["payload"]["todos"][0]["title"] == "newer"


def test_coverage_reconcile_can_be_disabled_by_flag(monkeypatch) -> None:
    """关闭对账开关时回退到 legacy 行为。"""
    monkeypatch.setenv("ENABLE_COVERAGE_RECONCILE", "false")
    state = {
        "messages": [
            HumanMessage(content="帮我看看待办"),
            AIMessage(content="我去查询一下"),
        ],
        "handoff_execution_trace": _todo_trace(),
    }

    deliverables = _build_delivery_artifacts(state)
    report = _compute_coverage_report(_active_goals_todo_only(), deliverables)

    assert deliverables[0]["status"] == "success"
    assert report["pass"] is True
