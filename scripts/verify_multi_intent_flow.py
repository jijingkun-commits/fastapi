"""复合任务串行执行最小回归脚本。

用例：天气 + 网银功能 + 待办创建
目标：验证 handoff_queue 会被串行消费，不会在第一位专家后提前 complete。
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from app.ai.state import AgentType
from app.ai.workflow.multi_agent_graph import (
    _build_multi_intent_summary_content,
    _evaluate_handoff_progress,
)


def _print_step(title: str) -> None:
    print(f"\n=== {title} ===")


def main() -> int:
    # Step 0: supervisor 已拆分出两个专家任务
    state = {
        "messages": [
            HumanMessage(content="1.嘉兴今天天气怎么样 2.企业网银有哪些功能 3.创建待办:周五17:00输出汇总"),
            ToolMessage(
                content='{"answer":"嘉兴今天多云，气温18-24摄氏度"}',
                tool_call_id="t1",
                name="tavily_search",
            ),
            ToolMessage(
                content="企业网银目前支持账户管理、转账汇款、批量代发等功能。",
                tool_call_id="t2",
                name="knowledge_search",
            ),
            AIMessage(content="数据专家已返回网银功能清单。"),
        ],
        "pending_handoff": {
            "target_agent": AgentType.DATA,
            "task_description": "确认企业网银当前功能清单",
        },
        "handoff_queue": [
            {
                "target_agent": AgentType.TODO,
                "task_description": "创建待办：周五17:00整理并提交网银功能汇总",
            }
        ],
        "completed_handoffs": [],
        "handoff_execution_trace": [],
        "multi_intent_mode": True,
        "iteration_count": 0,
    }

    _print_step("Step 1: data_expert 完成后评估")
    decision_1 = _evaluate_handoff_progress(state)
    print("evaluation:", decision_1["evaluation"])
    print("evaluation_route:", decision_1["evaluation_route"])
    print("next_handoff:", decision_1.get("pending_handoff", {}).get("target_agent"))
    print("queue_left:", len(decision_1.get("handoff_queue") or []))

    if decision_1.get("evaluation_route") != "todo_expert":
        print("ERROR: 第一步没有继续到 todo_expert，存在提前 complete 风险")
        return 1

    # Step 2: todo_expert 执行完成，再次进入 evaluate
    state_after_todo = {
        **state,
        **decision_1,
        "messages": [
            *state["messages"],
            AIMessage(content="待办已创建：周五17:00输出企业网银功能汇总。"),
        ],
    }

    _print_step("Step 2: todo_expert 完成后评估")
    decision_2 = _evaluate_handoff_progress(state_after_todo)
    print("evaluation:", decision_2["evaluation"])
    print("evaluation_route:", decision_2["evaluation_route"])
    print("trace_count:", len(decision_2.get("handoff_execution_trace") or []))

    if decision_2.get("evaluation_route") != "summarize":
        print("ERROR: 第二步没有进入 summarize")
        return 1

    # Step 3: 统一汇总
    summary_state = {
        **state_after_todo,
        **decision_2,
    }

    _print_step("Step 3: 最终统一汇总")
    summary = _build_multi_intent_summary_content(summary_state)
    print(summary)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
