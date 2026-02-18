"""LLM 工具模块：统一管理 LLM 实例创建与配置（中文注释）。

支持 Qwen Think 模式（深度思考），自动检测模型名并启用 enable_thinking 参数。
"""
import os
import json
import logging
from langchain.chat_models import init_chat_model

from app.ai import config as ai_config
from app.services.config_resolver import ConfigResolver

logger = logging.getLogger(__name__)

# 中转实验统一配置键（数据库）
PROXY_EXPERIMENT_SWITCH_KEY = "feature.proxy_experiment_enabled"
PROXY_EXPERIMENT_PROVIDERS_KEY = "feature.proxy_experiment_providers"


def _is_proxy_experiment_master_enabled() -> bool:
    """读取中转实验统一总开关（数据库优先，环境变量兜底）。"""
    try:
        return ConfigResolver.get_bool(
            PROXY_EXPERIMENT_SWITCH_KEY,
            ai_config.ENABLE_PROXY_EXPERIMENT,
        )
    except Exception as exc:
        logger.warning("读取统一实验开关失败，回退环境变量: %s", exc)
        return ai_config.ENABLE_PROXY_EXPERIMENT


def _get_proxy_experiment_provider_whitelist() -> set[str]:
    """读取中转实验 provider 白名单（数据库优先，环境变量兜底）。"""
    env_fallback = set(ai_config.PROXY_EXPERIMENT_PROVIDERS)
    try:
        raw_codes = ConfigResolver.get(PROXY_EXPERIMENT_PROVIDERS_KEY, None)
        if raw_codes is None:
            return env_fallback

        if isinstance(raw_codes, str):
            return {code.strip() for code in raw_codes.split(",") if code.strip()}

        if isinstance(raw_codes, (list, tuple, set)):
            return {str(code).strip() for code in raw_codes if str(code).strip()}

        logger.warning(
            "中转实验 provider 白名单类型非法，回退环境变量: type=%s",
            type(raw_codes).__name__,
        )
        return env_fallback
    except Exception as exc:
        logger.warning("读取 provider 白名单失败，回退环境变量: %s", exc)
        return env_fallback


def _normalize(url: str) -> str:
    """规范化 API URL，确保以版本号结尾（支持 /v1、/v2、/v3、/v4 等）。
    
    不同供应商的 API 版本号不同：
    - OpenAI / DeepSeek / Qwen: /v1
    - 智谱 AI (Zhipu/GLM): /v4
    """
    import re
    if not url:
        return "https://api.deepseek.com/v1"
    u = url.rstrip("/")
    # 检查是否已有版本号（/v1、/v2、/v3、/v4 等）
    if re.search(r'/v\d+$', u):
        return u
    # 默认追加 /v1
    return u + "/v1"


def _parse_bool_flag(value):
    """解析布尔配置，返回 True/False/None。"""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on", "enabled"}:
            return True
        if lowered in {"0", "false", "no", "off", "disabled"}:
            return False
    return None


def _parse_headers(headers):
    """解析默认请求头，仅保留字符串键值。"""
    if not isinstance(headers, dict):
        return {}
    parsed = {}
    for key, value in headers.items():
        if isinstance(key, str) and isinstance(value, str) and key.strip():
            parsed[key.strip()] = value
    return parsed


def _resolve_reasoning_effort(extra_config: dict):
    """解析 reasoning effort 配置。"""
    if not isinstance(extra_config, dict):
        return None
    reasoning_effort = extra_config.get("reasoning_effort")
    if not reasoning_effort:
        reasoning = extra_config.get("reasoning")
        if isinstance(reasoning, dict):
            reasoning_effort = reasoning.get("effort")
    if isinstance(reasoning_effort, str):
        normalized = reasoning_effort.strip().lower()
        if normalized in {"low", "medium", "high", "xhigh"}:
            return normalized
    return None


def _resolve_scene_model_id(scene_key: str, model_id: str = None) -> str:
    """按调用场景键解析目标模型代码。"""

    from app.services.llm_scene_service import LLMSceneService

    return LLMSceneService.resolve_model_code(scene_key=scene_key, model_id=model_id)


def get_scene_llm(
    scene_key: str = None,
    model_id: str = None,
    **kwargs,
):
    """按调用场景键获取 LLM 实例。"""

    if "scene" in kwargs:
        raise TypeError("get_scene_llm() 不再支持 scene 参数，请改用 scene_key")

    if not scene_key:
        raise ValueError("调用 get_scene_llm 时必须提供 scene_key")

    resolved_model_id = _resolve_scene_model_id(scene_key=scene_key, model_id=model_id)
    return get_llm(model_id=resolved_model_id, **kwargs)


def _normalize_text_content(content) -> str:
    """将消息内容归一化为纯文本。

    仅用于 internal 调用链路，避免将 Responses 风格的 function_call 内容块
    透传给 Chat Completions 接口导致 400。
    """
    if isinstance(content, str):
        return content
    if content is None:
        return ""

    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
                continue

            if not isinstance(item, dict):
                continue

            block_type = str(item.get("type", "")).lower()
            if block_type in {"function_call", "tool_call", "function_result"}:
                # 内部工具调用块不参与自然语言意图分析
                continue

            text_val = item.get("text")
            if isinstance(text_val, str):
                parts.append(text_val)
                continue

            inner_content = item.get("content")
            if isinstance(inner_content, str):
                parts.append(inner_content)

        return "".join(parts)

    if isinstance(content, dict):
        text_val = content.get("text")
        if isinstance(text_val, str):
            return text_val

        inner_content = content.get("content")
        if isinstance(inner_content, str):
            return inner_content

        try:
            return json.dumps(content, ensure_ascii=False)
        except Exception:
            return str(content)

    return str(content)


def _sanitize_internal_invoke_input(input_data):
    """清洗 internal 调用输入，兼容不同模型协议的历史消息。"""
    if not isinstance(input_data, list):
        return input_data

    try:
        from copy import deepcopy

        sanitized_messages = deepcopy(input_data)
    except Exception:
        return input_data

    sanitized_count = 0

    for index, msg in enumerate(sanitized_messages):
        content = getattr(msg, "content", None)
        if not isinstance(content, list):
            continue

        normalized_content = _normalize_text_content(content)

        try:
            msg.content = normalized_content
        except Exception:
            if hasattr(msg, "model_copy"):
                try:
                    sanitized_messages[index] = msg.model_copy(update={"content": normalized_content})
                except Exception:
                    continue
            else:
                continue

        sanitized_count += 1

    if sanitized_count:
        logger.debug(
            "internal 调用输入清洗完成: %d 条消息 content(list)->text",
            sanitized_count,
        )

    return sanitized_messages


# 尝试导入 DeepSeek 依赖
try:
    from langchain_deepseek import ChatDeepSeek
    from langchain_core.messages import AIMessage
except ImportError:
    # Handle case where optional dependencies are missing
    ChatDeepSeek = object
    AIMessage = object

class InternalLLMWrapper:
    """内部 LLM 调用包装器（中文注释）。
    
    用于封装需要隐藏输出的 LLM 调用（如意图分析、JSON 解析等），
    自动为 invoke/ainvoke 添加 internal_thought tag，防止内容泄露到前端。
    
    使用方式：
        llm = get_scene_llm(scene_key="app.ai.workflow.todo_graph.analyze_intent", internal=True)
        response = llm.invoke(messages)  # 自动添加 tag
    """
    
    def __init__(self, llm):
        self._llm = llm
    
    def _merge_config(self, config: dict = None) -> dict:
        """合并配置，确保包含 internal_thought tag。"""
        config = config or {}
        tags = config.get("tags", [])
        if "internal_thought" not in tags:
            tags = list(tags) + ["internal_thought"]
        config["tags"] = tags
        return config
    
    def invoke(self, input, config: dict = None, **kwargs):
        """同步调用，自动添加 internal_thought tag。"""
        merged_config = self._merge_config(config)
        sanitized_input = (
            _sanitize_internal_invoke_input(input)
            if ai_config.ENABLE_INTERNAL_CONTENT_SANITIZE
            else input
        )
        return self._llm.invoke(sanitized_input, config=merged_config, **kwargs)
    
    async def ainvoke(self, input, config: dict = None, **kwargs):
        """异步调用，自动添加 internal_thought tag。"""
        merged_config = self._merge_config(config)
        sanitized_input = (
            _sanitize_internal_invoke_input(input)
            if ai_config.ENABLE_INTERNAL_CONTENT_SANITIZE
            else input
        )
        return await self._llm.ainvoke(sanitized_input, config=merged_config, **kwargs)
    
    def __getattr__(self, name):
        """代理其他属性到底层 LLM。"""
        return getattr(self._llm, name)


class CustomChatDeepSeek(ChatDeepSeek):
    """DeepSeek 客户端的自定义补丁类。
    
    解决 DeepSeek R1 (Reasoner) 的严格 API 要求：
    当启用 thinking mode 进行多轮对话时，历史 Assistant 消息必须包含 reasoning_content 字段。
    标准 LangChain 序列化可能丢失此字段，导致 400 BadRequest 错误。
    
    此类在构建请求 Payload 时检查并强制注入该字段。
    """
    
    def _get_request_payload(self, input_, *args, **kwargs):
        payload = super()._get_request_payload(input_, *args, **kwargs)
        try:
            self._inject_reasoning_content(input_, payload)
        except Exception as e:
            logger.warning("CustomChatDeepSeek 解析失败: %s", e)
        return payload
    
    def _inject_reasoning_content(self, input_, payload: dict) -> None:
        """确保 Payload 中的 assistant 消息包含 reasoning_content 字段。"""
        messages = self._convert_input(input_)
        
        # Handle ChatPromptValue (which _convert_input returns for list inputs)
        if hasattr(messages, "to_messages"):
            messages = messages.to_messages()
        
        if not isinstance(messages, list) or "messages" not in payload:
            return
        
        for i, msg_obj in enumerate(messages):
            if i >= len(payload["messages"]):
                continue
                
            msg_dict = payload["messages"][i]
            if msg_dict.get("role") != "assistant" or not isinstance(msg_obj, AIMessage):
                continue
            
            # 检查原始消息对象中是否有 reasoning_content
            reasoning = msg_obj.additional_kwargs.get("reasoning_content")
            
            # 如果 Payload 中已经有 reasoning_content，跳过
            if "reasoning_content" in msg_dict:
                continue
            
            # 注入 reasoning_content
            if reasoning is not None:
                msg_dict["reasoning_content"] = reasoning
                logger.debug("[CustomChatDeepSeek] 注入 reasoning (索引 %d, 长度=%d)", i, len(reasoning))
            else:
                # 强制注入空字符串以满足 API 要求
                msg_dict["reasoning_content"] = ""
                logger.warning("[CustomChatDeepSeek] 强制注入空 reasoning_content (索引 %d)", i)


def get_llm(
    enable_streaming: bool = True,
    force_thinking: bool = False,
    model_id: str = None,
    internal: bool = False
):
    """获取 LLM 实例，支持动态模型选择。"""
    if internal:
        enable_streaming = False
    import os

    from app.services.llm_config_service import LLMConfigService

    config = None
    # 运行时扩展参数：仅用于命中实验开关的中转 provider。
    runtime_extra_config = {}
    # 默认关闭实验分支，确保生产链路不受影响。
    proxy_experiment_enabled = False

    if not model_id:
        raise ValueError("get_llm 已禁用无场景调用，请使用 get_scene_llm(scene_key=...)")

    config = LLMConfigService.get_model_config(model_id)
    if config:
        logger.info("使用数据库配置: model=%s, provider=%s", config.model_code, config.provider_code)

    if config:
        model_type = config.provider_code
        model_name = config.model_code
        api_key = config.api_key
        base_url = _normalize(config.base_url)
        temperature = config.temperature
        enable_thinking = (
            config.supports_thinking and ai_config.ENABLE_THINKING
        ) or force_thinking
        thinking_budget = config.thinking_budget

        if isinstance(config.extra_config, dict):
            runtime_extra_config = dict(config.extra_config)
        elif config.extra_config is not None:
            logger.warning(
                "模型 extra_config 不是 dict，忽略: model=%s, type=%s",
                config.model_code,
                type(config.extra_config).__name__,
            )

        # 实验分支三重门：非 prod + 统一总开关 + provider 命中白名单。
        proxy_experiment_master_enabled = _is_proxy_experiment_master_enabled()
        proxy_provider_whitelist = _get_proxy_experiment_provider_whitelist()
        proxy_experiment_enabled = (
            ai_config.ENV != "prod"
            and proxy_experiment_master_enabled
            and model_type in proxy_provider_whitelist
        )

        if proxy_experiment_enabled:
            # 允许 DB 中的展示模型代码映射到中转真实模型名。
            actual_model = runtime_extra_config.get("actual_model")
            if isinstance(actual_model, str) and actual_model.strip():
                model_name = actual_model.strip()
    else:
        logger.warning("由于未找到配置或 ConfigService 未初始化，回退到环境变量: model_id=%s", model_id)

        if "deepseek" in model_id.lower():
            model_type = "deepseek"
            model_name = model_id
            api_key = os.getenv("DEEPSEEK_API_KEY", ai_config.MODEL_API_KEY)
            base_url = _normalize(os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"))
        elif "qwen" in model_id.lower():
            model_type = "qwen"
            model_name = model_id
            api_key = os.getenv("QWEN_API_KEY", ai_config.MODEL_API_KEY)
            base_url = _normalize(os.getenv("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"))
        else:
            model_type = ai_config.MODEL_TYPE
            model_name = model_id
            api_key = ai_config.MODEL_API_KEY
            base_url = _normalize(ai_config.MODEL_BASE_URL)

        temperature = ai_config.MODEL_TEMPERATURE
        enable_thinking = ai_config.ENABLE_THINKING or force_thinking
        thinking_budget = ai_config.THINKING_BUDGET

    streaming = enable_streaming and ai_config.STREAMING
    timeout = ai_config.REQUEST_TIMEOUT
    max_retries = ai_config.MAX_RETRIES

    if not api_key and ai_config.ENV == "test":
        api_key = "test-api-key"
        logger.warning("测试环境未配置 API Key，使用占位值: model=%s", model_name)

    if not api_key:
        raise ValueError(f"配置错误：无法获取 model={model_name} 的 API Key")

    extra_body = {}
    model_kwargs = {}

    if proxy_experiment_enabled:
        # 仅实验 provider 注入兼容参数，常规 provider 完全不走该分支。
        use_responses_api = _parse_bool_flag(runtime_extra_config.get("use_responses_api"))
        if use_responses_api is True:
            model_kwargs["use_responses_api"] = True

        store_flag = _parse_bool_flag(runtime_extra_config.get("store"))
        if store_flag is not None:
            model_kwargs["store"] = store_flag

        verbosity = runtime_extra_config.get("verbosity")
        if isinstance(verbosity, str) and verbosity.strip():
            model_kwargs["verbosity"] = verbosity.strip().lower()

        reasoning_effort = _resolve_reasoning_effort(runtime_extra_config)
        if reasoning_effort:
            model_kwargs["reasoning_effort"] = reasoning_effort

        default_headers = _parse_headers(runtime_extra_config.get("default_headers"))
        # 若未配置 UA，给实验 provider 注入浏览器 UA 以绕过部分网关对 SDK UA 的拦截。
        if "User-Agent" not in default_headers:
            default_headers["User-Agent"] = "Mozilla/5.0"

        send_x_api_key = _parse_bool_flag(runtime_extra_config.get("send_x_api_key"))
        # 部分中转网关要求 X-API-Key；默认不发送，按模型配置显式开启。
        if send_x_api_key is True:
            default_headers["X-API-Key"] = api_key
        if default_headers:
            model_kwargs["default_headers"] = default_headers

        request_params = runtime_extra_config.get("request_params")
        if isinstance(request_params, dict):
            extra_body.update(request_params)
        elif request_params is not None:
            logger.warning(
                "request_params 不是 dict，忽略: model=%s, type=%s",
                model_name,
                type(request_params).__name__,
            )

        logger.info(
            "启用中转实验适配: provider=%s, model=%s, responses=%s",
            model_type,
            model_name,
            bool(model_kwargs.get("use_responses_api")),
        )

    if enable_thinking:
        extra_body["enable_thinking"] = True
        extra_body["thinking_budget"] = thinking_budget
        logger.info("已启用深度思考模式: model=%s, budget=%d", model_name, thinking_budget)

    is_deepseek_reasoner = "reasoner" in model_name.lower()
    if is_deepseek_reasoner:
        logger.info("DeepSeek Reasoner: effort=%s", ai_config.REASONING_EFFORT)

    llm = None
    if model_type == "deepseek":
        try:
            if ChatDeepSeek is object:
                raise ImportError("langchain_deepseek not installed")

            logger.info(
                "使用 CustomChatDeepSeek (patched+debug): model=%s, provider=chat_deepseek, base_url=%s",
                model_name,
                base_url,
            )
            llm = CustomChatDeepSeek(
                model=model_name,
                api_key=api_key,
                api_base=base_url,
                streaming=streaming,
                timeout=timeout,
                max_retries=max_retries,
            )
        except ImportError:
            logger.warning("未安装 langchain_deepseek，降级使用 ChatOpenAI（可能导致 reasoning_content 丢失）")

    if llm is None:
        if model_type == "qwen":
            provider = "openai"
        elif model_type in ("openai", "azure"):
            provider = model_type
        else:
            provider = "openai"

        llm = init_chat_model(
            model=model_name,
            model_provider=provider,
            api_key=api_key,
            base_url=base_url,
            temperature=temperature,
            streaming=streaming,
            timeout=timeout,
            max_retries=max_retries,
            extra_body=extra_body if extra_body else None,
            **model_kwargs,
        )

    if internal:
        return InternalLLMWrapper(llm)

    return llm
