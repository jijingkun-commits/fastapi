"""LLM 中转实验适配单元测试。"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.ai import config as ai_config
from app.ai.llm_util import InternalLLMWrapper, get_llm, _get_proxy_experiment_provider_whitelist


def _make_model_config(**overrides):
    """构造最小模型配置对象。"""

    defaults = {
        "model_code": "gpt-5.2",
        "model_name": "GPT-5.2",
        "model_type": "chat",
        "provider_code": "openai_proxy_trial",
        "base_url": "https://proxy.example.com",
        "api_key": "sk-test-key",
        "temperature": 0.3,
        "supports_thinking": False,
        "thinking_budget": 2048,
        "max_output_tokens": 4096,
        "context_window": 128000,
        "extra_config": {},
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


@patch("app.ai.llm_util._get_proxy_experiment_provider_whitelist", return_value={"openai_proxy_trial"})
@patch("app.ai.llm_util._is_proxy_experiment_master_enabled", return_value=True)
@patch("app.services.llm_config_service.LLMConfigService.get_default_model_code", return_value=None)
@patch("app.services.llm_config_service.LLMConfigService.get_model_config")
@patch("app.ai.llm_util.init_chat_model")
def test_proxy_experiment_force_disabled_in_prod(
    mock_init_chat_model,
    mock_get_model_config,
    _mock_get_default_code,
    _mock_master_switch,
    _mock_provider_whitelist,
):
    """生产环境应忽略中转实验注入参数，保持原有调用链路。"""

    mock_get_model_config.return_value = _make_model_config(
        extra_config={
            "actual_model": "gpt-5.2",
            "use_responses_api": True,
            "send_x_api_key": True,
            "default_headers": {"X-Test": "1"},
            "request_params": {"foo": "bar"},
        }
    )
    mock_init_chat_model.return_value = MagicMock()

    with patch.object(ai_config, "ENV", "prod"):
        get_llm(model_id="gpt-5.2")

    kwargs = mock_init_chat_model.call_args.kwargs
    assert kwargs["model"] == "gpt-5.2"
    assert kwargs["model_provider"] == "openai"
    assert kwargs["base_url"] == "https://proxy.example.com/v1"
    assert "use_responses_api" not in kwargs
    assert "default_headers" not in kwargs
    assert kwargs.get("extra_body") is None


@patch("app.ai.llm_util._get_proxy_experiment_provider_whitelist", return_value={"openai_proxy_trial"})
@patch("app.ai.llm_util._is_proxy_experiment_master_enabled", return_value=True)
@patch("app.services.llm_config_service.LLMConfigService.get_default_model_code", return_value=None)
@patch("app.services.llm_config_service.LLMConfigService.get_model_config")
@patch("app.ai.llm_util.init_chat_model")
def test_proxy_experiment_injects_runtime_kwargs_in_dev(
    mock_init_chat_model,
    mock_get_model_config,
    _mock_get_default_code,
    _mock_master_switch,
    _mock_provider_whitelist,
):
    """开发环境命中 provider 时应注入实验参数。"""

    mock_get_model_config.return_value = _make_model_config(
        model_code="gpt-5.2-codex",
        extra_config={
            "actual_model": "gpt-5.2",
            "use_responses_api": "true",
            "store": "false",
            "verbosity": "HIGH",
            "reasoning": {"effort": "xhigh"},
            "send_x_api_key": "true",
            "default_headers": {"X-Test": "1"},
            "request_params": {"foo": "bar"},
        },
    )
    mock_init_chat_model.return_value = MagicMock()

    with patch.object(ai_config, "ENV", "dev"):
        get_llm(model_id="gpt-5.2-codex")

    kwargs = mock_init_chat_model.call_args.kwargs
    assert kwargs["model"] == "gpt-5.2"
    assert kwargs["model_provider"] == "openai"
    assert kwargs["use_responses_api"] is True
    assert kwargs["store"] is False
    assert kwargs["verbosity"] == "high"
    assert kwargs["reasoning_effort"] == "xhigh"
    assert kwargs["default_headers"]["X-Test"] == "1"
    assert kwargs["default_headers"]["X-API-Key"] == "sk-test-key"
    assert kwargs["extra_body"] == {"foo": "bar"}


def test_internal_wrapper_sanitizes_function_call_content_blocks():
    """internal 调用应清洗 function_call 内容块，避免 chat-completions 400。"""

    captured = {}

    class _FakeLLM:
        def invoke(self, input, config=None, **kwargs):
            captured["input"] = input
            captured["config"] = config
            return SimpleNamespace(content="ok")

    wrapper = InternalLLMWrapper(_FakeLLM())

    messages = [
        SystemMessage(content="系统提示"),
        HumanMessage(content="我明天要去北京"),
        AIMessage(
            content=[
                {"type": "text", "text": "准备委派给待办专家。"},
                {
                    "type": "function_call",
                    "name": "assign_to_todo_expert",
                    "arguments": "{\"task_description\": \"test\"}",
                },
            ],
            tool_calls=[
                {
                    "name": "assign_to_todo_expert",
                    "args": {"task_description": "test"},
                    "id": "call_test_1",
                    "type": "tool_call",
                }
            ],
        ),
    ]

    with patch.object(ai_config, "ENABLE_INTERNAL_CONTENT_SANITIZE", True):
        wrapper.invoke(messages)

    sent_messages = captured["input"]
    assert isinstance(sent_messages[2].content, str)
    assert sent_messages[2].content == "准备委派给待办专家。"
    assert isinstance(messages[2].content, list)
    assert captured["config"]["tags"][-1] == "internal_thought"


@patch("app.ai.llm_util._get_proxy_experiment_provider_whitelist", return_value={"openai_proxy_trial"})
@patch("app.ai.llm_util._is_proxy_experiment_master_enabled", return_value=False)
@patch("app.services.llm_config_service.LLMConfigService.get_default_model_code", return_value=None)
@patch("app.services.llm_config_service.LLMConfigService.get_model_config")
@patch("app.ai.llm_util.init_chat_model")
def test_proxy_experiment_respects_master_switch(
    mock_init_chat_model,
    mock_get_model_config,
    _mock_get_default_code,
    _mock_master_switch,
    _mock_provider_whitelist,
):
    """统一总开关关闭时，不应注入中转实验参数。"""

    mock_get_model_config.return_value = _make_model_config(
        extra_config={
            "actual_model": "gpt-5.2",
            "use_responses_api": True,
            "default_headers": {"X-Test": "1"},
        }
    )
    mock_init_chat_model.return_value = MagicMock()

    with patch.object(ai_config, "ENV", "dev"):
        get_llm(model_id="gpt-5.2")

    kwargs = mock_init_chat_model.call_args.kwargs
    assert kwargs["model"] == "gpt-5.2"
    assert kwargs["model_provider"] == "openai"
    assert "use_responses_api" not in kwargs
    assert "default_headers" not in kwargs


@patch("app.ai.llm_util._get_proxy_experiment_provider_whitelist", return_value={"other_provider"})
@patch("app.ai.llm_util._is_proxy_experiment_master_enabled", return_value=True)
@patch("app.services.llm_config_service.LLMConfigService.get_default_model_code", return_value=None)
@patch("app.services.llm_config_service.LLMConfigService.get_model_config")
@patch("app.ai.llm_util.init_chat_model")
def test_proxy_experiment_respects_provider_whitelist(
    mock_init_chat_model,
    mock_get_model_config,
    _mock_get_default_code,
    _mock_master_switch,
    _mock_provider_whitelist,
):
    """provider 不在白名单时，不应注入中转实验参数。"""

    mock_get_model_config.return_value = _make_model_config(
        provider_code="openai_proxy_trial",
        extra_config={
            "actual_model": "gpt-5.2",
            "use_responses_api": True,
        },
    )
    mock_init_chat_model.return_value = MagicMock()

    with patch.object(ai_config, "ENV", "dev"):
        get_llm(model_id="gpt-5.2")

    kwargs = mock_init_chat_model.call_args.kwargs
    assert kwargs["model"] == "gpt-5.2"
    assert kwargs["model_provider"] == "openai"
    assert "use_responses_api" not in kwargs


@patch("app.services.system_config_service.SystemConfigService.get", return_value="openai_proxy_trial,custom_proxy")
def test_provider_whitelist_prefers_db_string(_mock_get):
    """provider 白名单优先读取 DB 字符串配置。"""

    with patch.object(ai_config, "PROXY_EXPERIMENT_PROVIDERS", {"env_fallback"}):
        providers = _get_proxy_experiment_provider_whitelist()

    assert providers == {"openai_proxy_trial", "custom_proxy"}


@patch("app.services.system_config_service.SystemConfigService.get", return_value=None)
def test_provider_whitelist_fallbacks_to_env(_mock_get):
    """DB 未配置 provider 白名单时应回退环境变量。"""

    with patch.object(ai_config, "PROXY_EXPERIMENT_PROVIDERS", {"env_a", "env_b"}):
        providers = _get_proxy_experiment_provider_whitelist()

    assert providers == {"env_a", "env_b"}
