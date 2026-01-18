"""Vision 图片理解工具（中文注释）。

提供图片理解能力，支持配置化的 Vision 模型。
从 LLMConfigService 获取 model_type='vision' 的模型配置。
"""
import httpx
import logging
from typing import Optional
from pydantic import BaseModel, Field
from langchain.tools import tool

from app.services.llm_config_service import LLMConfigService
from app.core import config as ai_config

logger = logging.getLogger(__name__)


class ImageAnalysisInput(BaseModel):
    """图片分析输入参数。"""
    image_url: str = Field(description="图片 URL 地址")
    question: Optional[str] = Field(
        default="请描述这张图片的内容，尽量详细一些，除了文字内容，对图片里的东西也要做一个描述。",
        description="关于图片的问题"
    )


def _call_vision_model(image_url: str, question: str) -> str:
    """调用 Vision 模型分析图片。
    
    从 LLMConfigService 获取 vision 类型的模型配置。
    
    Args:
        image_url: 图片 URL
        question: 关于图片的问题
        
    Returns:
        模型回答
    """
    config = LLMConfigService.get_model_by_type("vision")
    if not config:
        return "⚠️ Vision 模型未配置，请在数据库中添加 model_type='vision' 的模型"
    
    if not config.api_key:
        return f"⚠️ Vision 模型 {config.model_code} 的 API Key 未配置"
    
    # 处理本地 URL
    if image_url.startswith("/") or image_url.startswith("http://localhost") or image_url.startswith("minio://"):
        try:
            from app.services.asset_service import get_asset_service
            import base64
            
            # 提取 object_key
            object_key = image_url
            if "/api/v1/assets/" in image_url:
                object_key = image_url.split("/api/v1/assets/")[-1]
                logger.info("从 URL 提取 object_key: %s", object_key)
            elif image_url.startswith("minio://"):
                # minio://bucket/path/to/file -> path/to/file
                parts = image_url.replace("minio://", "").split("/", 1)
                if len(parts) > 1:
                    object_key = parts[1]
                logger.info("从 minio:// URL 提取 object_key: %s", object_key)
            
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
    
    # 从 extra_config 获取额外参数
    if config.extra_config:
        payload.update(config.extra_config.get("request_params", {}))
    
    # 确定 API 端点
    base_url = config.base_url.rstrip("/") if config.base_url else ""
    api_url = f"{base_url}/chat/completions"
    
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
        return "⚠️ 图片分析功能未配置：请在模型管理中添加 Vision 类型的模型"
    
    try:
        logger.info("分析图片: url=%s, question=%s", image_url[:50], question[:30])
        
        result = _call_vision_model(image_url, question)
        
        logger.info("图片分析完成")
        return result
        
    except httpx.HTTPStatusError as e:
        logger.error("Vision API 错误: %s", e)
        return f"图片分析失败: HTTP {e.response.status_code}"
    except httpx.ConnectError as e:
        logger.error("无法连接到 Vision 服务: %s", e)
        return "图片分析服务连接失败"
    except Exception as e:
        logger.exception("图片分析异常: %s", e)
        return f"图片分析失败: {str(e)}"


def is_vision_configured() -> bool:
    """检查 Vision 模型是否已配置。"""
    return LLMConfigService.is_type_configured("vision")
