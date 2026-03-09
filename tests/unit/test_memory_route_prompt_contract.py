"""记忆删除路由与 resolver prompt 合同测试。"""

from app.ai.prompts.agent_prompts import (
    MEMORY_INTENT_DECISION_PROMPT,
    MEMORY_REFERENCE_RESOLUTION_PROMPT,
    SUPERVISOR_PROMPT,
)
from app.ai.prompts.common_prompts import INTENT_CLASSIFY_PROMPT


def test_supervisor_prompt_should_keep_memory_delete_out_of_todo() -> None:
    """记忆/偏好删除必须留在 supervisor，不得误派 todo_expert。"""
    assert "长期记忆/偏好" in SUPERVISOR_PROMPT
    assert "不要委派 todo_expert" in SUPERVISOR_PROMPT
    assert 'route_to="supervisor"' in INTENT_CLASSIFY_PROMPT
    assert "不属于 todo_management" in INTENT_CLASSIFY_PROMPT


def test_memory_prompts_should_require_active_candidates_for_reference_resolution() -> None:
    """memory intent 相关 prompt 必须显式声明 active candidates 参与二阶段定位。"""
    assert "active_preference_candidates" in MEMORY_INTENT_DECISION_PROMPT
    assert "active_preference_candidates" in MEMORY_REFERENCE_RESOLUTION_PROMPT


def test_supervisor_prompt_should_describe_native_memory_delete_capability() -> None:
    """Supervisor 必须知道系统具备原生记忆删除能力。"""
    assert '原生记忆删除能力' in SUPERVISOR_PROMPT or '系统具备原生记忆删除能力' in SUPERVISOR_PROMPT
    assert '不要让用户去 Memory 页面手工删除' in SUPERVISOR_PROMPT


def test_memory_prompts_should_describe_confirmation_chain_by_behavior() -> None:
    """memory prompt 应描述承接行为，而不是把具体短语写死进合同。"""
    assert 'latest_assistant_message' in MEMORY_INTENT_DECISION_PROMPT
    assert 'latest_user_message_before_source' in MEMORY_INTENT_DECISION_PROMPT
    assert '固定触发词' in MEMORY_INTENT_DECISION_PROMPT
    assert '短确认回复' in MEMORY_INTENT_DECISION_PROMPT
    assert '编号选择' in MEMORY_INTENT_DECISION_PROMPT
    assert '已唯一确认目标' in MEMORY_INTENT_DECISION_PROMPT

    assert 'latest_assistant_message' in MEMORY_REFERENCE_RESOLUTION_PROMPT
    assert 'latest_user_message_before_source' in MEMORY_REFERENCE_RESOLUTION_PROMPT
    assert 'recent_archived_preference_candidates' in MEMORY_REFERENCE_RESOLUTION_PROMPT
    assert '短确认回复' in MEMORY_REFERENCE_RESOLUTION_PROMPT
    assert '编号选择' in MEMORY_REFERENCE_RESOLUTION_PROMPT


def test_memory_prompts_should_not_require_specific_delete_phrases() -> None:
    """prompt 合同不应要求某个固定删除短语必须出现。"""
    assert '删除这个记忆/忘掉这个' not in MEMORY_INTENT_DECISION_PROMPT
    assert '“1”“确认”“是这条”' not in MEMORY_INTENT_DECISION_PROMPT
    assert '删除这个记忆/忘掉这个' not in MEMORY_REFERENCE_RESOLUTION_PROMPT
    assert '“1”“确认”“是这条”' not in MEMORY_REFERENCE_RESOLUTION_PROMPT
    assert '<用户原文中的撤销表达>' in MEMORY_INTENT_DECISION_PROMPT
    assert '<用户原文中的删除指代>' in MEMORY_REFERENCE_RESOLUTION_PROMPT
