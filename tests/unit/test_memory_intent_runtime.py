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
    calls: list[str] = []

    async def _fake_stop(app):  # noqa: ANN001
        calls.append("stop")

    async def _fake_aclose() -> None:
        return None

    async def _fake_build_runtime():
        return SimpleNamespace(aclose=_fake_aclose)

    monkeypatch.setattr(main_module, "build_runtime", _fake_build_runtime, raising=False)
    monkeypatch.setattr(main_module, "start_memory_intent_runtime", lambda app: calls.append("start"), raising=False)
    monkeypatch.setattr(main_module, "stop_memory_intent_runtime", _fake_stop, raising=False)

    async def _exercise() -> None:
        async with main_module.lifespan(main_module.app):
            assert calls == ["start"]

    asyncio.run(_exercise())

    assert calls == ["start", "stop"]


def test_runtime_loop_should_backoff_idle_polls_and_reset_after_work(monkeypatch) -> None:  # noqa: ANN001
    """空闲轮询应逐步退避，并在消费任务后恢复最小间隔。"""

    results = iter(
        [
            {"status": "idle"},
            {"status": "idle"},
            {"status": "succeeded"},
            {"status": "idle"},
        ]
    )
    delays: list[float] = []

    async def _fake_to_thread(func, *args, **kwargs):  # noqa: ANN002, ANN003
        return func(*args, **kwargs)

    async def _fake_sleep_or_stop(stop_event, seconds):  # noqa: ANN001
        delays.append(float(seconds))
        if len(delays) >= 3:
            stop_event.set()

    async def _fake_sleep(seconds):  # noqa: ANN001
        return None

    monkeypatch.setattr(runtime.asyncio, "to_thread", _fake_to_thread)
    monkeypatch.setattr(runtime, "run_memory_intent_worker_once", lambda worker_id=None: next(results))
    monkeypatch.setattr(runtime, "_sleep_or_stop", _fake_sleep_or_stop)
    monkeypatch.setattr(runtime.asyncio, "sleep", _fake_sleep)

    async def _exercise() -> None:
        stop_event = asyncio.Event()
        await runtime._run_memory_intent_runtime_loop(stop_event)

    asyncio.run(_exercise())

    assert delays == [0.5, 1.0, 0.5]
