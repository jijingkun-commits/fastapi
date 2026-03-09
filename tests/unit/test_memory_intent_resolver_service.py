"""memory intent resolver 服务测试。"""

from __future__ import annotations

from types import SimpleNamespace

import app.services.memory_intent_resolver_service as resolver_service


class _FakeLLM:
    def invoke(self, prompt: str):  # noqa: ARG002
        raise AssertionError("本测试应通过 monkeypatch 控制 resolver，不应真的调用 LLM")


def test_build_context_should_include_active_preference_candidates(monkeypatch) -> None:  # noqa: ANN001
    """resolver 上下文应携带当前活跃偏好候选。"""

    monkeypatch.setattr(
        resolver_service.document_memory_repo,
        "list_documents",
        lambda *args, **kwargs: (
            [
                {
                    "slot_key": "user.preference.response.structure",
                    "summary_md": "用户偏好用详细的总分总段落结构回答",
                },
                {
                    "slot_key": "assistant.persona.style",
                    "summary_md": "助手人设为友好亲切",
                },
            ],
            2,
        ),
    )
    monkeypatch.setattr(resolver_service.chat_repo, "get_messages_by_thread", lambda *args, **kwargs: [])

    context = resolver_service.build_context(
        object(),
        user_id=2,
        thread_id="thread-archive",
        source_message_id=5253,
    )

    assert context["source_thread_id"] == "thread-archive"
    assert context["source_message_id"] == 5253
    assert context["active_preference_candidates"][0]["slot_key"] == "user.preference.response.structure"
    assert "总分总" in context["active_preference_candidates"][0]["summary_md"]


def test_build_context_should_include_latest_dialogue_reference_messages(monkeypatch) -> None:  # noqa: ANN001
    """resolver 上下文应显式暴露最近 assistant / previous human 承接信息。"""

    monkeypatch.setattr(
        resolver_service.document_memory_repo,
        "list_documents",
        lambda *args, **kwargs: (
            [
                {
                    "slot_key": "user.profile.relationship.parent.of",
                    "summary_md": "用户是纪宇圩的爸爸",
                }
            ],
            1,
        ),
    )
    monkeypatch.setattr(
        resolver_service.chat_repo,
        "get_messages_by_thread",
        lambda *args, **kwargs: [
            SimpleNamespace(id=5329, role="human", content="谁是纪宇圩的爸爸"),
            SimpleNamespace(id=5330, role="ai", content="根据之前记录，你是纪宇圩的爸爸。"),
            SimpleNamespace(id=5331, role="human", content="删除这个记忆"),
            SimpleNamespace(id=5332, role="ai", content="好的，你说的这个记忆我理解为你是纪宇圩的爸爸。"),
            SimpleNamespace(id=5333, role="human", content="1"),
        ],
    )

    context = resolver_service.build_context(
        object(),
        user_id=2,
        thread_id="thread-confirm",
        source_message_id=5333,
    )

    assert context["latest_assistant_message"]["message_id"] == 5332
    assert "你是纪宇圩的爸爸" in context["latest_assistant_message"]["content"]
    assert context["latest_user_message_before_source"]["message_id"] == 5331
    assert context["latest_user_message_before_source"]["content"] == "删除这个记忆"


def test_build_context_should_include_recent_reference_candidates(monkeypatch) -> None:  # noqa: ANN001
    """指代删除场景应补充最近线程消息与最近记忆候选。"""

    monkeypatch.setattr(
        resolver_service.document_memory_repo,
        "list_documents",
        lambda *args, **kwargs: (
            [
                {
                    "slot_key": "user.profile.fact.jiaxing.bank.founded.2000",
                    "summary_md": "嘉兴银行成立于2000年",
                },
                {
                    "slot_key": "user.profile.fact.wealth.management.products.types",
                    "summary_md": "理财产品分为自营和代销",
                },
            ],
            2,
        ),
    )
    monkeypatch.setattr(
        resolver_service.chat_repo,
        "get_messages_by_thread",
        lambda *args, **kwargs: [
            SimpleNamespace(id=5265, role="ai", content="我记得你提到过嘉兴银行成立于2000年。"),
            SimpleNamespace(id=5266, role="human", content="嘉兴银行成立于2000年"),
            SimpleNamespace(id=5267, role="human", content="忘掉这个记忆"),
        ],
    )

    context = resolver_service.build_context(
        object(),
        user_id=2,
        thread_id="thread-reference",
        source_message_id=5267,
    )

    assert context["recent_thread_messages"][-1]["message_id"] == 5266
    assert context["recent_memory_reference_candidates"][0]["slot_key"] == "user.profile.fact.jiaxing.bank.founded.2000"
    assert context["recent_memory_reference_candidates"][0]["matched_message_id"] == 5266



def test_build_context_should_include_recent_archived_candidates_for_confirmation_turn(monkeypatch) -> None:  # noqa: ANN001
    """上一轮已归档的同线程目标应显式暴露给确认轮。"""

    captured_calls: list[dict[str, object]] = []

    def _fake_list_documents(*args, **kwargs):  # noqa: ANN001
        captured_calls.append(dict(kwargs))
        status = kwargs.get("status")
        if status == "active":
            return ([], 0)
        if status == "archived":
            return (
                [
                    {
                        "slot_key": "user.profile.relationship.to.person",
                        "summary_md": "用户是纪宇圩的爸爸",
                        "source_thread_id": "thread-confirm",
                        "source_message_id": 5395,
                    }
                ],
                1,
            )
        return ([], 0)

    monkeypatch.setattr(resolver_service.document_memory_repo, "list_documents", _fake_list_documents)
    monkeypatch.setattr(
        resolver_service.chat_repo,
        "get_messages_by_thread",
        lambda *args, **kwargs: [
            SimpleNamespace(id=5394, role="ai", content="系统繁忙，当前请求暂时无法处理，请稍后重试。"),
            SimpleNamespace(id=5395, role="human", content="删除这个记忆"),
            SimpleNamespace(id=5396, role="ai", content="系统繁忙，当前请求暂时无法处理，请稍后重试。"),
            SimpleNamespace(id=5397, role="human", content="1"),
        ],
    )

    context = resolver_service.build_context(
        object(),
        user_id=1,
        thread_id="thread-confirm",
        source_message_id=5397,
    )

    assert context["latest_user_message_before_source"]["message_id"] == 5395
    assert context["recent_archived_preference_candidates"][0]["slot_key"] == "user.profile.relationship.to.person"
    assert context["recent_archived_preference_candidates"][0]["source_message_id"] == 5395
    assert context["recent_archived_preference_candidates"][0]["match_latest_user_message"] is True
    assert captured_calls[0].get("status") == "active"
    assert captured_calls[0].get("include_source_refs") in (None, False)
    assert captured_calls[1].get("status") == "archived"
    assert captured_calls[1].get("include_source_refs") is True


def test_resolve_should_return_primary_contract_when_primary_decision_accept(monkeypatch) -> None:  # noqa: ANN001
    """primary 判定 accept 时应直接产出持久化合同。"""

    monkeypatch.setattr(
        resolver_service,
        "build_context",
        lambda *args, **kwargs: {"source_thread_id": "thread-1", "source_message_id": 101},
    )
    monkeypatch.setattr(
        resolver_service.memory_intent_llm_service,
        "decide",
        lambda **kwargs: {
            "decision": "accept",
            "reason_code": "accepted",
            "confidence": 0.93,
            "memories": [
                {
                    "memory_kind": "response_preference",
                    "operation": "upsert",
                    "slot_key": "user.preference.response_length",
                    "normalized_value": "short",
                    "canonical_text": "用户偏好回答简短",
                    "evidence_span": "回答简短一点",
                }
            ],
            "audit": {"detector": "llm_primary"},
        },
    )
    monkeypatch.setattr(
        resolver_service.memory_intent_llm_service,
        "resolve_reference_archive",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("primary accept 不应触发候选解析")),
    )

    result = resolver_service.resolve(
        object(),
        llm=_FakeLLM(),
        user_text="以后回答简短一点",
        user_id=7,
        thread_id="thread-1",
        source_message_id=101,
    )

    assert result["resolution_status"] == "resolved"
    assert result["reason_code"] == "accepted"
    assert result["persistence_contract"]["decision"] == "accept"
    assert result["audit"]["resolver_stage"] == "primary"


def test_resolve_should_use_reference_resolution_when_primary_rejects(monkeypatch) -> None:  # noqa: ANN001
    """primary reject 且存在候选时，应交给 reference resolver 继续解析。"""

    monkeypatch.setattr(
        resolver_service,
        "build_context",
        lambda *args, **kwargs: {
            "source_thread_id": "thread-reference",
            "source_message_id": 5267,
            "recent_memory_reference_candidates": [
                {
                    "slot_key": "user.profile.fact.jiaxing.bank.founded.2000",
                    "summary_md": "嘉兴银行成立于2000年",
                }
            ],
        },
    )
    monkeypatch.setattr(
        resolver_service.memory_intent_llm_service,
        "decide",
        lambda **kwargs: {
            "decision": "reject",
            "reason_code": "reverse_intent_slot_missing",
            "confidence": 0.71,
            "memories": [],
            "audit": {"detector": "llm_primary"},
        },
    )
    monkeypatch.setattr(
        resolver_service.memory_intent_llm_service,
        "resolve_reference_archive",
        lambda **kwargs: {
            "decision": "accept",
            "reason_code": "reference_archive_resolved",
            "confidence": 0.95,
            "memories": [
                {
                    "memory_kind": "profile_fact",
                    "operation": "archive",
                    "slot_key": "user.profile.fact.jiaxing.bank.founded.2000",
                    "normalized_value": "",
                    "canonical_text": "用户要求删除已有记忆：嘉兴银行成立于2000年",
                    "evidence_span": "忘掉这个记忆",
                }
            ],
            "audit": {"detector": "llm_primary"},
        },
    )

    result = resolver_service.resolve(
        object(),
        llm=_FakeLLM(),
        user_text="忘掉这个记忆",
        user_id=2,
        thread_id="thread-reference",
        source_message_id=5267,
    )

    assert result["resolution_status"] == "resolved"
    assert result["reason_code"] == "reference_archive_resolved"
    assert result["persistence_contract"]["memories"][0]["slot_key"] == "user.profile.fact.jiaxing.bank.founded.2000"
    assert result["audit"]["resolver_stage"] == "reference_resolution"
    assert result["audit"]["primary_reason_code"] == "reverse_intent_slot_missing"


def test_resolve_should_fallback_to_active_candidates_without_recent_reference_hits(monkeypatch) -> None:  # noqa: ANN001
    """没有 lexical recent hit 时，只要有 active candidates + recent messages 仍应进入二阶段解析。"""

    monkeypatch.setattr(
        resolver_service,
        "build_context",
        lambda *args, **kwargs: {
            "source_thread_id": "thread-reference",
            "source_message_id": 5286,
            "active_preference_candidates": [
                {
                    "slot_key": "user.profile.fact.wealth.management.products.types",
                    "summary_md": "理财产品分为自营和代销",
                }
            ],
            "recent_thread_messages": [
                {
                    "message_id": 5285,
                    "role": "ai",
                    "content": "理财产品一般分为两类：自营和代销。",
                }
            ],
        },
    )
    monkeypatch.setattr(
        resolver_service.memory_intent_llm_service,
        "decide",
        lambda **kwargs: {
            "decision": "reject",
            "reason_code": "low_confidence",
            "confidence": 0.62,
            "memories": [],
            "audit": {"detector": "llm_primary"},
        },
    )
    monkeypatch.setattr(
        resolver_service.memory_intent_llm_service,
        "resolve_reference_archive",
        lambda **kwargs: {
            "decision": "accept",
            "reason_code": "reference_archive_resolved",
            "confidence": 0.94,
            "memories": [
                {
                    "memory_kind": "profile_fact",
                    "operation": "archive",
                    "slot_key": "user.profile.fact.wealth.management.products.types",
                    "normalized_value": "",
                    "canonical_text": "用户要求删除已有记忆：理财产品分为自营和代销",
                    "evidence_span": "帮我删除这个记忆",
                }
            ],
            "audit": {"detector": "llm_primary"},
        },
    )

    result = resolver_service.resolve(
        object(),
        llm=_FakeLLM(),
        user_text="这是记忆吧？帮我删除这个记忆",
        user_id=2,
        thread_id="thread-reference",
        source_message_id=5286,
    )

    assert result["resolution_status"] == "resolved"
    assert result["reason_code"] == "reference_archive_resolved"
    assert result["persistence_contract"]["memories"][0]["slot_key"] == "user.profile.fact.wealth.management.products.types"
    assert result["audit"]["resolver_stage"] == "reference_resolution"
    assert result["audit"]["primary_reason_code"] == "low_confidence"


def test_resolve_should_return_needs_clarification_when_reference_resolution_unresolved(monkeypatch) -> None:  # noqa: ANN001
    """候选解析仍无法唯一定位时，应返回 needs_clarification。"""

    monkeypatch.setattr(
        resolver_service,
        "build_context",
        lambda *args, **kwargs: {
            "source_thread_id": "thread-reference",
            "source_message_id": 5267,
            "recent_memory_reference_candidates": [
                {"slot_key": "slot-a", "summary_md": "候选A"},
                {"slot_key": "slot-b", "summary_md": "候选B"},
            ],
        },
    )
    monkeypatch.setattr(
        resolver_service.memory_intent_llm_service,
        "decide",
        lambda **kwargs: {
            "decision": "reject",
            "reason_code": "low_confidence",
            "confidence": 0.62,
            "memories": [],
            "audit": {"detector": "llm_primary"},
        },
    )
    monkeypatch.setattr(
        resolver_service.memory_intent_llm_service,
        "resolve_reference_archive",
        lambda **kwargs: {
            "decision": "reject",
            "reason_code": "reverse_intent_target_ambiguous",
            "confidence": 0.74,
            "memories": [],
            "audit": {"detector": "llm_primary"},
        },
    )

    result = resolver_service.resolve(
        object(),
        llm=_FakeLLM(),
        user_text="忘掉这个记忆",
        user_id=2,
        thread_id="thread-reference",
        source_message_id=5267,
    )

    assert result["resolution_status"] == "needs_clarification"
    assert result["reason_code"] == "reverse_intent_target_ambiguous"
    assert result["persistence_contract"] is None




def test_resolve_should_attempt_reference_resolution_with_recent_archived_candidates(monkeypatch) -> None:  # noqa: ANN001
    """同线程最近已归档目标应足以放行确认轮二阶段解析。"""

    monkeypatch.setattr(
        resolver_service,
        "build_context",
        lambda *args, **kwargs: {
            "source_thread_id": "thread-confirm",
            "source_message_id": 5397,
            "recent_archived_preference_candidates": [
                {
                    "slot_key": "user.profile.relationship.to.person",
                    "summary_md": "用户是纪宇圩的爸爸",
                    "source_thread_id": "thread-confirm",
                    "source_message_id": 5395,
                    "match_latest_user_message": True,
                }
            ],
            "recent_thread_messages": [
                {"message_id": 5394, "role": "ai", "content": "系统繁忙，当前请求暂时无法处理，请稍后重试。"},
                {"message_id": 5395, "role": "human", "content": "删除这个记忆"},
                {"message_id": 5396, "role": "ai", "content": "系统繁忙，当前请求暂时无法处理，请稍后重试。"},
            ],
            "latest_assistant_message": {"message_id": 5396, "role": "ai", "content": "系统繁忙，当前请求暂时无法处理，请稍后重试。"},
            "latest_user_message_before_source": {"message_id": 5395, "role": "human", "content": "删除这个记忆"},
        },
    )
    monkeypatch.setattr(
        resolver_service.memory_intent_llm_service,
        "decide",
        lambda **kwargs: {
            "decision": "reject",
            "reason_code": "low_confidence",
            "confidence": 0.52,
            "memories": [],
            "audit": {"detector": "llm_primary"},
        },
    )
    monkeypatch.setattr(
        resolver_service.memory_intent_llm_service,
        "resolve_reference_archive",
        lambda **kwargs: {
            "decision": "accept",
            "reason_code": "reference_archive_resolved",
            "confidence": 0.94,
            "memories": [
                {
                    "memory_kind": "profile_fact",
                    "operation": "archive",
                    "slot_key": "user.profile.relationship.to.person",
                    "normalized_value": "",
                    "canonical_text": "用户要求删除已有记忆：用户是纪宇圩的爸爸",
                    "evidence_span": "1",
                }
            ],
            "audit": {"detector": "llm_primary"},
        },
    )

    result = resolver_service.resolve(
        object(),
        llm=_FakeLLM(),
        user_text="1",
        user_id=1,
        thread_id="thread-confirm",
        source_message_id=5397,
    )

    assert result["resolution_status"] == "resolved"
    assert result["reason_code"] == "reference_archive_resolved"
    assert result["persistence_contract"]["memories"][0]["slot_key"] == "user.profile.relationship.to.person"
    assert result["audit"]["primary_reason_code"] == "low_confidence"

def test_resolve_should_use_archived_candidates_for_confirmation_turn(monkeypatch) -> None:  # noqa: ANN001
    """active 候选已消失时，archived candidates + 最近确认上下文仍应允许继续识别同一删除目标。"""

    monkeypatch.setattr(
        resolver_service,
        "build_context",
        lambda *args, **kwargs: {
            "source_thread_id": "thread-confirm",
            "source_message_id": 5345,
            "archived_preference_candidates": [
                {
                    "slot_key": "user.profile.relationship.parent.of",
                    "summary_md": "用户是纪宇圩的爸爸",
                }
            ],
            "recent_thread_messages": [
                {"message_id": 5342, "role": "ai", "content": "你是纪宇圩的爸爸。"},
                {"message_id": 5343, "role": "human", "content": "删除这个记忆"},
                {"message_id": 5344, "role": "ai", "content": "我会处理并删除你是纪宇圩的爸爸这条长期记忆。"},
            ],
            "latest_assistant_message": {"message_id": 5344, "role": "ai", "content": "我会处理并删除你是纪宇圩的爸爸这条长期记忆。"},
            "latest_user_message_before_source": {"message_id": 5343, "role": "human", "content": "删除这个记忆"},
        },
    )
    monkeypatch.setattr(
        resolver_service.memory_intent_llm_service,
        "decide",
        lambda **kwargs: {
            "decision": "reject",
            "reason_code": "low_confidence",
            "confidence": 0.51,
            "memories": [],
            "audit": {"detector": "llm_primary"},
        },
    )
    monkeypatch.setattr(
        resolver_service.memory_intent_llm_service,
        "resolve_reference_archive",
        lambda **kwargs: {
            "decision": "accept",
            "reason_code": "reference_archive_resolved",
            "confidence": 0.93,
            "memories": [
                {
                    "memory_kind": "profile_fact",
                    "operation": "archive",
                    "slot_key": "user.profile.relationship.parent.of",
                    "normalized_value": "",
                    "canonical_text": "用户要求删除已有记忆：用户是纪宇圩的爸爸",
                    "evidence_span": "1",
                }
            ],
            "audit": {"detector": "llm_primary"},
        },
    )

    result = resolver_service.resolve(
        object(),
        llm=_FakeLLM(),
        user_text="1",
        user_id=2,
        thread_id="thread-confirm",
        source_message_id=5345,
    )

    assert result["resolution_status"] == "resolved"
    assert result["persistence_contract"]["memories"][0]["slot_key"] == "user.profile.relationship.parent.of"
