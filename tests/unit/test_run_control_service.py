"""RunControlService 单元测试。"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.models.chat_run import ChatRunStatus
from app.services.run_control_service import (
    RunControlService,
    RunPermissionDeniedError,
)


def _build_service() -> RunControlService:
    """构造启用 run_control 的隔离实例。"""

    return RunControlService(
        enable_override=True,
        stopped_event_override=True,
        orphan_timeout_seconds=3,
    )


def test_create_run_and_get_active_run() -> None:
    """创建 run 后应可通过 active_run 取回。"""

    svc = _build_service()

    created = svc.create_run(thread_id="thread-loan", user_id=101)
    active = svc.get_active_run(thread_id="thread-loan", user_id=101)

    assert created.run_id.startswith("run_")
    assert created.status == ChatRunStatus.RUNNING.value
    assert active is not None
    assert active.run_id == created.run_id


def test_cancel_run_idempotent_semantics() -> None:
    """取消接口应支持幂等语义。"""

    svc = _build_service()
    created = svc.create_run(thread_id="thread-deposit", user_id=202)

    first = svc.cancel_run(
        run_id=created.run_id,
        requester_user_id=202,
        reason="user_cancelled",
    )
    second = svc.cancel_run(
        run_id=created.run_id,
        requester_user_id=202,
        reason="user_cancelled",
    )

    assert first.accepted is True
    assert first.idempotent is False
    assert first.status == ChatRunStatus.STOPPING.value

    assert second.accepted is True
    assert second.idempotent is True
    assert second.status == ChatRunStatus.STOPPING.value


def test_cancel_run_permission_denied_for_other_user() -> None:
    """非管理员且非归属用户取消应被拒绝。"""

    svc = _build_service()
    created = svc.create_run(thread_id="thread-branch", user_id=301)

    with pytest.raises(RunPermissionDeniedError):
        svc.cancel_run(
            run_id=created.run_id,
            requester_user_id=999,
            is_admin=False,
        )


def test_mark_stopped_blocks_resume() -> None:
    """run 进入 stopped 后必须阻断 resume。"""

    svc = _build_service()
    created = svc.create_run(thread_id="thread-retail", user_id=401)

    svc.cancel_run(run_id=created.run_id, requester_user_id=401, reason="user_cancelled")
    stopped = svc.mark_stopped(run_id=created.run_id, reason="user_cancelled")

    assert stopped is not None
    assert stopped.status == ChatRunStatus.STOPPED.value
    assert svc.can_resume_run(created.run_id) is False


def test_recover_active_runs_cleanup_orphan() -> None:
    """超时 active_run 应在恢复阶段清理为 orphan/stopped。"""

    svc = _build_service()
    created = svc.create_run(thread_id="thread-corp", user_id=501)

    snapshot = svc.get_run(created.run_id)
    assert snapshot is not None
    # 强制回拨更新时间，模拟孤儿 run
    snapshot.updated_at = datetime.now() - timedelta(seconds=30)
    svc._sync_memory(snapshot)  # noqa: SLF001 - 测试场景需要直接注入状态

    cleaned = svc.recover_active_runs(now=datetime.now())

    assert len(cleaned) == 1
    assert cleaned[0].run_id == created.run_id
    assert cleaned[0].status == ChatRunStatus.STOPPED.value
    assert cleaned[0].cancel_reason in {"orphan_cleanup", "cancel_timeout"}
