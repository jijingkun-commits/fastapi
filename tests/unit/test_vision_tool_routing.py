"""Vision 工具路由配置单元测试。"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from app.ai.tools import vision_tool
from app.services.llm_scene_service import SceneConfigError


@patch("app.ai.tools.vision_tool.LLMConfigService.get_model_config")
@patch("app.ai.tools.vision_tool.LLMSceneService.resolve_model_code", return_value="gpt-5.2")
def test_get_vision_model_config_uses_scene_binding(
    mock_resolve_scene_model,
    mock_get_model_config,
):
    """配置了 Vision 场景绑定时，应返回绑定模型。"""

    routed_config = SimpleNamespace(model_code="gpt-5.2", model_type="chat")
    mock_get_model_config.return_value = routed_config

    result = vision_tool._get_vision_model_config()

    assert result is routed_config
    mock_resolve_scene_model.assert_called_once_with("app.ai.tools.vision_tool.analyze_image")
    mock_get_model_config.assert_called_once_with("gpt-5.2")


@patch("app.ai.tools.vision_tool.LLMConfigService.get_model_config")
@patch(
    "app.ai.tools.vision_tool.LLMSceneService.resolve_model_code",
    side_effect=SceneConfigError("场景未配置"),
)
def test_get_vision_model_config_returns_none_when_scene_missing(
    mock_resolve_scene_model,
    mock_get_model_config,
):
    """Vision 场景未配置时应返回 None。"""

    result = vision_tool._get_vision_model_config()

    assert result is None
    mock_resolve_scene_model.assert_called_once_with("app.ai.tools.vision_tool.analyze_image")
    mock_get_model_config.assert_not_called()


@patch("app.ai.tools.vision_tool.LLMConfigService.get_model_config")
@patch("app.ai.tools.vision_tool.LLMSceneService.resolve_model_code", return_value="embedding-3")
def test_get_vision_model_config_returns_none_when_type_unsupported(
    _mock_resolve_scene_model,
    mock_get_model_config,
):
    """场景绑定模型类型不支持时，应返回 None。"""

    mock_get_model_config.return_value = SimpleNamespace(
        model_code="embedding-3",
        model_type="embedding",
    )

    result = vision_tool._get_vision_model_config()

    assert result is None


@patch("app.ai.tools.vision_tool._get_vision_model_config", return_value=object())
def test_is_vision_configured_true_when_route_resolves(_mock_get_config):
    """Vision 路由可解析模型时，配置状态应为 true。"""

    assert vision_tool.is_vision_configured() is True


@patch("app.ai.tools.vision_tool._get_vision_model_config", return_value=None)
def test_is_vision_configured_false_when_route_missing(_mock_get_config):
    """Vision 场景绑定不可用时，配置状态应为 false。"""

    assert vision_tool.is_vision_configured() is False

