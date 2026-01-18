"""LLM 工具模块：统一管理 LLM 实例创建与配置（中文注释）。

支持 Qwen Think 模式（深度思考），自动检测模型名并启用 enable_thinking 参数。
"""
import os
import logging
from langchain.chat_models import init_chat_model

from app.ai import config as ai_config

logger = logging.getLogger(__name__)


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


# 尝试导入 DeepSeek 依赖
try:
    from langchain_deepseek import ChatDeepSeek
    from langchain_core.messages import AIMessage
except ImportError:
    # Handle case where optional dependencies are missing
    ChatDeepSeek = object
    AIMessage = object

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


def get_llm(enable_streaming: bool = True, force_thinking: bool = False, model_id: str = None):
    """获取 LLM 实例，支持动态模型选择。
    
    支持：
    - 普通对话模型
    - 深度思考模式：通过配置或参数启用 enable_thinking
    - 动态模型选择：通过 model_id 参数指定模型
    
    Args:
        enable_streaming: 是否启用流式输出，默认 True
        force_thinking: 是否启用深度思考模式，默认 False
        model_id: 可选模型标识，如 'deepseek-chat'、'qwen-flash' 等
        
    Returns:
        配置好的 LLM 实例
    """
    import os
    
    # 尝试使用 ConfigService 获取配置（优先）
    from app.services.llm_config_service import LLMConfigService
    
    config = None
    if model_id:
        config = LLMConfigService.get_model_config(model_id)
        if config:
            logger.info(f"使用数据库配置: model={config.model_code}, provider={config.provider_code}")
    
    # 如果没传 model_id，尝试获取默认模型
    if not model_id and not config:
        default_code = LLMConfigService.get_default_model_code()
        if default_code:
            config = LLMConfigService.get_model_config(default_code)
            logger.info(f"使用默认模型配置: {default_code}")

    if config:
        # 使用数据库配置
        model_type = config.provider_code
        model_name = config.model_code
        api_key = config.api_key
        base_url = _normalize(config.base_url)
        temperature = config.temperature
        
        # 深度思考配置
        enable_thinking = config.supports_thinking and (ai_config.ENABLE_THINKING or force_thinking)
        thinking_budget = config.thinking_budget
    else:
        # Fallback 到旧的环境变量逻辑（兼容性）
        logger.warning(f"由于未找到配置或 ConfigService 未初始化，回退到环境变量: model_id={model_id}")
        
        if model_id:
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
        else:
            model_type = ai_config.MODEL_TYPE
            model_name = ai_config.MODEL_NAME
            api_key = ai_config.MODEL_API_KEY
            base_url = _normalize(ai_config.MODEL_BASE_URL)
            
            if "deepseek" in model_name.lower() or "reasoner" in model_name.lower():
                if model_type != "deepseek":
                    model_type = "deepseek"
                    if not api_key:
                        api_key = os.getenv("DEEPSEEK_API_KEY")

        temperature = ai_config.MODEL_TEMPERATURE
        enable_thinking = ai_config.ENABLE_THINKING or force_thinking
        thinking_budget = ai_config.THINKING_BUDGET

    # 从环境变量获取通用配置（streaming, timeout, retries 仍使用环境变量）
    streaming = enable_streaming and ai_config.STREAMING
    timeout = ai_config.REQUEST_TIMEOUT
    max_retries = ai_config.MAX_RETRIES
    
    if not api_key:
        # 最后的检查，防止空 key 报错不清晰
        raise ValueError(f"配置错误：无法获取 model={model_name} 的 API Key")

    # 构建额外参数
    extra_body = {}
    model_kwargs = {}
    
    if enable_thinking:
        # 启用深度思考
        extra_body["enable_thinking"] = True
        # 设置思考 token 预算
        extra_body["thinking_budget"] = thinking_budget
        logger.info(
            "已启用深度思考模式: model=%s, budget=%d", 
            model_name, thinking_budget
        )
    
    # DeepSeek Reasoner 额外需要 reasoning.effort 参数
    is_deepseek_reasoner = "reasoner" in model_name.lower()
    reasoning_config = None
    if is_deepseek_reasoner:
        reasoning_config = {"effort": ai_config.REASONING_EFFORT}
        logger.info("DeepSeek Reasoner: effort=%s", ai_config.REASONING_EFFORT)

    # 对于 DeepSeek 模型，使用专门的 ChatDeepSeek 类以正确获取 reasoning_content
    # 注意：ChatDeepSeek 有兼容性问题，某些参数组合会导致 KeyError: 'messages'
    # 因此只传递必要的核心参数
    if model_type == "deepseek":
        try:
            # 尝试使用 CustomChatDeepSeek
            if ChatDeepSeek is object:
                raise ImportError("langchain_deepseek not installed")
                
            logger.info("使用 CustomChatDeepSeek (patched+debug): model=%s, provider=chat_deepseek, base_url=%s", model_name, base_url)
            return CustomChatDeepSeek(
                model=model_name,
                api_key=api_key,
                api_base=base_url,
                streaming=streaming,
                timeout=timeout,
                max_retries=max_retries,
            )
        except ImportError:
            logger.warning("未安装 langchain_deepseek，降级使用 ChatOpenAI（可能导致 reasoning_content 丢失）")
            # 降级逻辑：继续向下执行，使用 ChatOpenAI
            pass

    # 其他模型使用 init_chat_model
    if model_type == "qwen":
        provider = "openai"  # Qwen 使用 OpenAI 兼容 API
    elif model_type in ("openai", "azure"):
        provider = model_type
    else:
        provider = "openai"

    return init_chat_model(
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




