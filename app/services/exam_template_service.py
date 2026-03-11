"""AI 出题默认模板服务。"""
from __future__ import annotations

from app.schemas.exam_generation import DatasetOption, PaperTemplateRequest
from app.core import config as app_config

MAX_TOTAL_QUESTIONS = 100
MAX_ACTIVE_JOBS_PER_USER = 3


def build_default_template() -> PaperTemplateRequest:
    return PaperTemplateRequest(
        paper_title="AI 生成试卷",
        single_choice_count=5,
        multiple_choice_count=3,
        judge_count=3,
        short_answer_count=2,
    )


def list_available_datasets() -> list[DatasetOption]:
    dataset_ids = list(app_config.RAGFLOW_DATASET_IDS or ([] if not app_config.RAGFLOW_DATASET_ID else [app_config.RAGFLOW_DATASET_ID]))
    return [DatasetOption(dataset_id=item, label=item) for item in dataset_ids]
