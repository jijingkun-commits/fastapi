"""AI 出题任务 repo（中文注释）。"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models.exam_generation_job import ExamGenerationJob

ACTIVE_JOB_STATUSES = ("queued", "running")


def create_job(
    db: Session,
    *,
    user_id: int,
    title: str,
    dataset_ids: list[str],
    request_snapshot: dict,
) -> ExamGenerationJob:
    job = ExamGenerationJob(
        user_id=user_id,
        title=title,
        status="queued",
        dataset_ids=list(dataset_ids),
        request_snapshot=dict(request_snapshot),
        result_payload={},
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def get_job_by_id(db: Session, job_id: int) -> Optional[ExamGenerationJob]:
    return db.query(ExamGenerationJob).filter(ExamGenerationJob.id == job_id).first()


def list_jobs_by_user(db: Session, user_id: int, limit: int = 50) -> list[ExamGenerationJob]:
    return (
        db.query(ExamGenerationJob)
        .filter(ExamGenerationJob.user_id == user_id)
        .order_by(ExamGenerationJob.created_at.desc())
        .limit(limit)
        .all()
    )


def count_active_jobs_by_user(db: Session, user_id: int) -> int:
    return (
        db.query(ExamGenerationJob)
        .filter(ExamGenerationJob.user_id == user_id, ExamGenerationJob.status.in_(ACTIVE_JOB_STATUSES))
        .count()
    )


def mark_running(db: Session, job: ExamGenerationJob) -> ExamGenerationJob:
    now = datetime.now()
    job.status = "running"
    job.started_at = now
    job.updated_at = now
    db.commit()
    db.refresh(job)
    return job


def mark_succeeded(
    db: Session,
    job: ExamGenerationJob,
    *,
    result_payload: dict,
    asset_id: int,
    minio_object_key: str,
) -> ExamGenerationJob:
    now = datetime.now()
    job.status = "succeeded"
    job.result_payload = dict(result_payload)
    job.asset_id = asset_id
    job.minio_object_key = minio_object_key
    job.error_message = None
    job.finished_at = now
    job.updated_at = now
    db.commit()
    db.refresh(job)
    return job


def mark_failed(db: Session, job: ExamGenerationJob, *, error_message: str, result_payload: dict | None = None) -> ExamGenerationJob:
    now = datetime.now()
    job.status = "failed"
    job.error_message = error_message
    job.finished_at = now
    job.updated_at = now
    if result_payload is not None:
        job.result_payload = dict(result_payload)
    db.commit()
    db.refresh(job)
    return job
