"""用户记忆意图 Worker 服务（中文注释）。"""

from __future__ import annotations

from datetime import datetime
from typing import Callable

from sqlalchemy.orm import Session

from app.models.user_memory_intent_job import UserMemoryIntentJob
from app.repositories import user_memory_intent_job_repo


def run_once(
    db: Session,
    *,
    worker_id: str,
    process_job: Callable[[UserMemoryIntentJob], None],
    lease_seconds: int = user_memory_intent_job_repo.DEFAULT_WORKER_LEASE_SECONDS,
    max_attempts: int = user_memory_intent_job_repo.DEFAULT_MAX_ATTEMPTS,
    retry_base_seconds: int = user_memory_intent_job_repo.DEFAULT_RETRY_BASE_SECONDS,
    retry_recover_limit: int = user_memory_intent_job_repo.DEFAULT_RETRY_RECOVER_LIMIT,
    now: datetime | None = None,
) -> dict[str, object]:
    """执行一轮 Worker 消费：回捞重试、抢占任务、推进状态机。"""

    current_time = now or datetime.now()
    recovered_count = user_memory_intent_job_repo.promote_retryable_failed(
        db,
        now=current_time,
        limit=retry_recover_limit,
    )
    job = user_memory_intent_job_repo.claim_pending(
        db,
        worker_id=worker_id,
        lease_seconds=lease_seconds,
        now=current_time,
    )
    if job is None:
        return {
            "status": "idle",
            "job_id": None,
            "recovered_count": int(recovered_count),
        }

    try:
        process_job(job)
        finished_time = now or datetime.now()
        finished = user_memory_intent_job_repo.mark_succeeded(
            db,
            job_id=int(job.id),
            worker_id=worker_id,
            now=finished_time,
        )
        db.commit()
        resolved = finished or job
        return {
            "status": str(resolved.status),
            "job_id": int(resolved.id),
            "recovered_count": int(recovered_count),
        }
    except Exception as process_error:
        try:
            failed_time = now or datetime.now()
            failed = user_memory_intent_job_repo.mark_failed(
                db,
                job_id=int(job.id),
                worker_id=worker_id,
                error_message=str(process_error),
                max_attempts=max_attempts,
                base_retry_seconds=retry_base_seconds,
                now=failed_time,
            )
            db.commit()
        except Exception:
            db.rollback()
            raise

        resolved = failed or job
        return {
            "status": str(resolved.status),
            "job_id": int(resolved.id),
            "recovered_count": int(recovered_count),
            "error": str(process_error),
        }


class MemoryIntentWorkerService:
    """记忆意图 Worker 轻量服务封装。"""

    def __init__(
        self,
        *,
        worker_id: str,
        lease_seconds: int = user_memory_intent_job_repo.DEFAULT_WORKER_LEASE_SECONDS,
        max_attempts: int = user_memory_intent_job_repo.DEFAULT_MAX_ATTEMPTS,
        retry_base_seconds: int = user_memory_intent_job_repo.DEFAULT_RETRY_BASE_SECONDS,
        retry_recover_limit: int = user_memory_intent_job_repo.DEFAULT_RETRY_RECOVER_LIMIT,
    ) -> None:
        self.worker_id = str(worker_id)
        self.lease_seconds = int(lease_seconds)
        self.max_attempts = int(max_attempts)
        self.retry_base_seconds = int(retry_base_seconds)
        self.retry_recover_limit = int(retry_recover_limit)

    def run_once(
        self,
        db: Session,
        *,
        process_job: Callable[[UserMemoryIntentJob], None],
        now: datetime | None = None,
    ) -> dict[str, object]:
        """按实例配置执行一轮消费。"""

        return run_once(
            db,
            worker_id=self.worker_id,
            process_job=process_job,
            lease_seconds=self.lease_seconds,
            max_attempts=self.max_attempts,
            retry_base_seconds=self.retry_base_seconds,
            retry_recover_limit=self.retry_recover_limit,
            now=now,
        )
