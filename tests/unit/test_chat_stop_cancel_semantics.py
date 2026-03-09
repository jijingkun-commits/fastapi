"""Run cancel semantics for strong-stop flow."""

from __future__ import annotations

from app.models.chat_run import ChatRunStatus
from app.services.run_control_service import RunControlService


def _build_service(*, enabled: bool) -> RunControlService:
    return RunControlService(
        enable_override=enabled,
        stopped_event_override=True,
        orphan_timeout_seconds=10,
    )


def test_cancel_run_returns_disabled_result_when_run_control_off() -> None:
    svc = _build_service(enabled=False)

    result = svc.cancel_run(
        run_id="run-disabled-001",
        requester_user_id=7,
        reason="user_cancelled",
        cancel_mode="hard",
    )

    assert result.accepted is False
    assert result.status == "disabled"
    assert result.idempotent is True
    assert result.reason == "run_control_disabled"
    assert result.thread_id == ""


def test_cancel_run_marks_running_to_stopped_with_hard_mode() -> None:
    svc = _build_service(enabled=True)
    created = svc.create_run(thread_id="thread-strong-stop", user_id=9)

    result = svc.cancel_run(
        run_id=created.run_id,
        requester_user_id=9,
        reason="user_cancelled",
        cancel_mode="hard",
    )
    snapshot = svc.get_run(created.run_id)

    assert result.accepted is True
    assert result.idempotent is False
    assert result.status == ChatRunStatus.STOPPED.value
    assert result.reason == "user_cancelled"
    assert snapshot is not None
    assert snapshot.status == ChatRunStatus.STOPPED.value
    assert snapshot.cancel_mode == "hard"
    assert snapshot.cancel_reason == "user_cancelled"



def test_hard_cancelled_run_drops_from_active_runs() -> None:
    svc = _build_service(enabled=True)
    created = svc.create_run(thread_id="thread-strong-stop-active", user_id=9)

    svc.cancel_run(
        run_id=created.run_id,
        requester_user_id=9,
        reason="user_cancelled",
        cancel_mode="hard",
    )

    active_runs = svc.list_active_runs_by_user(user_id=9)
    assert all(run.run_id != created.run_id for run in active_runs)
