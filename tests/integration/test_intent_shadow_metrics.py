"""C05: 意图灰度指标与回滚开关集成测试。"""

from langchain_core.messages import HumanMessage

import app.ai.workflow.multi_agent_graph as graph
from app.ai.workflow.multi_agent_graph import _build_planner_intent_plan as _build_intent_plan
from app.services.config_resolver import ConfigResolver
from app.services.system_config_service import SystemConfigService


def test_intent_shadow_settings_supports_heuristic_only_rollback(monkeypatch) -> None:
    """INTENT_MODE=heuristic_only 应快速回切并关闭 shadow 对账。"""
    monkeypatch.setenv("INTENT_MODE", "heuristic_only")
    monkeypatch.setenv("ENABLE_INTENT_SHADOW_COMPARE", "true")
    monkeypatch.setattr(SystemConfigService, "get", lambda _key, default=None: default)

    settings = ConfigResolver.get_intent_shadow_settings(default_mode="model_primary")
    assert settings["intent_mode"] == "heuristic_only"
    assert settings["intent_shadow_enabled"] is False

    def _raise_if_called(*_args, **_kwargs):
        raise AssertionError("heuristic_only 模式不应调用模型路径")

    monkeypatch.setattr(graph, "_infer_model_intent_plan", _raise_if_called)

    state = {"messages": [HumanMessage(content="请看下今天的待办")]}
    plan = _build_intent_plan(state, llm=object(), mode=settings["intent_mode"])
    metrics = graph._build_intent_shadow_metrics(
        state=state,
        intent_plan=plan,
        planner_mode=settings["intent_mode"],
        intent_shadow_enabled=settings["intent_shadow_enabled"],
    )

    assert plan["source"] == "heuristic_only"
    assert metrics["fallback_hit_rate"] == 0.0
    assert metrics["intent_diff_rate"] == 0.0
    assert metrics["intent_shadow_enabled"] is False


def test_intent_shadow_compare_outputs_diff_rate(monkeypatch) -> None:
    """shadow 开启时应输出 intent_diff_rate。"""
    monkeypatch.setenv("INTENT_MODE", "model_primary")
    monkeypatch.setenv("ENABLE_INTENT_SHADOW_COMPARE", "true")
    monkeypatch.setattr(SystemConfigService, "get", lambda _key, default=None: default)

    def _fake_model_plan(_state, _llm):
        return {
            "version": 1,
            "source": "model_primary",
            "user_query": "查看待办",
            "goals": [
                {
                    "goal_id": "GOAL-01",
                    "order": 1,
                    "kind": "external.lookup",
                    "title": "外部信息",
                    "must_answer": True,
                    "confidence": 0.92,
                    "allowed_agents": [],
                }
            ],
        }

    monkeypatch.setattr(graph, "_infer_model_intent_plan", _fake_model_plan)

    settings = ConfigResolver.get_intent_shadow_settings(default_mode="model_primary")
    state = {"messages": [HumanMessage(content="查看待办")]}
    plan = _build_intent_plan(state, llm=object(), mode=settings["intent_mode"])
    metrics = graph._build_intent_shadow_metrics(
        state=state,
        intent_plan=plan,
        planner_mode=settings["intent_mode"],
        intent_shadow_enabled=settings["intent_shadow_enabled"],
    )

    assert plan["source"] == "model_primary"
    assert metrics["intent_shadow_enabled"] is True
    assert metrics["intent_diff_rate"] > 0.0
    assert metrics["fallback_hit_rate"] == 0.0


def test_intent_shadow_metrics_records_fallback_hit_rate(monkeypatch) -> None:
    """模型失败兜底时应记录 fallback_hit_rate。"""
    monkeypatch.setenv("INTENT_MODE", "model_primary")
    monkeypatch.setenv("ENABLE_INTENT_SHADOW_COMPARE", "true")
    monkeypatch.setattr(SystemConfigService, "get", lambda _key, default=None: default)

    def _raise_model_error(_state, _llm):
        raise graph._PlannerModelInvokeError("provider unavailable")

    monkeypatch.setattr(graph, "_infer_model_intent_plan", _raise_model_error)

    settings = ConfigResolver.get_intent_shadow_settings(default_mode="model_primary")
    state = {"messages": [HumanMessage(content="帮我看下待办")]}
    plan = _build_intent_plan(state, llm=object(), mode=settings["intent_mode"])
    metrics = graph._build_intent_shadow_metrics(
        state=state,
        intent_plan=plan,
        planner_mode=settings["intent_mode"],
        intent_shadow_enabled=settings["intent_shadow_enabled"],
    )

    assert plan["source"] == "heuristic_fallback"
    assert metrics["fallback_hit_rate"] == 1.0
    assert metrics["intent_shadow_enabled"] is True


def test_intent_shadow_settings_prefers_db_dynamic_over_env(monkeypatch) -> None:
    """DB 动态配置应覆盖环境变量（与 ConfigResolver 既有契约一致）。"""
    monkeypatch.setenv("INTENT_MODE", "model_primary")
    monkeypatch.setenv("ENABLE_INTENT_SHADOW_COMPARE", "false")

    def _fake_get(key: str, default=None):
        if key == "INTENT_MODE":
            return "heuristic_only"
        if key == "ENABLE_INTENT_SHADOW_COMPARE":
            return "true"
        return default

    monkeypatch.setattr(SystemConfigService, "get", _fake_get)
    settings = ConfigResolver.get_intent_shadow_settings(default_mode="model_primary")

    assert settings["intent_mode"] == "heuristic_only"
    assert settings["intent_shadow_enabled"] is False
