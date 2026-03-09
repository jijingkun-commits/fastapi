"""记忆意图异步运行时。"""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import suppress
from typing import Any

from fastapi import FastAPI
from sqlalchemy.orm import Session

from app.ai.llm_util import get_scene_llm
from app.ai.scene_registry import SCENE_KEY_INTENT_CLASSIFIER
from app.core.config import ENABLE_DOCUMENT_MEMORY, MEMORY_INTENT_ASYNC_ENABLED
from app.db.session import get_db_context
from app.models.user_memory_intent_job import UserMemoryIntentJob
from app.services import memory_intent_resolver_service, memory_intent_worker_service
from app.services.config_resolver import ConfigResolver
from app.services.document_memory_service import flush_canonical_memory

logger = logging.getLogger(__name__)

_TRUE_VALUES = {"1", "true", "yes", "on"}
_RUNTIME_TASK_ATTR = "memory_intent_runtime_task"
_RUNTIME_STOP_ATTR = "memory_intent_runtime_stop_event"
_IDLE_POLL_SECONDS = 0.5
_ERROR_RETRY_SECONDS = 1.0
_SHUTDOWN_TIMEOUT_SECONDS = 5.0


def _is_enabled_env(env_name: str, fallback: bool) -> bool:
    value = os.getenv(env_name)
    if value is None:
        return bool(fallback)
    return value.strip().lower() in _TRUE_VALUES


def is_memory_intent_runtime_enabled() -> bool:
    """仅在文档记忆与异步判定同时开启时启动运行时。"""

    document_enabled = _is_enabled_env("ENABLE_DOCUMENT_MEMORY", ENABLE_DOCUMENT_MEMORY)
    async_enabled = _is_enabled_env("MEMORY_INTENT_ASYNC_ENABLED", MEMORY_INTENT_ASYNC_ENABLED)
    try:
        document_enabled = _is_enabled_env(
            "ENABLE_DOCUMENT_MEMORY",
            bool(ConfigResolver.get_bool("feature.enable_document_memory", document_enabled)),
        )
        async_enabled = _is_enabled_env(
            "MEMORY_INTENT_ASYNC_ENABLED",
            bool(ConfigResolver.get_bool("memory.intent_async_enabled", async_enabled)),
        )
    except Exception:
        logger.warning("memory_intent_runtime_flag_resolve_failed", exc_info=True)
    return bool(document_enabled and async_enabled)


def _build_worker_id() -> str:
    return f"memory-intent-runtime-{os.getpid()}"


def process_memory_intent_job(db: Session, *, job: UserMemoryIntentJob) -> None:
    """处理单条记忆意图任务。"""

    user_id = int(getattr(job, "user_id", 0) or 0)
    if user_id <= 0:
        raise ValueError("memory intent job 缺少 user_id")

    payload = dict(getattr(job, "payload_json", {}) or {})
    user_text = str(payload.get("user_text") or "").strip()
    if not user_text:
        raise ValueError("memory intent job 缺少 user_text")

    source_thread_id = str(payload.get("source_thread_id") or "").strip()
    if not source_thread_id:
        raise ValueError("memory intent job 缺少 source_thread_id")

    raw_source_message_id = payload.get("source_message_id")
    source_message_id = int(raw_source_message_id) if raw_source_message_id is not None else None

    llm = get_scene_llm(scene_key=SCENE_KEY_INTENT_CLASSIFIER, internal=True)
    resolved = memory_intent_resolver_service.resolve(
        db,
        llm=llm,
        user_text=user_text,
        user_id=user_id,
        thread_id=source_thread_id,
        source_message_id=source_message_id,
    )
    decision_contract = resolved.get("persistence_contract")
    if not isinstance(decision_contract, dict):
        logger.info(
            "memory_intent_job_no_persistence_contract: job_id=%s, reason_code=%s, status=%s",
            getattr(job, "id", None),
            resolved.get("reason_code"),
            resolved.get("resolution_status"),
        )
        return

    persisted_count = flush_canonical_memory(
        db,
        user_id=user_id,
        source_thread_id=source_thread_id,
        source_message_id=source_message_id,
        source="memory",
        decision_contract=decision_contract,
        manage_transaction=False,
    )
    logger.info(
        "memory_intent_job_processed: job_id=%s, user_id=%s, persisted_count=%s, reason_code=%s",
        getattr(job, "id", None),
        user_id,
        persisted_count,
        decision_contract.get("reason_code") if isinstance(decision_contract, dict) else None,
    )


def run_memory_intent_worker_once(*, worker_id: str | None = None) -> dict[str, object]:
    """使用独立数据库会话执行一轮记忆 worker。"""

    resolved_worker_id = str(worker_id or _build_worker_id()).strip() or _build_worker_id()
    with get_db_context() as db:
        return memory_intent_worker_service.run_once(
            db,
            worker_id=resolved_worker_id,
            process_job=lambda job: process_memory_intent_job(db, job=job),
        )


async def _sleep_or_stop(stop_event: asyncio.Event, seconds: float) -> None:
    try:
        await asyncio.wait_for(stop_event.wait(), timeout=max(0.0, float(seconds)))
    except asyncio.TimeoutError:
        return


async def _run_memory_intent_runtime_loop(stop_event: asyncio.Event) -> None:
    worker_id = _build_worker_id()
    while not stop_event.is_set():
        try:
            result = await asyncio.to_thread(run_memory_intent_worker_once, worker_id=worker_id)
        except Exception:
            logger.exception("memory_intent_runtime_loop_failed")
            await _sleep_or_stop(stop_event, _ERROR_RETRY_SECONDS)
            continue

        status = str(result.get("status") or "").strip().lower()
        if status in {"idle", "circuit_open"}:
            await _sleep_or_stop(stop_event, _IDLE_POLL_SECONDS)
            continue

        await asyncio.sleep(0)


def start_memory_intent_runtime(app: FastAPI) -> asyncio.Task[Any] | None:
    """按开关启动记忆异步 worker。"""

    if not is_memory_intent_runtime_enabled():
        logger.info("memory_intent_runtime_disabled")
        return None

    current_task = getattr(app.state, _RUNTIME_TASK_ATTR, None)
    if current_task is not None and not current_task.done():
        return current_task

    stop_event = asyncio.Event()
    task = asyncio.create_task(_run_memory_intent_runtime_loop(stop_event), name="memory-intent-runtime")
    setattr(app.state, _RUNTIME_STOP_ATTR, stop_event)
    setattr(app.state, _RUNTIME_TASK_ATTR, task)
    logger.info("memory_intent_runtime_started")
    return task


async def stop_memory_intent_runtime(app: FastAPI) -> None:
    """停止记忆异步 worker。"""

    stop_event = getattr(app.state, _RUNTIME_STOP_ATTR, None)
    task = getattr(app.state, _RUNTIME_TASK_ATTR, None)
    if stop_event is not None:
        stop_event.set()
    if task is None:
        return

    try:
        await asyncio.wait_for(task, timeout=_SHUTDOWN_TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
    finally:
        setattr(app.state, _RUNTIME_STOP_ATTR, None)
        setattr(app.state, _RUNTIME_TASK_ATTR, None)
        logger.info("memory_intent_runtime_stopped")
