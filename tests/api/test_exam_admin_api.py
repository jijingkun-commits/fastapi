from __future__ import annotations

from io import BytesIO
from types import SimpleNamespace

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_admin_user
from app.db.session import get_db
from app.api.v1.endpoints import exam_admin_api
from app.schemas.exam_generation import PaperTemplateRequest


@pytest.fixture()
def admin_client():
    app = FastAPI()
    app.include_router(
        exam_admin_api.router,
        prefix="/api/v1",
        dependencies=[Depends(get_admin_user)],
    )
    app.dependency_overrides[get_admin_user] = lambda: SimpleNamespace(id=1, role="admin", is_active=True)

    def _override_db():
        yield SimpleNamespace()

    app.dependency_overrides[get_db] = _override_db

    with TestClient(app) as client:
        yield client, app
    app.dependency_overrides.clear()


def test_exam_template_returns_default_payload(admin_client, monkeypatch):
    client, app = admin_client
    service_stub = SimpleNamespace(build_template_payload=lambda: {
        "template": PaperTemplateRequest(paper_title="默认试卷").model_dump(),
        "available_datasets": [{"dataset_id": "kb-a", "label": "kb-a"}],
        "limits": {"max_total_questions": 100, "max_active_jobs_per_user": 3},
    })
    app.dependency_overrides[exam_admin_api.get_exam_generation_service] = lambda: service_stub
    response = client.get("/api/v1/exam-admin/template")
    assert response.status_code == 200
    assert response.json()["template"]["paper_title"] == "默认试卷"


def test_exam_create_job_returns_job_summary(admin_client, monkeypatch):
    client, app = admin_client
    service_stub = SimpleNamespace(
        create_job=lambda db, user, payload: SimpleNamespace(
            id=1,
            user_id=1,
            title=payload.template.paper_title,
            status="queued",
            dataset_ids=payload.dataset_ids,
            asset_id=None,
            minio_object_key=None,
            download_url=None,
            error_message=None,
            created_at="2026-03-11T00:00:00",
            updated_at="2026-03-11T00:00:00",
            started_at=None,
            finished_at=None,
        ),
        run_job=lambda job_id: None,
    )
    app.dependency_overrides[exam_admin_api.get_exam_generation_service] = lambda: service_stub
    response = client.post(
        "/api/v1/exam-admin/jobs",
        json={"dataset_ids": ["kb-a"], "template": {"paper_title": "测试试卷", "single_choice_count": 1, "multiple_choice_count": 0, "judge_count": 0, "short_answer_count": 0, "difficulty_distribution": {"easy": 0.4, "medium": 0.4, "hard": 0.2}, "score_strategy": {"single_choice": 2, "multiple_choice": 3, "judge": 1, "short_answer": 10}, "answer_section_enabled": True, "answer_page_break": True, "answer_explanation_mode": "short"}},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "queued"


def test_exam_create_job_returns_limit_error_detail(admin_client):
    client, app = admin_client

    def _raise_limit(*args, **kwargs):
        from fastapi import HTTPException
        raise HTTPException(status_code=429, detail="进行中的任务数已达到上限 3")

    service_stub = SimpleNamespace(create_job=_raise_limit)
    app.dependency_overrides[exam_admin_api.get_exam_generation_service] = lambda: service_stub
    response = client.post(
        "/api/v1/exam-admin/jobs",
        json={"dataset_ids": ["kb-a"], "template": {"paper_title": "测试试卷", "single_choice_count": 1, "multiple_choice_count": 0, "judge_count": 0, "short_answer_count": 0, "difficulty_distribution": {"easy": 0.4, "medium": 0.4, "hard": 0.2}, "score_strategy": {"single_choice": 2, "multiple_choice": 3, "judge": 1, "short_answer": 10}, "answer_section_enabled": True, "answer_page_break": True, "answer_explanation_mode": "short"}},
    )
    assert response.status_code == 429
    assert response.json()["detail"] == "进行中的任务数已达到上限 3"


def test_exam_download_streams_pdf(admin_client, monkeypatch):
    client, app = admin_client
    monkeypatch.setattr(exam_admin_api.exam_generation_job_repo, 'get_job_by_id', lambda db, job_id: SimpleNamespace(id=job_id, user_id=1, status='succeeded', minio_object_key='1/exam-job-1/exports/demo.pdf', title='测试试卷'))

    class _Resp:
        headers = {"Content-Type": "application/pdf"}
        def stream(self, _: int):
            yield b"%PDF-1.4\nmock"
        def close(self):
            return None
        def release_conn(self):
            return None

    asset_service = SimpleNamespace(client=SimpleNamespace(get_object=lambda **kwargs: _Resp()))
    monkeypatch.setattr(exam_admin_api, 'get_asset_service', lambda: asset_service)
    response = client.get('/api/v1/exam-admin/jobs/1/download')
    assert response.status_code == 200
    assert response.content.startswith(b'%PDF-1.4')
