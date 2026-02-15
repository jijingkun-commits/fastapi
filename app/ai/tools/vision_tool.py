"""Vision 图片理解工具（中文注释）。

提供图片理解能力，支持配置化的多模态模型路由。
优先读取路由键 vision，未配置时回退 model_type='vision' 的默认模型。
"""
import httpx
import logging
from typing import Any, Optional
from pydantic import BaseModel, Field
from langchain.tools import tool

from app.services.llm_config_service import LLMConfigService
from app.schemas.llm import LLMModelConfig
from app.core import config as ai_config

logger = logging.getLogger(__name__)


class ImageAnalysisInput(BaseModel):
    """图片分析输入参数。"""
    image_url: str = Field(description="图片 URL 地址")
    question: Optional[str] = Field(
        default="请描述这张图片的内容，尽量详细一些，除了文字内容，对图片里的东西也要做一个描述。",
        description="关于图片的问题"
    )


def _is_supported_vision_route_model_type(model_type: Optional[str]) -> bool:
    """检查模型类型是否可用于 Vision 路由。"""
    return (model_type or "chat") in {"vision", "chat", "reasoning"}


def _get_vision_model_config() -> Optional[LLMModelConfig]:
    """获取 Vision 工具使用的模型配置（优先显式路由，回退类型默认）。"""
    routed_model_code = ai_config.get_routing_model(ai_config.MODEL_ROUTING_VISION, "")
    if routed_model_code:
        routed_config = LLMConfigService.get_model_config(routed_model_code)
        if routed_config and _is_supported_vision_route_model_type(routed_config.model_type):
            return routed_config
        logger.warning(
            "Vision 路由模型不可用，回退类型默认: code=%s",
            routed_model_code,
        )

    return LLMConfigService.get_model_by_type("vision")


def _is_truthy(value: Any) -> bool:
    """宽松解析布尔值。"""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    if isinstance(value, (int, float)):
        return bool(value)
    return False


def _extract_responses_text(data: dict) -> str:
    """从 Responses API 返回体中提取文本。"""
    output_text = data.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    texts: list[str] = []
    output_items = data.get("output")
    if isinstance(output_items, list):
        for item in output_items:
            if not isinstance(item, dict):
                continue
            content_items = item.get("content")
            if not isinstance(content_items, list):
                continue
            for content in content_items:
                if not isinstance(content, dict):
                    continue
                if content.get("type") in {"output_text", "text"}:
                    text = content.get("text")
                    if isinstance(text, str) and text.strip():
                        texts.append(text.strip())

    if texts:
        return "\n".join(texts)

    raise ValueError("Vision Responses API 未返回可解析文本")


def _call_vision_model(image_url: str, question: str) -> str:
    """调用 Vision 模型分析图片。
    
    优先读取 vision 路由配置，未命中时回退到 vision 类型默认模型。
    
    Args:
        image_url: 图片 URL
        question: 关于图片的问题
        
    Returns:
        模型回答
    """
    config = _get_vision_model_config()
    if not config:
        return "⚠️ Vision 模型未配置，请在模型路由中设置 vision，或添加 model_type='vision' 的模型"
    
    if not config.api_key:
        return f"⚠️ Vision 模型 {config.model_code} 的 API Key 未配置"

    extra_config = config.extra_config if isinstance(config.extra_config, dict) else {}
    request_params = extra_config.get("request_params") if isinstance(extra_config.get("request_params"), dict) else {}
    wire_api = str(extra_config.get("wire_api") or "").strip().lower()
    use_responses_api = _is_truthy(extra_config.get("use_responses_api")) or wire_api == "responses"

    normalized_image_url = (image_url or "").strip()
    image_url = normalized_image_url
    object_key = None
    if normalized_image_url.startswith("/api/v1/assets/"):
        object_key = normalized_image_url.split("/api/v1/assets/", 1)[1]
    elif normalized_image_url and "/" in normalized_image_url and not normalized_image_url.startswith(("http://", "https://", "data:")):
        object_key = normalized_image_url.lstrip("/")

    # 处理本地 URL
    if object_key:
        try:
            from app.services.asset_service import get_asset_service
            import base64

            logger.info("从上传图片地址提取 object_key: %s", object_key)
            
            # 获取文件内容
            asset_service = get_asset_service()
            bucket_name = ai_config.MINIO_BUCKET_ASSETS
            logger.info("尝试从 MinIO 读取图片: bucket=%s, key=%s", bucket_name, object_key)
            
            resp = asset_service.client.get_object(
                bucket_name=bucket_name,
                object_name=object_key
            )
            file_data = resp.read()
            resp.close()
            resp.release_conn()
            
            # 转 Base64
            b64_data = base64.b64encode(file_data).decode("utf-8")
            
            # 确定 mime type
            mime_type = "image/jpeg"
            if object_key.lower().endswith(".png"):
                mime_type = "image/png"
            elif object_key.lower().endswith(".gif"):
                mime_type = "image/gif"
            elif object_key.lower().endswith(".webp"):
                mime_type = "image/webp"
                
            image_url = f"data:{mime_type};base64,{b64_data}"
            logger.info("已将本地图片转换为 Base64 (len=%d, mime=%s)", len(b64_data), mime_type)
            
        except Exception as e:
            logger.exception("读取本地图片失败: url=%s, error=%s", image_url, e)
            return f"读取图片失败: {str(e)}"

    headers = {
        "Authorization": f"Bearer {config.api_key}",
        "Content-Type": "application/json",
    }

    default_headers = extra_config.get("default_headers")
    if isinstance(default_headers, dict):
        headers.update(default_headers)
    if _is_truthy(extra_config.get("send_x_api_key")):
        headers["X-API-Key"] = config.api_key

    base_url = config.base_url.rstrip("/") if config.base_url else ""

    if use_responses_api:
        payload = {
            "model": config.model_code,
            "input": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_image",
                            "image_url": image_url,
                        },
                        {
                            "type": "input_text",
                            "text": question,
                        },
                    ],
                }
            ],
            "max_output_tokens": config.max_output_tokens or 1024,
        }
        payload.update(request_params)

        api_url = f"{base_url}/responses"
        logger.info("Vision 调用接口: responses (%s)", api_url)
        response = httpx.post(
            api_url,
            headers=headers,
            json=payload,
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        return _extract_responses_text(data)
    
    # 构建请求体（兼容 OpenAI 格式）
    payload = {
        "model": config.model_code,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": image_url}
                    },
                    {
                        "type": "text",
                        "text": question
                    }
                ]
            }
        ],
        "max_tokens": config.max_output_tokens or 1024,
    }

    payload.update(request_params)

    api_url = f"{base_url}/chat/completions"
    logger.info("Vision 调用接口: chat_completions (%s)", api_url)
    
    response = httpx.post(
        api_url,
        headers=headers,
        json=payload,
        timeout=60,
    )
    response.raise_for_status()
    
    data = response.json()
    return data["choices"][0]["message"]["content"]



@tool(args_schema=ImageAnalysisInput)
def analyze_image(image_url: str, question: str = "请描述这张图片的内容") -> str:
    """分析图片内容并回答问题。
    
    当用户上传图片或询问图片相关问题时使用此工具。
    可以：
    - 描述图片内容
    - 识别图片中的文字（OCR）
    - 回答关于图片的问题
    
    返回图片分析结果和问题的回答。
    """
    if not is_vision_configured():
        return "⚠️ 图片分析功能未配置：请在模型路由中设置 vision，或添加 Vision 类型模型"
    
    try:
        logger.info("分析图片: url=%s, question=%s", image_url[:50], question[:30])
        
        result = _call_vision_model(image_url, question)
        
        logger.info("图片分析完成")
        return result
        
    except httpx.HTTPStatusError as e:
        status_code = e.response.status_code if e.response else "unknown"
        endpoint = str(e.request.url) if e.request else "unknown"
        logger.error("Vision API 错误: status=%s, endpoint=%s, err=%s", status_code, endpoint, e)
        return f"图片分析失败: Vision 接口 HTTP {status_code}（endpoint={endpoint}）"
    except httpx.ConnectError as e:
        logger.error("无法连接到 Vision 服务: %s", e)
        return "图片分析服务连接失败"
    except Exception as e:
        logger.exception("图片分析异常: %s", e)
        return f"图片分析失败: {str(e)}"


def is_vision_configured() -> bool:
    """检查 Vision 路由是否已配置可用模型。"""
    return _get_vision_model_config() is not None
