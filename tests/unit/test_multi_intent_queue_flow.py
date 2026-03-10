"""复合任务串行队列回归测试。"""

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from app.ai.contracts.delivery_contract_validators import validate_coverage_report_contract
from app.ai.state import AgentType
from app.ai.workflow.multi_agent_graph import (
    _build_delivery_artifacts,
    _build_multi_intent_summary_content,
    _compute_coverage_report,
    _evaluate_handoff_progress,
    _render_coverage_blocked_message,
    _render_final_answer,
    _resolve_coverage_gate_route,
)


def test_evaluate_handoff_progress_consumes_queue_before_complete() -> None:
    """有 handoff_queue 时必须继续执行下一个专家，而不是提前 complete。"""
    state = {
        "messages": [
            HumanMessage(content="嘉兴天气、网银功能、并创建待办"),
            AIMessage(content="天气已查询，准备继续处理。"),
        ],
        "pending_handoff": {
            "target_agent": AgentType.DATA,
            "task_description": "查询企业网银当前功能",
        },
        "handoff_queue": [
            {
                "target_agent": AgentType.TODO,
                "task_description": "创建待办：整理网银功能清单",
            }
        ],
        "completed_handoffs": [],
        "handoff_execution_trace": [],
        "multi_intent_mode": True,
        "iteration_count": 0,
    }

    decision = _evaluate_handoff_progress(state)

    assert decision["evaluation"] == "continue"
    assert decision["evaluation_route"] == "todo_expert"
    assert decision["pending_handoff"]["target_agent"] == AgentType.TODO
    assert decision["handoff_queue"] == []
    assert len(decision["completed_handoffs"]) == 1
    assert len(decision["handoff_execution_trace"]) == 1


def test_evaluate_handoff_progress_enters_coverage_gate_after_last_handoff() -> None:
    """复合任务最后一个专家完成后应先进入 coverage_gate，而不是直接 postprocess。"""
    state = {
        "messages": [
            HumanMessage(content="嘉兴天气、网银功能、并创建待办"),
            AIMessage(content="待办已创建：本周五17:00提交网银功能汇总。"),
        ],
        "pending_handoff": {
            "target_agent": AgentType.TODO,
            "task_description": "创建待办：提交网银功能汇总",
        },
        "handoff_queue": [],
        "completed_handoffs": [
            {
                "target_agent": AgentType.DATA,
                "task_description": "查询网银功能",
            }
        ],
        "handoff_execution_trace": [
            {
                "target_agent": AgentType.DATA,
                "task_description": "查询网银功能",
                "result_excerpt": "已返回企业网银功能列表",
            }
        ],
        "multi_intent_mode": True,
        "iteration_count": 1,
    }

    decision = _evaluate_handoff_progress(state)

    assert decision["evaluation"] == "coverage"
    assert decision["evaluation_route"] == "coverage_gate"
    assert decision["pending_handoff"] is None
    assert len(decision["handoff_execution_trace"]) == 2


def test_evaluate_handoff_progress_routes_direct_plus_single_expert_to_coverage() -> None:
    """direct tool + 1 个专家也应进入 coverage_gate，避免直接结束丢失完整性校验。"""
    state = {
        "messages": [
            HumanMessage(content="嘉兴天气并创建待办"),
            ToolMessage(
                content='{"answer":"嘉兴今天多云，气温 18-24 摄氏度"}',
                tool_call_id="t1",
                name="tavily_search",
            ),
            AIMessage(content="待办已创建：明天 10:00 跟进天气变化。"),
        ],
        "pending_handoff": {
            "target_agent": AgentType.TODO,
            "task_description": "创建待办：跟进嘉兴天气变化",
        },
        "handoff_queue": [],
        "completed_handoffs": [],
        "handoff_execution_trace": [],
        "multi_intent_mode": True,
        "iteration_count": 0,
    }

    decision = _evaluate_handoff_progress(state)

    assert decision["evaluation"] == "coverage"
    assert decision["evaluation_route"] == "coverage_gate"
    assert decision["pending_handoff"] is None
    assert len(decision["handoff_execution_trace"]) == 1


def test_evaluate_handoff_progress_enters_coverage_gate_when_coverage_missing() -> None:
    """复合任务存在未完成目标时，应统一进入 coverage_gate 决策下一跳。"""
    state = {
        "messages": [
            HumanMessage(content="先查待办 + 再看天气"),
            AIMessage(content="查到 1 条待办：提交周报"),
        ],
        "pending_handoff": {
            "target_agent": AgentType.TODO,
            "task_description": "查询待办",
        },
        "handoff_queue": [],
        "completed_handoffs": [],
        "handoff_execution_trace": [],
        "multi_intent_mode": True,
        "iteration_count": 0,
        "system_context": "当前时间: 2026-02-27 20:00:00 (Friday)",
        "decomposed_goals": [
            {"goal_id": "GOAL-01", "order": 1, "kind": "todo.query", "title": "待办事项", "must_answer": True},
            {"goal_id": "GOAL-02", "order": 2, "kind": "external.lookup", "title": "外部信息", "must_answer": True},
        ],
    }

    decision = _evaluate_handoff_progress(state)

    assert decision["evaluation"] == "coverage"
    assert decision["evaluation_route"] == "coverage_gate"
    assert decision["pending_handoff"] is None
    assert decision["handoff_queue"] == []
    assert "iteration_count" not in decision
    assert decision["coverage_report"]["pass"] is False
    assert decision["delivery_meta"]["pending_goal_titles"] == ["外部信息"]


def test_build_multi_intent_summary_content_contains_direct_and_expert_results() -> None:
    """统一汇总应覆盖 direct tool 与专家执行结果，并隐藏内部术语。"""
    state = {
        "messages": [
            ToolMessage(
                content='{"answer":"嘉兴今天多云，气温 18-24 摄氏度"}',
                tool_call_id="t1",
                name="tavily_search",
            ),
            ToolMessage(
                content="企业网银目前支持账户管理、转账、批量代发等功能。",
                tool_call_id="t2",
                name="knowledge_search",
            ),
        ],
        "handoff_execution_trace": [
            {
                "target_agent": AgentType.DATA,
                "task_description": "确认企业网银功能",
                "result_excerpt": "已确认三项核心功能",
            },
            {
                "target_agent": AgentType.TODO,
                "task_description": "创建待办：周五17:00输出汇总",
                "result_excerpt": "待办已创建成功",
            },
        ],
    }

    summary = _build_multi_intent_summary_content(state)

    assert "外部信息" in summary
    assert "待办事项" in summary
    assert "待办已创建成功" in summary
    assert "data_expert" not in summary
    assert "todo_expert" not in summary
    assert "handoff" not in summary.lower()


def test_build_delivery_artifacts_includes_supervisor_excerpt_when_handoff_exists() -> None:
    """存在 handoff 时，仍应保留 Supervisor 已完成的可见回答摘要。"""
    state = {
        "messages": [HumanMessage(content="先回答预算，再查待办")],
        "handoff_execution_trace": [
            {
                "goal_id": "GOAL-02",
                "target_agent": AgentType.TODO,
                "task_description": "查询待办",
                "supervisor_excerpt": "预算控制建议：先核对本月支出上限。",
                "result_excerpt": "查到 1 条待办",
            }
        ],
    }

    deliverables = _build_delivery_artifacts(state)
    general_deliverables = [item for item in deliverables if item.get("kind") == "general.reply"]

    assert general_deliverables
    assert "预算控制建议" in str(general_deliverables[0].get("summary") or "")


def test_build_multi_intent_summary_content_respects_user_question_order() -> None:
    """最终汇总应优先按用户提问顺序组织答案，而不是执行顺序。"""
    state = {
        "messages": [
            HumanMessage(content="先帮我看看嘉兴天气，再查一下我的待办"),
            ToolMessage(
                content='{"answer":"嘉兴今天多云，18-24℃"}',
                tool_call_id="t1",
                name="tavily_search",
            ),
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
                "target_agent": AgentType.TODO,
                "task_description": "查询待办",
                "result_excerpt": "查到 1 条待办",
            }
        ],
    }

    summary = _build_multi_intent_summary_content(state)
    first_line = summary.splitlines()[1]
    second_line = summary.splitlines()[2]

    assert "外部信息" in first_line
    assert "待办事项" in second_line


def test_resolve_coverage_gate_route_returns_supervisor_when_missing_goals() -> None:
    """coverage 未通过时应先回到 supervisor 继续补齐。"""
    route = _resolve_coverage_gate_route(
        state={"coverage_retry_count": 0},
        coverage_report={
            "pass": False,
            "missing_goals": [{"goal_id": "GOAL-02", "title": "外部信息", "reason": "missing_deliverable"}],
        },
    )

    assert route["route"] == "supervisor"
    assert route["coverage_retry_count"] == 1
    assert route["retry_exhausted"] is False


def test_resolve_coverage_gate_route_allows_partial_gap_for_subagent_only_missing() -> None:
    """仅专家目标缺失时，应允许直接进入 final_composer（A1 策略）。"""
    active_goals = [
        {
            "goal_id": "GOAL-01",
            "order": 1,
            "kind": "general.reply",
            "title": "问题回复",
            "must_answer": True,
            "allowed_agents": [],
        },
        {
            "goal_id": "GOAL-02",
            "order": 2,
            "kind": "todo.query",
            "title": "待办事项",
            "must_answer": True,
            "allowed_agents": [AgentType.TODO],
        },
    ]
    route = _resolve_coverage_gate_route(
        state={"coverage_retry_count": 0},
        active_goals=active_goals,
        coverage_report={
            "pass": False,
            "missing_goals": [{"goal_id": "GOAL-02", "title": "待办事项", "reason": "missing_deliverable"}],
        },
    )

    assert route["route"] == "final_composer"
    assert route["partial_gap_allowed"] is True
    assert route["coverage_retry_count"] == 0


def test_resolve_coverage_gate_route_enters_postprocess_after_retry_exhausted(monkeypatch) -> None:
    """补齐轮次超过上限后应转入 postprocess 输出缺口说明。"""
    monkeypatch.setenv("COVERAGE_GATE_MAX_RETRIES", "1")

    route = _resolve_coverage_gate_route(
        state={"coverage_retry_count": 1},
        coverage_report={
            "pass": False,
            "missing_goals": [{"goal_id": "GOAL-02", "title": "外部信息", "reason": "missing_deliverable"}],
        },
    )

    assert route["route"] == "postprocess"
    assert route["coverage_retry_count"] == 2
    assert route["retry_exhausted"] is True


def test_resolve_coverage_gate_route_goes_final_when_passed() -> None:
    """coverage 通过时应进入 final_composer。"""
    route = _resolve_coverage_gate_route(
        state={"coverage_retry_count": 2},
        coverage_report={"pass": True, "missing_goals": []},
    )

    assert route["route"] == "final_composer"
    assert route["coverage_retry_count"] == 0


def test_compute_coverage_report_should_fill_goal_id_for_direct_deliverable() -> None:
    """direct tool 交付物未显式携带 goal_id 时，coverage 输出仍应满足合同。"""
    active_goals = [
        {"goal_id": "GOAL-01", "order": 1, "kind": "todo.query", "title": "待办事项", "must_answer": True},
        {"goal_id": "GOAL-02", "order": 2, "kind": "external.lookup", "title": "外部信息", "must_answer": True},
    ]
    deliverables = [
        {
            "kind": "external.lookup",
            "status": "success",
            "summary": "嘉兴今天多云，18-24℃",
            "payload": {"findings": [{"label": "天气", "summary": "多云"}]},
        },
        {
            "goal_id": "GOAL-01",
            "kind": "todo.query",
            "status": "success",
            "summary": "查到 1 条待办",
            "payload": {"todos": [{"title": "提交周报"}]},
        },
    ]

    report = _compute_coverage_report(active_goals, deliverables)
    normalized, valid, error = validate_coverage_report_contract(report)

    assert report["pass"] is True
    assert valid is True
    assert error == ""
    assert normalized["goal_results"]["GOAL-02"]["goal_id"] == "GOAL-02"


def test_render_coverage_blocked_message_should_not_prompt_user_to_continue() -> None:
    """coverage 缺口属于内部补齐失败，不应再要求用户回复“继续”。"""
    active_goals = [
        {"goal_id": "GOAL-01", "order": 1, "kind": "todo.query", "title": "待办事项", "must_answer": True},
        {"goal_id": "GOAL-02", "order": 2, "kind": "external.lookup", "title": "外部信息", "must_answer": True},
    ]
    coverage_report = {
        "pass": False,
        "missing_goals": [
            {"goal_id": "GOAL-02", "title": "外部信息", "reason": "missing_deliverable"},
        ],
    }

    message = _render_coverage_blocked_message(active_goals, coverage_report)

    assert "- 外部信息" in message
    assert "继续补齐" not in message
    assert "你回复“继续”即可" not in message
    assert "请稍后重试" in message


def test_render_final_answer_should_not_invite_user_to_continue_when_missing_goals() -> None:
    """partial gap 收口时可以提示重试，但不应邀请用户继续内部补齐。"""
    active_goals = [
        {"goal_id": "GOAL-01", "order": 1, "kind": "data.query", "title": "数据查询", "must_answer": True},
    ]
    coverage_report = {
        "pass": False,
        "missing_goals": [
            {"goal_id": "GOAL-01", "title": "数据查询", "reason": "missing_deliverable"},
        ],
        "goal_results": {},
    }

    answer = _render_final_answer(active_goals, coverage_report)

    assert "数据查询：暂未完成，缺少可用结果。" in answer
    assert "如果你愿意，我可以继续补齐" not in answer
    assert "请稍后重试" in answer
