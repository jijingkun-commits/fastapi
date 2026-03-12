"""AI 出题默认模板服务。"""
from __future__ import annotations

import logging
from typing import Any

import requests

from app.schemas.exam_generation import DatasetOption, PaperTemplateRequest
from app.core import config as app_config

MAX_TOTAL_QUESTIONS = 100
MAX_ACTIVE_JOBS_PER_USER = 3
DATASET_METADATA_TIMEOUT_SECONDS = 10

logger = logging.getLogger(__name__)


def build_default_template() -> PaperTemplateRequest:
    return PaperTemplateRequest(
        paper_title="AI 生成试卷",
        single_choice_count=5,
        multiple_choice_count=3,
        judge_count=3,
        short_answer_count=2,
    )


def _configured_dataset_ids() -> list[str]:
    return list(app_config.RAGFLOW_DATASET_IDS or ([] if not app_config.RAGFLOW_DATASET_ID else [app_config.RAGFLOW_DATASET_ID]))


def _extract_dataset_items(payload: Any) -> list[dict[str, Any]]:
    data = payload.get("data") if isinstance(payload, dict) else None
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        for key in ("items", "records", "list", "datasets"):
            value = data.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


def _fetch_dataset_label_map(dataset_ids: list[str]) -> dict[str, str]:
    if not dataset_ids or not app_config.RAGFLOW_API_KEY:
        return {}

    try:
        response = requests.get(
            f"{app_config.RAGFLOW_API_URL}/datasets",
            headers={"Authorization": f"Bearer {app_config.RAGFLOW_API_KEY}"},
            timeout=DATASET_METADATA_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        logger.warning("exam_template_dataset_metadata_unavailable: %s", exc)
        return {}
    except ValueError as exc:
        logger.warning("exam_template_dataset_metadata_invalid_json: %s", exc)
        return {}

    labels: dict[str, str] = {}
    for item in _extract_dataset_items(payload):
        dataset_id = str(item.get("id") or "").strip()
        if not dataset_id or dataset_id not in dataset_ids:
            continue
        label = str(item.get("name") or item.get("title") or item.get("description") or dataset_id).strip() or dataset_id
        labels[dataset_id] = label
    return labels


def get_dataset_label_map(dataset_ids: list[str]) -> dict[str, str]:
    normalized = [str(item).strip() for item in dataset_ids if str(item).strip()]
    if not normalized:
        return {}
    return _fetch_dataset_label_map(normalized)


def resolve_dataset_labels(dataset_ids: list[str], *, label_map: dict[str, str] | None = None) -> list[str]:
    normalized = [str(item).strip() for item in dataset_ids if str(item).strip()]
    if not normalized:
        return []
    effective_map = label_map if label_map is not None else get_dataset_label_map(normalized)
    return [effective_map.get(dataset_id, dataset_id) for dataset_id in normalized]


def list_available_datasets() -> list[DatasetOption]:
    dataset_ids = _configured_dataset_ids()
    label_map = get_dataset_label_map(dataset_ids)
    return [DatasetOption(dataset_id=item, label=label_map.get(item, item)) for item in dataset_ids]
