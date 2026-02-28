"""运行时证据对账与覆盖率收敛测试。"""

from langchain_core.messages import AIMessage, HumanMessage

from app.ai.state import AgentType
from app.ai.workflow.multi_agent_graph import (
    _build_delivery_artifacts,
    _compute_coverage_report,
    _resolve_coverage_gate_route,
)


def _intent_plan_todo_only() -> dict:
    return {
        "goals": [
            {
                "goal_id": "GOAL-01",
                "order": 1,
                "kind": "todo.query",
                "title": "待办事项",
                "must_answer": True,
            }
        ]
    }


def test_coverage_reconcile_marks_missing_goal_without_runtime_evidence() -> None:
    """缺少运行时证据时，coverage 必须判定未覆盖。"""
    state = {
        "messages": [
            HumanMessage(content="帮我看看待办"),
            AIMessage(content="我去查询一下"),
        ],
        "handoff_execution_trace": [
            {
                "goal_id": "GOAL-01",
                "target_agent": AgentType.TODO,
                "task_description": "查询待办",
            }
        ],
    }

    deliverables = _build_delivery_artifacts(state)
    report = _compute_coverage_report(_intent_plan_todo_only(), deliverables)
    route = _resolve_coverage_gate_route(state={"coverage_retry_count": 0}, coverage_report=report)

    assert deliverables[0]["status"] == "pending"
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
        "handoff_execution_trace": [
            {
                "goal_id": "GOAL-01",
                "target_agent": AgentType.TODO,
                "task_description": "查询待办",
            }
        ],
    }

    deliverables = _build_delivery_artifacts(state)
    report = _compute_coverage_report(_intent_plan_todo_only(), deliverables)

    assert deliverables[0]["status"] == "success"
    assert report["pass"] is True
    assert report["missing_goals"] == []


def test_coverage_reconcile_can_be_disabled_by_flag(monkeypatch) -> None:
    """关闭对账开关时回退到 legacy 行为。"""
    monkeypatch.setenv("ENABLE_COVERAGE_RECONCILE", "false")
    state = {
        "messages": [
            HumanMessage(content="帮我看看待办"),
            AIMessage(content="我去查询一下"),
        ],
        "handoff_execution_trace": [
            {
                "goal_id": "GOAL-01",
                "target_agent": AgentType.TODO,
                "task_description": "查询待办",
            }
        ],
    }

    deliverables = _build_delivery_artifacts(state)
    report = _compute_coverage_report(_intent_plan_todo_only(), deliverables)

    assert deliverables[0]["status"] == "success"
    assert report["pass"] is True
