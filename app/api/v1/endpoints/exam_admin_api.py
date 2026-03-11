"""AI 出题后台 API（中文注释）。"""
from __future__ import annotations

import logging
from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_admin_user
from app.db.session import get_db
from app.models.user import User
from app.repositories import exam_generation_job_repo
from app.schemas.exam_generation import (
    ExamGenerationJobCreateRequest,
    ExamGenerationJobDetail,
    ExamGenerationJobSummary,
    ExamTemplateResponse,
)
from app.services.asset_service import get_asset_service
from app.services.exam_generation_service import ExamGenerationService, get_exam_generation_service
from app.core import config as app_config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/exam-admin", tags=["AI出题管理"])


@router.get("/template", response_model=ExamTemplateResponse)
def get_template(
    current_user: User = Depends(get_admin_user),
    service: ExamGenerationService = Depends(get_exam_generation_service),
):
    return service.build_template_payload()


@router.post("/jobs", response_model=ExamGenerationJobSummary)
def create_job(
    payload: ExamGenerationJobCreateRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
    service: ExamGenerationService = Depends(get_exam_generation_service),
):
    job = service.create_job(db, user=current_user, payload=payload)
    background_tasks.add_task(service.run_job, int(job.id))
    return job


@router.get("/jobs", response_model=List[ExamGenerationJobSummary])
def list_jobs(
    limit: int = 50,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
    service: ExamGenerationService = Depends(get_exam_generation_service),
):
    return service.list_jobs(db, user=current_user, limit=limit)


@router.get("/jobs/{job_id}", response_model=ExamGenerationJobDetail)
def get_job(
    job_id: int,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
    service: ExamGenerationService = Depends(get_exam_generation_service),
):
    return service.get_job(db, user=current_user, job_id=job_id)


@router.get("/jobs/{job_id}/download")
def download_export(
    job_id: int,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    job = exam_generation_job_repo.get_job_by_id(db, job_id)
    if job is None or int(job.user_id) != int(current_user.id):
        raise HTTPException(status_code=404, detail="任务不存在")
    if job.status != "succeeded" or not job.minio_object_key:
        raise HTTPException(status_code=409, detail="PDF 尚未生成")

    asset_service = get_asset_service()
    response = asset_service.client.get_object(
        bucket_name=app_config.MINIO_BUCKET_ASSETS,
        object_name=job.minio_object_key,
    )

    def _iterfile():
        try:
            for chunk in response.stream(32 * 1024):
                yield chunk
        finally:
            response.close()
            response.release_conn()

    filename = f"exam-job-{job.id}.pdf"
    return StreamingResponse(
        _iterfile(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
