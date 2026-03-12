"""AI 出题服务（中文注释）。"""
from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from io import BytesIO
from typing import Any
from uuid import uuid4

from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from app.ai.workflow.exam_generation_workflow import evaluate_paper_contract, generate_paper_contract
from app.api.deps import get_admin_user
from app.core import config as app_config
from app.db.session import get_db_context
from app.models.chat_asset import AssetType
from app.repositories import exam_generation_job_repo
from app.schemas.exam_generation import (
    ExamGenerationJobCreateRequest,
    ExamGenerationJobDetail,
    ExamGenerationJobSummary,
)
from app.services.asset_service import get_asset_service
from app.services.exam_template_service import (
    MAX_ACTIVE_JOBS_PER_USER,
    MAX_TOTAL_QUESTIONS,
    build_default_template,
    list_available_datasets,
    get_dataset_label_map,
    resolve_dataset_labels,
)

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class AccessPolicyResult:
    allowed: bool
    reason: str = ""


class ExamGenerationService:
    def build_template_payload(self) -> dict[str, Any]:
        return {
            "template": jsonable_encoder(build_default_template()),
            "available_datasets": jsonable_encoder(list_available_datasets()),
            "limits": {
                "max_total_questions": MAX_TOTAL_QUESTIONS,
                "max_active_jobs_per_user": MAX_ACTIVE_JOBS_PER_USER,
            },
        }

    def enforce_access_policy(self, db: Session, *, user: Any, total_question_count: int) -> AccessPolicyResult:
        if getattr(user, "role", None) != "admin":
            return AccessPolicyResult(False, "需要管理员权限")
        if total_question_count <= 0 or total_question_count > MAX_TOTAL_QUESTIONS:
            return AccessPolicyResult(False, f"总题数需在 1 到 {MAX_TOTAL_QUESTIONS} 之间")
        active_jobs = exam_generation_job_repo.count_active_jobs_by_user(db, int(user.id))
        if active_jobs >= MAX_ACTIVE_JOBS_PER_USER:
            return AccessPolicyResult(False, f"进行中的任务数已达到上限 {MAX_ACTIVE_JOBS_PER_USER}")
        return AccessPolicyResult(True)

    def create_job(self, db: Session, *, user: Any, payload: ExamGenerationJobCreateRequest) -> ExamGenerationJobSummary:
        policy = self.enforce_access_policy(db, user=user, total_question_count=payload.template.total_question_count)
        if not policy.allowed:
            if "上限" in policy.reason:
                status_code = 429
            elif "总题数" in policy.reason:
                status_code = 400
            else:
                status_code = 403
            raise HTTPException(status_code=status_code, detail=policy.reason)

        job = exam_generation_job_repo.create_job(
            db,
            user_id=int(user.id),
            title=payload.template.paper_title,
            dataset_ids=payload.dataset_ids,
            request_snapshot=jsonable_encoder(payload),
        )
        dataset_label_map = get_dataset_label_map(list(job.dataset_ids or []))
        return self._to_summary(job, dataset_label_map=dataset_label_map)

    def list_jobs(self, db: Session, *, user: Any, limit: int = 50) -> list[ExamGenerationJobSummary]:
        jobs = exam_generation_job_repo.list_jobs_by_user(db, int(user.id), limit=min(max(limit, 1), 100))
        dataset_label_map = get_dataset_label_map([dataset_id for job in jobs for dataset_id in list(job.dataset_ids or [])])
        return [self._to_summary(job, dataset_label_map=dataset_label_map) for job in jobs]

    def get_job(self, db: Session, *, user: Any, job_id: int) -> ExamGenerationJobDetail:
        job = exam_generation_job_repo.get_job_by_id(db, job_id)
        if job is None or int(job.user_id) != int(user.id):
            raise HTTPException(status_code=404, detail="任务不存在")
        dataset_label_map = get_dataset_label_map(list(job.dataset_ids or []))
        return self._to_detail(job, dataset_label_map=dataset_label_map)

    def run_job(self, job_id: int) -> None:
        with get_db_context() as db:
            job = exam_generation_job_repo.get_job_by_id(db, job_id)
            if job is None:
                logger.warning("exam_generation_job_missing: job_id=%s", job_id)
                return
            exam_generation_job_repo.mark_running(db, job)
            try:
                payload = ExamGenerationJobCreateRequest.model_validate(job.request_snapshot)
                paper = generate_paper_contract(payload.template, payload.dataset_ids)
                quality_report = evaluate_paper_contract(paper)
                if not quality_report.passed:
                    raise ValueError("题单未通过质量门禁")
                from app.services.pdf_render_service import render_exam_pdf
                pdf_bytes = render_exam_pdf(paper)
                asset = self._save_pdf_asset(db=db, user_id=int(job.user_id), job_id=int(job.id), title=job.title, pdf_bytes=pdf_bytes)
                result_payload = {
                    "status": "succeeded",
                    "request_snapshot": jsonable_encoder(payload),
                    "paper_contract": jsonable_encoder(paper),
                    "quality_report": jsonable_encoder(quality_report),
                    "asset_id": asset.id,
                    "minio_object_key": asset.object_key,
                    "download_url": f"/api/v1/exam-admin/jobs/{job.id}/download",
                }
                exam_generation_job_repo.mark_succeeded(
                    db,
                    job,
                    result_payload=result_payload,
                    asset_id=int(asset.id),
                    minio_object_key=str(asset.object_key),
                )
            except Exception as exc:
                logger.exception("exam_generation_job_failed: job_id=%s", job_id)
                exam_generation_job_repo.mark_failed(
                    db,
                    job,
                    error_message=str(exc),
                    result_payload={"status": "failed", "error_message": str(exc)},
                )

    def _save_pdf_asset(self, *, db: Session, user_id: int, job_id: int, title: str, pdf_bytes: bytes):
        safe_title = "-".join(part for part in str(title).strip().split() if part) or f"exam-{job_id}"
        object_key = f"{user_id}/exam-job-{job_id}/exports/{uuid4().hex}.pdf"
        asset_service = get_asset_service()
        asset_service.ensure_bucket()
        asset_service.client.put_object(
            bucket_name=app_config.MINIO_BUCKET_ASSETS,
            object_name=object_key,
            data=BytesIO(pdf_bytes),
            length=len(pdf_bytes),
            content_type="application/pdf",
        )
        return asset_service.register_existing_asset(
            db=db,
            object_key=object_key,
            chat_id=f"exam-job-{job_id}",
            qa_record_id=0,
            user_id=user_id,
            asset_type=AssetType.EXPORT,
            file_name=f"{safe_title}.pdf",
        )

    def _to_summary(self, job, *, dataset_label_map: dict[str, str] | None = None) -> ExamGenerationJobSummary:
        result_payload = job.result_payload or {}
        dataset_ids = list(job.dataset_ids or [])
        return ExamGenerationJobSummary(
            id=int(job.id),
            user_id=int(job.user_id),
            title=str(job.title),
            status=str(job.status),
            dataset_ids=dataset_ids,
            dataset_labels=resolve_dataset_labels(dataset_ids, label_map=dataset_label_map),
            asset_id=int(job.asset_id) if job.asset_id is not None else None,
            minio_object_key=job.minio_object_key,
            download_url=result_payload.get("download_url"),
            error_message=job.error_message,
            created_at=job.created_at,
            updated_at=job.updated_at,
            started_at=job.started_at,
            finished_at=job.finished_at,
        )

    def _to_detail(self, job, *, dataset_label_map: dict[str, str] | None = None) -> ExamGenerationJobDetail:
        summary = self._to_summary(job, dataset_label_map=dataset_label_map)
        return ExamGenerationJobDetail(
            **summary.model_dump(),
            request_snapshot=dict(job.request_snapshot or {}),
            result_payload=dict(job.result_payload or {}),
        )


_service = ExamGenerationService()


def get_exam_generation_service() -> ExamGenerationService:
    return _service
