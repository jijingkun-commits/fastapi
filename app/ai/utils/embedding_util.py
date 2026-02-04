"""嵌入向量工具：生成文本向量（中文注释）。

通过 LLMConfigService 获取配置的 embedding 模型，支持智谱、OpenAI 等。

重要：数据库 Vector 列定义为 2048 维，必须使用对应维度的 embedding 模型：
- 智谱 embedding-3: 2048 维 ✅ 推荐
- 智谱 embedding-2: 1024 维 ❌ 不兼容
"""
import logging
from typing import List, Optional

from openai import OpenAI

from app.services.llm_config_service import LLMConfigService
from app.core.config import EMBEDDING_DIMENSION

logger = logging.getLogger(__name__)


class EmbeddingDimensionError(Exception):
    """Embedding 维度不匹配错误。"""
    pass


def get_embedding(text: str, model_code: Optional[str] = None) -> Optional[List[float]]:
    """生成文本的嵌入向量。
    
    Args:
        text: 待向量化的文本
        model_code: 指定模型代码，为 None 时使用默认 embedding 模型
        
    Returns:
        向量列表（必须为 EMBEDDING_DIMENSION 维，默认 2048）
        
    Raises:
        EmbeddingDimensionError: 当生成的向量维度与配置不匹配时
    """
    if not text or not text.strip():
        logger.warning("嵌入文本为空，跳过")
        return None
    
    # 获取 embedding 模型配置
    if model_code:
        config = LLMConfigService.get_model_config(model_code)
    else:
        config = LLMConfigService.get_model_by_type("embedding")
    
    if not config:
        logger.error("未找到 embedding 模型配置，请在 t_llm_models 中配置类型为 'embedding' 的模型")
        return None
    
    try:
        client = OpenAI(
            api_key=config.api_key,
            base_url=config.base_url
        )
        
        response = client.embeddings.create(
            model=config.model_code,
            input=text
        )
        
        embedding = response.data[0].embedding
        actual_dim = len(embedding)
        
        # 维度验证：确保与数据库 Vector 列定义一致
        if actual_dim != EMBEDDING_DIMENSION:
            error_msg = (
                f"Embedding 维度不匹配！"
                f"模型 {config.model_name} 输出 {actual_dim} 维，"
                f"但数据库要求 {EMBEDDING_DIMENSION} 维。"
                f"请在 t_llm_model 表中将 embedding 模型更换为 embedding-3（2048维）。"
            )
            logger.error(error_msg)
            raise EmbeddingDimensionError(error_msg)
        
        logger.debug(f"生成向量成功，维度: {actual_dim}, 模型: {config.model_name}")
        return embedding
        
    except EmbeddingDimensionError:
        raise  # 维度错误直接抛出
    except Exception as e:
        logger.error(f"生成嵌入向量失败: {e}")
        return None


async def get_embedding_async(text: str, model_code: Optional[str] = None) -> Optional[List[float]]:
    """异步版本的嵌入向量生成。
    
    目前使用同步调用，未来可优化为真正的异步。
    
    Raises:
        EmbeddingDimensionError: 当生成的向量维度与配置不匹配时
    """
    return get_embedding(text, model_code)


# 导出
__all__ = ["get_embedding", "get_embedding_async", "EmbeddingDimensionError", "EMBEDDING_DIMENSION"]
