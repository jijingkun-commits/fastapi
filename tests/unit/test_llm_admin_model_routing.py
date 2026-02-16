"""LLM 管理后台模型路由单元测试。"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints import llm_admin_api


class _FakeQuery:
    """最小查询桩，支持 filter/first/update 链式调用。"""

    def __init__(self, first_result=None):
        self._first_result = first_result
        self.update_payload = None

    def filter(self, *_args, **_kwargs):
        return self

    def first(self):
        return self._first_result

    def update(self, payload):
        self.update_payload = payload
        return 1


@patch("app.core.config.get_routing_model")
@patch("app.api.v1.endpoints.llm_admin_api._has_vision_route_candidates")
@patch("app.api.v1.endpoints.llm_admin_api._get_vision_model_for_routing")
@patch("app.api.v1.endpoints.llm_admin_api._get_type_default_model")
@patch("app.api.v1.endpoints.llm_admin_api._get_chat_default_model_for_routing")
def test_get_model_routing_marks_vision_as_editable_when_configured(
    mock_get_chat_default,
    mock_get_type_default,
    mock_get_vision_model,
    mock_has_vision_candidates,
    mock_get_routing_model,
):
    """Vision 路由存在候选模型时应允许编辑。"""

    mock_get_chat_default.return_value = "gpt-5.2"
    mock_get_type_default.return_value = "embedding-3"
    mock_get_vision_model.return_value = "qwen3-vl-flash-2026-01-22"
    mock_has_vision_candidates.return_value = True
    mock_get_routing_model.side_effect = lambda key, fallback: {
        "model_routing.lightweight": "gpt-5.2-mini",
        "model_routing.sql_generation": "gpt-5.2",
    }.get(key, fallback)

    routes = llm_admin_api.get_model_routing(db=MagicMock())

    vision_route = next(route for route in routes if route.scene == "Vision")
    assert vision_route.current_model == "qwen3-vl-flash-2026-01-22"
    assert vision_route.config_key == "vision"
    assert vision_route.editable is True


@patch("app.core.config.get_routing_model")
@patch("app.api.v1.endpoints.llm_admin_api._has_vision_route_candidates")
@patch("app.api.v1.endpoints.llm_admin_api._get_vision_model_for_routing")
@patch("app.api.v1.endpoints.llm_admin_api._get_type_default_model")
@patch("app.api.v1.endpoints.llm_admin_api._get_chat_default_model_for_routing")
def test_get_model_routing_disables_vision_when_no_candidates(
    mock_get_chat_default,
    mock_get_type_default,
    mock_get_vision_model,
    mock_has_vision_candidates,
    mock_get_routing_model,
):
    """Vision 无候选模型时，路由应显示不可编辑。"""

    mock_get_chat_default.return_value = "gpt-5.2"
    mock_get_type_default.return_value = "embedding-3"
    mock_get_vision_model.return_value = "未配置"
    mock_has_vision_candidates.return_value = False
    mock_get_routing_model.side_effect = lambda _key, fallback: fallback

    routes = llm_admin_api.get_model_routing(db=MagicMock())

    vision_route = next(route for route in routes if route.scene == "Vision")
    assert vision_route.current_model == "未配置"
    assert vision_route.editable is False


@patch("app.services.system_config_service.SystemConfigService.refresh_cache")
@patch("app.repositories.config_repo.upsert_config")
@patch("app.api.v1.endpoints.llm_admin_api._refresh_llm_runtime_cache")
def test_update_model_routing_supports_vision_default_switch(
    mock_refresh_llm_cache,
    mock_upsert_config,
    mock_refresh_system_cache,
):
    """vision 类型模型绑定 Vision 路由时应同步刷新类型默认。"""

    request = llm_admin_api.ModelRoutingUpdateRequest(
        config_key="vision",
        model_code="qwen3-vl-flash-2026-01-22",
    )
    vision_model = SimpleNamespace(
        model_code="qwen3-vl-flash-2026-01-22",
        model_type="vision",
        is_default=False,
    )

    db = MagicMock()
    find_model_query = _FakeQuery(first_result=vision_model)
    reset_default_query = _FakeQuery()
    db.query.side_effect = [find_model_query, reset_default_query]

    resp = llm_admin_api.update_model_routing(request, db)

    assert resp == {
        "message": "模型路由已更新",
        "config_key": "vision",
        "model_code": "qwen3-vl-flash-2026-01-22",
    }
    assert reset_default_query.update_payload == {"is_default": False}
    assert vision_model.is_default is True
    db.commit.assert_called_once()
    mock_refresh_llm_cache.assert_called_once_with(db)
    mock_refresh_system_cache.assert_called_once_with(db)
    mock_upsert_config.assert_called_once()


@patch("app.services.system_config_service.SystemConfigService.refresh_cache")
@patch("app.repositories.config_repo.upsert_config")
@patch("app.api.v1.endpoints.llm_admin_api._refresh_llm_runtime_cache")
def test_update_model_routing_accepts_chat_model_for_vision_key(
    mock_refresh_llm_cache,
    mock_upsert_config,
    mock_refresh_system_cache,
):
    """Vision 路由应允许绑定具备多模态能力的 chat 类型模型。"""

    request = llm_admin_api.ModelRoutingUpdateRequest(
        config_key="vision",
        model_code="gpt-5.2",
    )
    chat_model = SimpleNamespace(
        model_code="gpt-5.2",
        model_type="chat",
        is_default=False,
    )

    db = MagicMock()
    find_model_query = _FakeQuery(first_result=chat_model)
    db.query.side_effect = [find_model_query]

    resp = llm_admin_api.update_model_routing(request, db)

    assert resp == {
        "message": "模型路由已更新",
        "config_key": "vision",
        "model_code": "gpt-5.2",
    }
    assert chat_model.is_default is False
    db.commit.assert_called_once()
    mock_refresh_llm_cache.assert_called_once_with(db)
    mock_refresh_system_cache.assert_called_once_with(db)
    mock_upsert_config.assert_called_once()


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
