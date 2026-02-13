"""默认主对话模型路由单元测试。"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.ai.llm_util import get_llm, get_scene_llm
from app.core.config import MODEL_ROUTING_SQL_GENERATION, SQL_GENERATION_MODEL


def _make_model_config(model_code: str) -> SimpleNamespace:
    """构造最小可用模型配置。"""

    return SimpleNamespace(
        model_code=model_code,
        model_name=model_code,
        model_type="chat",
        provider_code="qwen",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        api_key="sk-test-key",
        temperature=0.3,
        supports_thinking=False,
        thinking_budget=2048,
        max_output_tokens=4096,
        context_window=128000,
        extra_config={},
    )


@patch("app.ai.llm_util._get_proxy_experiment_provider_whitelist", return_value=set())
@patch("app.ai.llm_util._is_proxy_experiment_master_enabled", return_value=False)
@patch("app.ai.llm_util.init_chat_model")
def test_default_chat_model_prefers_routing_config(
    mock_init_chat_model,
    _mock_proxy_switch,
    _mock_proxy_whitelist,
):
    """未传 model_id 时应优先命中 model_routing.default_chat。"""

    route_code = "qwen-plus-route"

    mock_init_chat_model.return_value = MagicMock()

    with patch(
        "app.services.llm_config_service.LLMConfigService.get_model_config",
        side_effect=lambda code: _make_model_config(route_code) if code == route_code else None,
    ) as mock_get_model_config, patch(
        "app.services.llm_config_service.LLMConfigService.get_default_model_code",
        return_value="qwen-plus-fallback",
    ) as mock_get_default_code, patch(
        "app.core.config.get_routing_model",
        return_value=route_code,
    ):
        get_llm()

    kwargs = mock_init_chat_model.call_args.kwargs
    assert kwargs["model"] == route_code
    assert kwargs["model_provider"] == "openai"

    mock_get_model_config.assert_called_once_with(route_code)
    mock_get_default_code.assert_not_called()


@patch("app.ai.llm_util._get_proxy_experiment_provider_whitelist", return_value=set())
@patch("app.ai.llm_util._is_proxy_experiment_master_enabled", return_value=False)
@patch("app.ai.llm_util.init_chat_model")
def test_default_chat_model_fallbacks_when_routing_misses(
    mock_init_chat_model,
    _mock_proxy_switch,
    _mock_proxy_whitelist,
):
    """路由配置不存在时应回退到 LLMConfigService 的默认模型。"""

    route_code = "missing-route"
    fallback_code = "qwen-plus-fallback"

    mock_init_chat_model.return_value = MagicMock()

    def _get_config(code: str):
        if code == fallback_code:
            return _make_model_config(fallback_code)
        return None

    with patch(
        "app.services.llm_config_service.LLMConfigService.get_model_config",
        side_effect=_get_config,
    ) as mock_get_model_config, patch(
        "app.services.llm_config_service.LLMConfigService.get_default_model_code",
        return_value=fallback_code,
    ) as mock_get_default_code, patch(
        "app.core.config.get_routing_model",
        return_value=route_code,
    ):
        get_llm()

    kwargs = mock_init_chat_model.call_args.kwargs
    assert kwargs["model"] == fallback_code
    assert kwargs["model_provider"] == "openai"

    assert mock_get_model_config.call_args_list[0].args == (route_code,)
    assert mock_get_model_config.call_args_list[1].args == (fallback_code,)
    mock_get_default_code.assert_called_once()


@patch("app.ai.llm_util.get_llm")
@patch("app.core.config.get_routing_model")
def test_get_scene_llm_uses_scene_registry(
    mock_get_routing_model,
    mock_get_llm,
):
    """get_scene_llm 应通过场景注册表解析模型代码。"""

    mock_get_routing_model.return_value = "sql-scene-model"
    mock_get_llm.return_value = MagicMock()

    get_scene_llm(scene="sql_generation", internal=True)

    mock_get_routing_model.assert_called_once_with(
        MODEL_ROUTING_SQL_GENERATION,
        SQL_GENERATION_MODEL,
    )
    mock_get_llm.assert_called_once_with(model_id="sql-scene-model", internal=True)


@patch("app.ai.llm_util.get_llm")
def test_get_scene_llm_prefers_explicit_model(
    mock_get_llm,
):
    """显式 model_id 应覆盖场景路由解析结果。"""

    mock_get_llm.return_value = MagicMock()

    get_scene_llm(scene="lightweight", model_id="manual-model", internal=True)

    mock_get_llm.assert_called_once_with(model_id="manual-model", internal=True)
