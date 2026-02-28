"""复合任务串行队列回归测试。"""

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from app.ai.state import AgentType
from app.ai.workflow.multi_agent_graph import (
    _build_multi_intent_summary_content,
    _evaluate_handoff_progress,
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


def test_evaluate_handoff_progress_returns_supervisor_when_coverage_missing() -> None:
    """复合任务存在未完成目标时，应回到 supervisor 补齐而不是直接结束。"""
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
        "intent_plan": {
            "goals": [
                {"goal_id": "GOAL-01", "order": 1, "kind": "todo.query", "title": "待办事项", "must_answer": True},
                {"goal_id": "GOAL-02", "order": 2, "kind": "external.lookup", "title": "外部信息", "must_answer": True},
            ]
        },
    }

    decision = _evaluate_handoff_progress(state)

    assert decision["evaluation"] == "continue"
    assert decision["evaluation_route"] == "supervisor"
    assert decision["pending_handoff"] is None
    assert decision["handoff_queue"] == []
    assert decision["iteration_count"] == 1
    assert decision["delivery_meta"]["pending_goal_titles"] == ["外部信息"]
    assert "【交付补齐提示】" in decision["system_context"]
    assert "tavily_search" in decision["system_context"]


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
