"""意图分层边界测试。"""

from langchain_core.messages import HumanMessage

import app.ai.workflow.multi_agent_graph as graph
from app.ai.workflow.multi_agent_graph import (
    _build_planner_intent_plan,
    _infer_initial_intent_plan,
    _resolve_active_goals,
)


def test_infer_initial_intent_plan_prefers_semantic_payload_user_query() -> None:
    """语义层 user_query 存在时，应优先作为目标分解输入。"""
    state = {
        "messages": [HumanMessage(content="你好")],
        "semantic_payload": {"user_query": "帮我看下今天待办"},
    }

    plan = _infer_initial_intent_plan(state)

    assert plan["user_query"] == "帮我看下今天待办"
    assert any(goal.get("kind") == "todo.query" for goal in list(plan.get("goals") or []))


def test_build_planner_intent_plan_control_flags_do_not_override_semantic_goal(monkeypatch) -> None:
    """控制面标记不应直接改写语义层目标。"""

    def _raise_if_called(*_args, **_kwargs):
        raise AssertionError("_infer_model_intent_plan should not be called in heuristic_only mode")

    monkeypatch.setattr(graph, "_infer_model_intent_plan", _raise_if_called)

    state = {
        "messages": [HumanMessage(content="只是打个招呼")],
        "control_flags": {"run_control_enabled": True, "has_attachments": False},
        "semantic_payload": {"user_query": "帮我查询今天的待办"},
    }
    plan = _build_planner_intent_plan(state, llm=object(), mode="heuristic_only")

    assert plan["source"] == "heuristic_only"
    assert plan["user_query"] == "帮我查询今天的待办"
    assert any(goal.get("kind") == "todo.query" for goal in list(plan.get("goals") or []))


def test_infer_model_intent_plan_uses_semantic_payload_for_prompt() -> None:
    """模型主判定提示词应使用语义层 user_query。"""

    class _FakeStructuredLLM:
        def __init__(self) -> None:
            self.prompt: str = ""

        def invoke(self, prompt: str) -> dict:
            self.prompt = prompt
            return {"goals": [{"kind": "general.reply"}]}

    class _FakeLLM:
        def __init__(self) -> None:
            self.structured = _FakeStructuredLLM()

        def with_structured_output(self, _schema):
            return self.structured

    llm = _FakeLLM()
    state = {
        "messages": [HumanMessage(content="你好")],
        "semantic_payload": {"user_query": "请帮我看看天气"},
    }

    plan = graph._infer_model_intent_plan(state, llm)

    assert "请帮我看看天气" in llm.structured.prompt
    assert "严格 JSON 对象" in llm.structured.prompt
    assert plan["user_query"] == "请帮我看看天气"



def test_resolve_active_goals_prefers_decomposed_goals_over_intent_plan() -> None:
    """运行态目标只允许来自 decomposed_goals。"""
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
        ],
        "intent_plan": {
            "goals": [
                {
                    "goal_id": "GOAL-X",
                    "order": 1,
                    "kind": "data.query",
                    "title": "数据查询",
                    "must_answer": True,
                    "allowed_agents": ["data_expert"],
                }
            ]
        },
    }

    goals = _resolve_active_goals(state)

    assert len(goals) == 1
    assert goals[0]["kind"] == "todo.query"
    assert goals[0]["goal_id"] == "GOAL-01"


def test_resolve_active_goals_returns_empty_when_runtime_contract_missing() -> None:
    """运行态缺少 decomposed_goals 时不应回退读取 intent_plan。"""
    state = {
        "intent_plan": {
            "goals": [
                {
                    "goal_id": "GOAL-X",
                    "kind": "todo.query",
                    "must_answer": True,
                }
            ]
        }
    }

    assert _resolve_active_goals(state) == []
