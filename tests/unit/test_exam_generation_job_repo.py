from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.exam_generation_job import ExamGenerationJob
from app.repositories import exam_generation_job_repo


def test_exam_generation_job_repo_roundtrip() -> None:
    engine = create_engine("sqlite:///:memory:")
    ExamGenerationJob.__table__.create(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        job = exam_generation_job_repo.create_job(
            db,
            user_id=1,
            title="测试试卷",
            dataset_ids=["kb-a"],
            request_snapshot={"foo": "bar"},
        )
        jobs = exam_generation_job_repo.list_jobs_by_user(db, 1)
        assert len(jobs) == 1
        assert jobs[0].id == job.id

        exam_generation_job_repo.mark_running(db, job)
        assert exam_generation_job_repo.count_active_jobs_by_user(db, 1) == 1

        exam_generation_job_repo.mark_succeeded(
            db,
            job,
            result_payload={"status": "succeeded"},
            asset_id=9,
            minio_object_key="1/exam/exports/demo.pdf",
        )
        refreshed = exam_generation_job_repo.get_job_by_id(db, int(job.id))
        assert refreshed is not None
        assert refreshed.status == "succeeded"
        assert refreshed.asset_id == 9
    finally:
        db.close()
        engine.dispose()
