"""Vision 工具路由配置单元测试。"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from app.ai.tools import vision_tool


@patch("app.ai.tools.vision_tool.ai_config.get_routing_model", return_value="gpt-5.2")
@patch("app.ai.tools.vision_tool.LLMConfigService.get_model_by_type")
@patch("app.ai.tools.vision_tool.LLMConfigService.get_model_config")
def test_get_vision_model_config_prefers_routed_chat_model(
    mock_get_model_config,
    mock_get_model_by_type,
    _mock_get_routing,
):
    """配置了 vision 路由时，应优先返回路由绑定模型。"""

    routed_config = SimpleNamespace(model_code="gpt-5.2", model_type="chat")
    mock_get_model_config.return_value = routed_config

    result = vision_tool._get_vision_model_config()

    assert result is routed_config
    mock_get_model_by_type.assert_not_called()


@patch("app.ai.tools.vision_tool.ai_config.get_routing_model", return_value="embedding-3")
@patch("app.ai.tools.vision_tool.LLMConfigService.get_model_by_type")
@patch("app.ai.tools.vision_tool.LLMConfigService.get_model_config")
def test_get_vision_model_config_falls_back_when_routed_model_unsupported(
    mock_get_model_config,
    mock_get_model_by_type,
    _mock_get_routing,
):
    """路由模型类型不支持时，应回退到 vision 类型默认模型。"""

    mock_get_model_config.return_value = SimpleNamespace(
        model_code="embedding-3",
        model_type="embedding",
    )
    fallback_config = SimpleNamespace(model_code="qwen3-vl-flash-2026-01-22", model_type="vision")
    mock_get_model_by_type.return_value = fallback_config

    result = vision_tool._get_vision_model_config()

    assert result is fallback_config
    mock_get_model_by_type.assert_called_once_with("vision")


@patch("app.ai.tools.vision_tool._get_vision_model_config", return_value=object())
def test_is_vision_configured_true_when_route_resolves(_mock_get_config):
    """Vision 路由可解析模型时，配置状态应为 true。"""

    assert vision_tool.is_vision_configured() is True


@patch("app.ai.tools.vision_tool._get_vision_model_config", return_value=None)
def test_is_vision_configured_false_when_route_missing(_mock_get_config):
    """Vision 路由和回退模型都不可用时，配置状态应为 false。"""

    assert vision_tool.is_vision_configured() is False
