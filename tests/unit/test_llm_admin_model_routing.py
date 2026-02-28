"""LLM 管理后台模型路由单元测试。"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints import llm_admin_api


@patch("app.api.v1.endpoints.llm_admin_api._get_route_group_model_for_routing")
@patch("app.api.v1.endpoints.llm_admin_api.LLMSceneService.refresh_cache")
def test_get_model_routing_all_rows_use_scene_binding(
    mock_refresh_scene_cache,
    mock_get_route_group_model,
):
    """模型路由总览应全部来自 scene_binding。"""

    mock_refresh_scene_cache.return_value = None
    mock_get_route_group_model.side_effect = [
        "gpt-5.2",
        "gpt-5.2",
        "qwen3.5-flash",
        "embedding-3",
        "qwen3-vl-flash-2026-01-22",
    ]

    routes = llm_admin_api.get_model_routing(db=MagicMock())

    assert len(routes) == 5
    assert all(route.source == "scene_binding" for route in routes)

    embedding_route = next(route for route in routes if route.scene == "Embedding")
    assert embedding_route.config_key == "embedding"
    assert embedding_route.current_model == "embedding-3"
    assert embedding_route.editable is True

    vision_route = next(route for route in routes if route.scene == "Vision")
    assert vision_route.config_key == "vision"
    assert vision_route.current_model == "qwen3-vl-flash-2026-01-22"
    assert vision_route.editable is True


@patch("app.api.v1.endpoints.llm_admin_api._refresh_llm_runtime_cache")
@patch("app.api.v1.endpoints.llm_admin_api.LLMSceneService.update_route_group_default_model")
def test_update_model_routing_updates_scene_binding_for_lightweight(
    mock_update_route_group,
    mock_refresh_llm_cache,
):
    """轻量路由更新应落到 t_llm_scene 分组绑定。"""

    request = llm_admin_api.ModelRoutingUpdateRequest(
        config_key="model_routing.lightweight",
        model_code="qwen3.5-flash",
    )
    model = SimpleNamespace(
        model_code="qwen3.5-flash",
        model_type="chat",
        is_default=False,
    )

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = model

    resp = llm_admin_api.update_model_routing(request, db)

    assert resp == {
        "message": "模型路由已更新",
        "config_key": "model_routing.lightweight",
        "model_code": "qwen3.5-flash",
    }
    mock_update_route_group.assert_called_once_with(
        db=db,
        route_group="lightweight",
        default_model_code="qwen3.5-flash",
    )
    mock_refresh_llm_cache.assert_called_once_with(db)


@patch("app.api.v1.endpoints.llm_admin_api._refresh_llm_runtime_cache")
@patch("app.api.v1.endpoints.llm_admin_api.LLMSceneService.update_route_group_default_model")
def test_update_model_routing_updates_scene_binding_for_embedding(
    mock_update_route_group,
    mock_refresh_llm_cache,
):
    """Embedding 路由更新应落到 embedding 分组。"""

    request = llm_admin_api.ModelRoutingUpdateRequest(
        config_key="embedding",
        model_code="embedding-3",
    )
    model = SimpleNamespace(
        model_code="embedding-3",
        model_type="embedding",
        is_default=False,
    )

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = model

    resp = llm_admin_api.update_model_routing(request, db)

    assert resp == {
        "message": "模型路由已更新",
        "config_key": "embedding",
        "model_code": "embedding-3",
    }
    mock_update_route_group.assert_called_once_with(
        db=db,
        route_group="embedding",
        default_model_code="embedding-3",
    )
    mock_refresh_llm_cache.assert_called_once_with(db)


@patch("app.api.v1.endpoints.llm_admin_api._refresh_llm_runtime_cache")
@patch("app.api.v1.endpoints.llm_admin_api.LLMSceneService.update_route_group_default_model")
def test_update_model_routing_updates_scene_binding_for_vision(
    mock_update_route_group,
    mock_refresh_llm_cache,
):
    """Vision 路由更新应落到 vision 分组。"""

    request = llm_admin_api.ModelRoutingUpdateRequest(
        config_key="vision",
        model_code="gpt-5.2",
    )
    model = SimpleNamespace(
        model_code="gpt-5.2",
        model_type="chat",
        is_default=False,
    )

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = model

    resp = llm_admin_api.update_model_routing(request, db)

    assert resp == {
        "message": "模型路由已更新",
        "config_key": "vision",
        "model_code": "gpt-5.2",
    }
    mock_update_route_group.assert_called_once_with(
        db=db,
        route_group="vision",
        default_model_code="gpt-5.2",
    )
    mock_refresh_llm_cache.assert_called_once_with(db)


def test_update_model_routing_rejects_non_embedding_model_for_embedding_key():
    """Embedding 路由应拒绝非 embedding 类型模型。"""

    request = llm_admin_api.ModelRoutingUpdateRequest(
        config_key="embedding",
        model_code="qwen3.5-flash",
    )
    chat_model = SimpleNamespace(
        model_code="qwen3.5-flash",
        model_type="chat",
        is_default=False,
    )

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = chat_model

    with pytest.raises(HTTPException) as exc:
        llm_admin_api.update_model_routing(request, db)

    assert exc.value.status_code == 400
    assert "embedding 类型模型" in exc.value.detail


def test_update_model_routing_rejects_embedding_model_for_vision_key():
    """Vision 路由应拒绝非多模态类型模型。"""

    request = llm_admin_api.ModelRoutingUpdateRequest(
        config_key="vision",
        model_code="embedding-3",
    )
    embedding_model = SimpleNamespace(
        model_code="embedding-3",
        model_type="embedding",
        is_default=False,
    )

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = embedding_model

    with pytest.raises(HTTPException) as exc:
        llm_admin_api.update_model_routing(request, db)

    assert exc.value.status_code == 400
    assert "vision/chat/reasoning" in exc.value.detail

