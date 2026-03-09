"""记忆意图运行时接线测试。"""

import asyncio
from types import SimpleNamespace

import app.core.memory_intent_runtime as runtime
import app.main as main_module


def test_process_memory_intent_job_should_resolve_and_flush(monkeypatch) -> None:  # noqa: ANN001
    captured: dict[str, object] = {}

    monkeypatch.setattr(runtime, "get_scene_llm", lambda **kwargs: "fake-llm")
    monkeypatch.setattr(
        runtime.memory_intent_resolver_service,
        "resolve",
        lambda db, **kwargs: {
            "resolution_status": "resolved",
            "reason_code": "reference_archive_resolved",
            "persistence_contract": {
                "decision": "accept",
                "reason_code": "reference_archive_resolved",
                "confidence": 0.93,
                "memories": [
                    {
                        "memory_kind": "user_identity",
                        "operation": "archive",
                        "slot_key": "user.profile.identity.display_name",
                        "normalized_value": "",
                        "canonical_text": "用户名字是纪景锟",
                        "evidence_span": "把我的名字删掉",
                    }
                ],
                "audit": {"decision_id": "decision-1001"},
            },
        },
    )
    monkeypatch.setattr(runtime, "flush_canonical_memory", lambda db, **kwargs: captured.update(kwargs) or 1)

    job = SimpleNamespace(
        id=11,
        user_id=2,
        payload_json={
            "user_text": "把我的名字删掉",
            "source_thread_id": "thread-1",
            "source_message_id": 1001,
        },
    )

    runtime.process_memory_intent_job(object(), job=job)

    assert captured["user_id"] == 2
    assert captured["source_thread_id"] == "thread-1"
    assert captured["source_message_id"] == 1001
    assert captured["manage_transaction"] is False
    assert captured["decision_contract"]["reason_code"] == "reference_archive_resolved"


def test_lifespan_should_start_and_stop_memory_intent_runtime(monkeypatch) -> None:  # noqa: ANN001
    import app.core.settings as settings_module
    import app.db.session as session_module
    import app.services.llm_config_service as llm_config_module
    import app.services.llm_scene_service as llm_scene_module
    import app.services.result_enrichment_rule_service as rule_module
    import app.services.system_config_service as system_config_module

    calls: list[str] = []

    class _SessionContext:
        def __enter__(self):
            return object()

        def __exit__(self, exc_type, exc, tb):
            return False

    async def _noop_async(*args, **kwargs):  # noqa: ANN002, ANN003
        return None

    async def _fake_stop(app):  # noqa: ANN001
        calls.append("stop")

    monkeypatch.setattr(main_module, "setup_logging", lambda: None)
    monkeypatch.setattr(main_module, "INIT_DB_ON_STARTUP", False)
    monkeypatch.setattr(main_module, "get_checkpointer", _noop_async)
    monkeypatch.setattr(main_module, "close_checkpointer", _noop_async)
    monkeypatch.setattr(settings_module, "Settings", lambda: object())
    monkeypatch.setattr(session_module, "SessionLocal", lambda: _SessionContext())
    monkeypatch.setattr(llm_config_module.LLMConfigService, "load_from_db", lambda *args, **kwargs: None)
    monkeypatch.setattr(llm_scene_module.LLMSceneService, "load_from_db", lambda *args, **kwargs: None)
    monkeypatch.setattr(llm_scene_module.LLMSceneService, "validate_startup_integrity", lambda *args, **kwargs: None)
    monkeypatch.setattr(system_config_module.SystemConfigService, "load_from_db", lambda *args, **kwargs: None)
    monkeypatch.setattr(rule_module, "get_result_enrichment_rule_service", lambda: SimpleNamespace(refresh_rules=lambda: None))
    monkeypatch.setattr(main_module, "start_memory_intent_runtime", lambda app: calls.append("start"), raising=False)
    monkeypatch.setattr(main_module, "stop_memory_intent_runtime", _fake_stop, raising=False)

    async def _exercise() -> None:
        async with main_module.lifespan(main_module.app):
            assert calls == ["start"]

    asyncio.run(_exercise())

    assert calls == ["start", "stop"]
