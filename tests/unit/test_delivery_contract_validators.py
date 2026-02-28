"""交付合同校验器测试。"""

from app.ai.contracts.delivery_contract_validators import (
    build_contract_validation_meta,
    validate_coverage_report_contract,
    validate_intent_plan_contract,
)


def test_validate_intent_plan_contract_should_accept_valid_payload() -> None:
    """合法 intent_plan 应通过校验并保持核心字段。"""
    raw = {
        "version": 1,
        "source": "model_primary",
        "user_query": "先查待办再看天气",
        "goals": [
            {
                "goal_id": "GOAL-01",
                "order": 1,
                "kind": "todo.query",
                "title": "待办事项",
                "must_answer": True,
                "allowed_agents": ["todo_expert"],
                "confidence": 0.93,
            }
        ],
    }

    normalized, valid, error = validate_intent_plan_contract(raw)

    assert valid is True
    assert error == ""
    assert normalized["goals"][0]["goal_id"] == "GOAL-01"
    assert normalized["goals"][0]["allowed_agents"] == ["todo_expert"]


def test_validate_intent_plan_contract_should_fallback_when_invalid() -> None:
    """非法 intent_plan 应降级为最小可执行合同。"""
    raw = {
        "version": 1,
        "source": "model_primary",
        "user_query": "你好",
        "goals": [],
    }

    normalized, valid, error = validate_intent_plan_contract(raw)

    assert valid is False
    assert error.startswith("validation_error:")
    assert normalized["source"] == "contract_fallback"
    assert len(normalized["goals"]) == 1
    assert normalized["goals"][0]["kind"] == "general.reply"


def test_validate_coverage_report_contract_should_fallback_when_invalid() -> None:
    """非法 coverage_report 应降级并标记缺口。"""
    raw = {
        "pass": True,
        "total_goals": 2,
    }

    normalized, valid, error = validate_coverage_report_contract(raw)

    assert valid is False
    assert error.startswith("validation_error:")
    assert normalized["pass"] is False
    assert normalized["missing_goals"]


def test_build_contract_validation_meta_should_merge_flags() -> None:
    """contract 校验元数据应可增量合并。"""
    existing = {"intent_plan_valid": True}
    merged = build_contract_validation_meta(
        existing_meta=existing,
        intent_plan_valid=False,
        intent_plan_error="validation_error:goal_empty",
        coverage_valid=True,
        coverage_error="",
    )

    assert merged["intent_plan_valid"] is False
    assert merged["intent_plan_error"] == "validation_error:goal_empty"
    assert merged["coverage_valid"] is True
