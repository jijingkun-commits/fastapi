"""记忆管理审计服务单元测试。"""

from __future__ import annotations

import pytest

import app.services.memory_admin_service as memory_admin_service
from app.core import config
from app.core.config_contract import CONFIG_SPECS
from app.services.config_resolver import ConfigResolver


class _DummySession:
    def __init__(self) -> None:
        self.commit_called = 0
        self.rollback_called = 0

    def commit(self) -> None:
        self.commit_called += 1

    def rollback(self) -> None:
        self.rollback_called += 1


def test_record_admin_audit_should_commit_when_insert_succeeds(monkeypatch) -> None:  # noqa: ANN001
    """审计入库成功时应提交事务。"""

    session = _DummySession()
    captured: dict[str, object] = {}

    def _fake_create_audit_log(db, **kwargs):  # noqa: ANN001
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(
        memory_admin_service.memory_admin_audit_repo,
        "create_audit_log",
        _fake_create_audit_log,
    )

    written = memory_admin_service.record_admin_audit(
        session,
        operator_user_id=101,
        target_user_id=202,
        memory_id=303,
        action=memory_admin_service.AUDIT_ACTION_ARCHIVE_MEMORY,
        action_payload={"status": "archived"},
        result_status=memory_admin_service.AUDIT_RESULT_COMPLETED,
    )

    assert written is True
    assert session.commit_called == 1
    assert session.rollback_called == 0
    assert captured["operator_user_id"] == 101
    assert captured["target_user_id"] == 202
    assert captured["memory_id"] == 303
    assert captured["result_status"] == memory_admin_service.AUDIT_RESULT_COMPLETED


def test_record_admin_audit_should_swallow_exception(monkeypatch) -> None:  # noqa: ANN001
    """审计写入失败时不抛异常并回滚。"""

    session = _DummySession()

    def _raise_create_audit_log(*args, **kwargs):  # noqa: ANN001
        raise RuntimeError("audit insert failed")

    monkeypatch.setattr(
        memory_admin_service.memory_admin_audit_repo,
        "create_audit_log",
        _raise_create_audit_log,
    )

    written = memory_admin_service.record_admin_audit(
        session,
        operator_user_id=101,
        target_user_id=202,
        memory_id=303,
        action=memory_admin_service.AUDIT_ACTION_ARCHIVE_MEMORY,
        action_payload={"status": "archived"},
        result_status=memory_admin_service.AUDIT_RESULT_FAILED,
        error_message="boom",
    )

    assert written is False
    assert session.commit_called == 0
    assert session.rollback_called == 1


def test_archive_memory_should_not_block_on_audit_failure(monkeypatch) -> None:  # noqa: ANN001
    """归档主流程成功时，审计失败不应阻塞返回。"""

    session = _DummySession()
    audit_calls: list[dict[str, object]] = []

    monkeypatch.setattr(
        memory_admin_service.document_memory_repo,
        "archive_document",
        lambda *args, **kwargs: {"found": True, "changed": True, "status": "archived"},
        raising=False,
    )

    def _fake_record_admin_audit(db, **kwargs):  # noqa: ANN001
        audit_calls.append(kwargs)
        return False

    monkeypatch.setattr(memory_admin_service, "record_admin_audit", _fake_record_admin_audit)

    payload = memory_admin_service.archive_memory(
        session,
        memory_id=11,
        user_id=7,
        operator_id=9,
    )

    assert payload["status"] == "archived"
    assert payload["changed"] is True
    assert session.commit_called == 1
    assert session.rollback_called == 0
    assert len(audit_calls) == 1
    assert audit_calls[0]["action"] == memory_admin_service.AUDIT_ACTION_ARCHIVE_MEMORY
    assert audit_calls[0]["result_status"] == memory_admin_service.AUDIT_RESULT_COMPLETED


def test_archive_memory_should_record_failed_audit(monkeypatch) -> None:  # noqa: ANN001
    """归档抛错时应写失败审计并继续抛出原异常。"""

    session = _DummySession()
    audit_calls: list[dict[str, object]] = []

    def _raise_archive(*args, **kwargs):  # noqa: ANN001
        raise RuntimeError("archive failed")

    monkeypatch.setattr(
        memory_admin_service.document_memory_repo,
        "archive_document",
        _raise_archive,
        raising=False,
    )

    def _fake_record_admin_audit(db, **kwargs):  # noqa: ANN001
        audit_calls.append(kwargs)
        return True

    monkeypatch.setattr(memory_admin_service, "record_admin_audit", _fake_record_admin_audit)

    with pytest.raises(RuntimeError, match="archive failed"):
        memory_admin_service.archive_memory(
            session,
            memory_id=11,
            user_id=7,
            operator_id=9,
        )

    assert session.rollback_called == 1
    assert len(audit_calls) == 1
    assert audit_calls[0]["action"] == memory_admin_service.AUDIT_ACTION_ARCHIVE_MEMORY
    assert audit_calls[0]["result_status"] == memory_admin_service.AUDIT_RESULT_FAILED
    assert audit_calls[0]["error_message"] == "archive failed"


def test_delete_memory_should_record_completed_audit(monkeypatch) -> None:  # noqa: ANN001
    """删除成功时应写完成审计。"""

    session = _DummySession()
    audit_calls: list[dict[str, object]] = []

    monkeypatch.setattr(
        memory_admin_service.document_memory_repo,
        "delete_document",
        lambda *args, **kwargs: {
            "found": True,
            "deleted": True,
            "deleted_chunks": 4,
        },
        raising=False,
    )

    def _fake_record_admin_audit(db, **kwargs):  # noqa: ANN001
        audit_calls.append(kwargs)
        return True

    monkeypatch.setattr(memory_admin_service, "record_admin_audit", _fake_record_admin_audit)

    payload = memory_admin_service.delete_memory(
        session,
        memory_id=22,
        user_id=8,
        operator_id=10,
    )

    assert payload["status"] == "deleted"
    assert payload["deleted"] is True
    assert payload["deleted_chunks"] == 4
    assert session.commit_called == 1
    assert len(audit_calls) == 1
    assert audit_calls[0]["action"] == memory_admin_service.AUDIT_ACTION_DELETE_MEMORY
    assert audit_calls[0]["result_status"] == memory_admin_service.AUDIT_RESULT_COMPLETED


def test_list_memories_should_suppress_legacy_assistant_persona_when_structured_exists(monkeypatch) -> None:  # noqa: ANN001
    """同一用户存在结构化人设时，列表应隐藏 legacy assistant.persona。"""

    monkeypatch.setattr(
        memory_admin_service.document_memory_repo,
        "list_documents",
        lambda *args, **kwargs: (
            [
                {
                    "memory_id": 8,
                    "doc_id": 8,
                    "user_id": 2,
                    "doc_kind": "preference",
                    "doc_key": "assistant.persona.name",
                    "slot_key": "assistant.persona.name",
                    "summary_md": "AAA",
                    "content_md": "",
                    "status": "active",
                },
                {
                    "memory_id": 5,
                    "doc_id": 5,
                    "user_id": 2,
                    "doc_kind": "preference",
                    "doc_key": "global:assistant.persona",
                    "slot_key": None,
                    "summary_md": "hh",
                    "content_md": "",
                    "status": "active",
                },
            ],
            2,
        ),
    )

    payload = memory_admin_service.list_memories(
        _DummySession(),
        user_id=2,
        status="active",
        page=1,
        page_size=20,
    )

    assert payload["total"] == 1
    assert len(payload["items"]) == 1
    assert payload["items"][0]["doc_key"] == "assistant.persona.name"


def test_memory_admin_feature_flags_should_be_registered_in_config_contract() -> None:
    """记忆能力应通过单开关纳入配置契约。"""

    switch_spec = CONFIG_SPECS["feature.enable_document_memory"]
    assert switch_spec.value_type == "boolean"
    assert switch_spec.default is False
    assert switch_spec.env_key == "ENABLE_DOCUMENT_MEMORY"


def test_memory_admin_pagination_should_be_registered_in_config_contract() -> None:
    """分页配置应纳入配置契约并提供默认值。"""

    default_page_spec = CONFIG_SPECS["memory.document.admin.default_page_size"]
    max_page_spec = CONFIG_SPECS["memory.document.admin.max_page_size"]

    assert default_page_spec.value_type == "number"
    assert default_page_spec.default == 20
    assert default_page_spec.env_key == "DOCUMENT_MEMORY_ADMIN_DEFAULT_PAGE_SIZE"

    assert max_page_spec.value_type == "number"
    assert max_page_spec.default == 100
    assert max_page_spec.env_key == "DOCUMENT_MEMORY_ADMIN_MAX_PAGE_SIZE"


def test_memory_admin_config_resolver_should_read_dynamic_values(monkeypatch) -> None:  # noqa: ANN001
    """ConfigResolver 应支持解析 memory-admin 新增配置。"""

    values = {
        "feature.enable_document_memory": "true",
        "memory.document.admin.default_page_size": "30",
        "memory.document.admin.max_page_size": "120",
    }

    def _mock_get(key: str, default=None):  # noqa: ANN001
        return values.get(key, default)

    monkeypatch.setattr("app.services.config_resolver.SystemConfigService.get", _mock_get)

    assert ConfigResolver.get_bool("feature.enable_document_memory", False) is True
    assert ConfigResolver.get_int("memory.document.admin.default_page_size", 20) == 30
    assert ConfigResolver.get_int("memory.document.admin.max_page_size", 100) == 120


def test_memory_admin_runtime_constants_should_be_exposed() -> None:
    """运行时配置模块应暴露 memory-admin 新增常量。"""

    assert isinstance(config.ENABLE_DOCUMENT_MEMORY, bool)
    assert isinstance(config.DOCUMENT_MEMORY_ADMIN_DEFAULT_PAGE_SIZE, int)
    assert isinstance(config.DOCUMENT_MEMORY_ADMIN_MAX_PAGE_SIZE, int)
