"""response policy 服务测试。"""

import app.services.response_policy_service as response_policy_service


def test_build_memory_archive_guidance_contract_should_return_structured_payload() -> None:
    contract = response_policy_service.build_memory_archive_guidance_contract(
        {
            "decision": "accept",
            "memories": [
                {
                    "operation": "archive",
                    "slot_key": "user.profile.relationship.parent.of",
                    "canonical_text": "用户要求删除已有记忆：用户是纪宇圩的爸爸",
                }
            ],
        },
        persisted_doc_count=1,
    )

    assert contract == {
        "kind": "memory_archive",
        "status": "persisted",
        "target_canonical_text": "用户要求删除已有记忆：用户是纪宇圩的爸爸",
        "target_slot_key": "user.profile.relationship.parent.of",
        "followup_behavior": "reuse_resolved_target",
    }


def test_render_response_guidance_contract_should_render_memory_archive_text() -> None:
    rendered = response_policy_service.render_response_guidance_contract(
        {
            "kind": "memory_archive",
            "status": "already_absent",
            "target_canonical_text": "用户要求删除已有记忆：用户是纪宇圩的爸爸",
            "target_slot_key": "user.profile.relationship.parent.of",
            "followup_behavior": "reuse_resolved_target",
        }
    )

    assert "已经删除或已处理" in rendered
    assert "user.profile.relationship.parent.of" in rendered
    assert "已唯一确认的删除链" in rendered


def test_build_multi_intent_recovery_system_context_should_not_append_legacy_recovery_prompt() -> None:
    rendered = response_policy_service.build_multi_intent_recovery_system_context(
        "当前时间: 2026-02-28",
        {
            "goals": [
                {"goal_id": "GOAL-1", "kind": "todo.query"},
                {"goal_id": "GOAL-2", "kind": "external.lookup"},
            ]
        },
        [
            {"goal_id": "GOAL-1", "title": "待办事项"},
            {"goal_id": "GOAL-2", "title": "天气信息"},
        ],
    )

    assert rendered == "当前时间: 2026-02-28"
    assert "【交付补齐提示】" not in rendered
    assert "assign_to_todo_expert" not in rendered
    assert "tavily_search" not in rendered


def test_build_router_blocked_system_context_should_not_append_recovery_prompt() -> None:
    rendered = response_policy_service.build_router_blocked_system_context(
        base_context="当前时间: 2026-02-28",
        active_plan={"goals": [{"goal_id": "GOAL-1", "kind": "todo.query"}]},
        pending_goals=[{"goal_id": "GOAL-1", "title": "待办事项"}],
    )

    assert rendered == "当前时间: 2026-02-28"
    assert "【交付补齐提示】" not in rendered
    assert "assign_to_todo_expert" not in rendered
