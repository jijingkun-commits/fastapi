"""LLM 场景治理管理接口单元测试。"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints import llm_admin_api


@patch("app.api.v1.endpoints.llm_admin_api.LLMSceneService.export_scene_payload")
@patch("app.api.v1.endpoints.llm_admin_api.LLMSceneService.refresh_cache")
def test_list_llm_scenes_returns_payload(
    mock_refresh,
    mock_export,
):
    """场景列表接口应返回服务层缓存输出。"""

    mock_export.return_value = [
        {
            "scene_key": "app.ai.intent_classifier.classify_intent",
            "scene_name": "意图分类",
            "route_group": "lightweight",
            "scene_type": "text",
            "default_model_id": 1,
            "default_model_code": "qwen-plus",
            "is_active": True,
            "description": "轻量意图识别",
        }
    ]

    resp = llm_admin_api.list_llm_scenes(db=MagicMock())

    assert len(resp) == 1
    assert resp[0].scene_key == "app.ai.intent_classifier.classify_intent"
    mock_refresh.assert_called_once()
    mock_export.assert_called_once()


@patch("app.api.v1.endpoints.llm_admin_api.LLMSceneService.update_scene")
def test_update_llm_scene_success(
    mock_update_scene,
):
    """更新场景接口成功返回更新结果。"""

    mock_update_scene.return_value = MagicMock(
        scene_key="app.ai.intent_classifier.classify_intent",
        default_model_code="qwen-plus",
        is_active=True,
    )

    request = llm_admin_api.SceneUpdateRequest(default_model_code="qwen-plus")
    resp = llm_admin_api.update_llm_scene(
        scene_key="app.ai.intent_classifier.classify_intent",
        request=request,
        db=MagicMock(),
    )

    assert resp["message"] == "场景配置已更新"
    assert resp["default_model_code"] == "qwen-plus"


def test_update_llm_scene_requires_payload():
    """空更新请求应被拒绝。"""

    request = llm_admin_api.SceneUpdateRequest()

    with pytest.raises(HTTPException) as exc:
        llm_admin_api.update_llm_scene(
            scene_key="app.ai.intent_classifier.classify_intent",
            request=request,
            db=MagicMock(),
        )

    assert exc.value.status_code == 400
