from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.exam_generation_job import ExamGenerationJob
from app.repositories import exam_generation_job_repo
from app.schemas.exam_generation import ExamGenerationJobCreateRequest, ExamQuestion, PaperContract, PaperTemplateRequest, QuestionEvidence, QuestionOption, ExamQualityReport
from app.services.exam_generation_service import ExamGenerationService
from app.services.exam_template_service import MAX_ACTIVE_JOBS_PER_USER


class _FakeAssetService:
    def __init__(self) -> None:
        self.client = self
        self.put_calls = []

    def ensure_bucket(self) -> None:
        return None

    def put_object(self, **kwargs):
        self.put_calls.append(kwargs)
        return None

    def register_existing_asset(self, **kwargs):
        return SimpleNamespace(id=11, object_key=kwargs["object_key"])


def _build_paper() -> PaperContract:
    return PaperContract(
        paper_title="测试试卷",
        dataset_ids=["kb-a"],
        generated_at="2026-03-11T00:00:00",
        questions=[
            ExamQuestion(
                question_id="Q001",
                question_type="single_choice",
                stem="根据资料回答",
                options=[QuestionOption(key="A", text="正确"), QuestionOption(key="B", text="错误")],
                answers=["A"],
                explanation="简短解析",
                evidence=[QuestionEvidence(dataset_id="kb-a", source_name="文档", excerpt="原文")],
            )
        ],
    )


def test_exam_generation_service_run_job_should_mark_succeeded(monkeypatch) -> None:
    engine = create_engine("sqlite:///:memory:")
    ExamGenerationJob.__table__.create(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    service = ExamGenerationService()
    job = service.create_job(
        db,
        user=SimpleNamespace(id=1, role="admin"),
        payload=ExamGenerationJobCreateRequest(dataset_ids=["kb-a"], template=PaperTemplateRequest(paper_title="测试试卷")),
    )

    @contextmanager
    def _fake_db_context():
        another = Session()
        try:
            yield another
        finally:
            another.close()

    monkeypatch.setattr("app.services.exam_generation_service.get_db_context", _fake_db_context)
    monkeypatch.setattr("app.services.exam_generation_service.generate_paper_contract", lambda template, dataset_ids: _build_paper())
    monkeypatch.setattr("app.services.exam_generation_service.evaluate_paper_contract", lambda paper: ExamQualityReport(passed=True))
    monkeypatch.setattr("app.services.pdf_render_service.render_exam_pdf", lambda paper: b"%PDF-1.4\nmock")
    monkeypatch.setattr("app.services.exam_generation_service.get_asset_service", lambda: _FakeAssetService())

    service.run_job(job.id)

    detail = service.get_job(db, user=SimpleNamespace(id=1), job_id=job.id)
    assert detail.status == "succeeded"
    assert detail.asset_id == 11
    assert detail.download_url == f"/api/v1/exam-admin/jobs/{job.id}/download"

    db.close()
    engine.dispose()


def test_exam_generation_service_create_job_should_reject_non_admin() -> None:
    engine = create_engine("sqlite:///:memory:")
    ExamGenerationJob.__table__.create(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    service = ExamGenerationService()

    with pytest.raises(HTTPException) as exc_info:
        service.create_job(
            db,
            user=SimpleNamespace(id=1, role="user"),
            payload=ExamGenerationJobCreateRequest(dataset_ids=["kb-a"], template=PaperTemplateRequest(paper_title="测试试卷")),
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "需要管理员权限"

    db.close()
    engine.dispose()


def test_exam_generation_service_create_job_should_reject_parallel_limit(monkeypatch) -> None:
    engine = create_engine("sqlite:///:memory:")
    ExamGenerationJob.__table__.create(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    service = ExamGenerationService()
    monkeypatch.setattr(exam_generation_job_repo, "count_active_jobs_by_user", lambda db, user_id: MAX_ACTIVE_JOBS_PER_USER)

    with pytest.raises(HTTPException) as exc_info:
        service.create_job(
            db,
            user=SimpleNamespace(id=1, role="admin"),
            payload=ExamGenerationJobCreateRequest(dataset_ids=["kb-a"], template=PaperTemplateRequest(paper_title="测试试卷")),
        )

    assert exc_info.value.status_code == 429
    assert f"进行中的任务数已达到上限 {MAX_ACTIVE_JOBS_PER_USER}" == exc_info.value.detail

    db.close()
    engine.dispose()


def test_exam_generation_service_list_jobs_should_replay_download_url_from_history() -> None:
    engine = create_engine("sqlite:///:memory:")
    ExamGenerationJob.__table__.create(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    service = ExamGenerationService()
    job = exam_generation_job_repo.create_job(
        db,
        user_id=1,
        title="历史试卷",
        dataset_ids=["kb-a", "kb-b"],
        request_snapshot={"paper_title": "历史试卷"},
    )
    exam_generation_job_repo.mark_succeeded(
        db,
        job,
        result_payload={"download_url": f"/api/v1/exam-admin/jobs/{job.id}/download"},
        asset_id=12,
        minio_object_key="1/exam-job-1/exports/history.pdf",
    )

    jobs = service.list_jobs(db, user=SimpleNamespace(id=1), limit=10)

    assert len(jobs) == 1
    assert jobs[0].title == "历史试卷"
    assert jobs[0].dataset_ids == ["kb-a", "kb-b"]
    assert jobs[0].download_url == f"/api/v1/exam-admin/jobs/{job.id}/download"

    db.close()
    engine.dispose()
