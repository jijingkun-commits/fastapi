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


def test_evaluate_handoff_progress_enters_summarize_after_last_handoff() -> None:
    """复合任务最后一个专家完成后应进入 summarize，而不是直接 postprocess。"""
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

    assert decision["evaluation"] == "summarize"
    assert decision["evaluation_route"] == "summarize"
    assert decision["pending_handoff"] is None
    assert len(decision["handoff_execution_trace"]) == 2


def test_build_multi_intent_summary_content_contains_direct_and_expert_results() -> None:
    """统一汇总应覆盖 direct tool 与专家执行结果。"""
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

    assert "天气/实时信息" in summary
    assert "知识库检索" in summary
    assert "数据专家" in summary
    assert "待办专家" in summary
    assert "待办已创建成功" in summary
