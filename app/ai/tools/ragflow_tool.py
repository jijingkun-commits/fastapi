"""RAGFlow 知识库检索工具（中文注释）。

提供与 RAGFlow 服务的集成，支持从企业知识库检索相关信息。
"""
import requests
import logging
from typing import Optional
from pydantic import BaseModel, Field
from langchain.tools import tool

from app.core import config

logger = logging.getLogger(__name__)


class KnowledgeSearchInput(BaseModel):
    """知识库检索输入参数。"""
    query: str = Field(description="用户的原始问题，必须直接传递用户输入，严禁添加、删除或修改任何内容")
    dataset_id: Optional[str] = Field(
        default=None, 
        description="可选，指定知识库 ID，不填则使用默认知识库"
    )


def _call_ragflow_retrieval(
    query: str, 
    dataset_ids: list[str],
    similarity_threshold: float = 0.2,
    top_k: int = 5,
    vector_weight: float = 0.3,
) -> dict:
    """调用 RAGFlow 检索 API。
    
    Args:
        query: 检索问题
        dataset_ids: 知识库 ID 列表
        similarity_threshold: 相似度阈值
        top_k: 返回结果数量
        vector_weight: 向量相似度权重（0-1），剩余为关键词权重
        
    Returns:
        API 响应数据
    """
    try:
        response = requests.post(
            f"{config.RAGFLOW_API_URL}/retrieval",
            headers={"Authorization": f"Bearer {config.RAGFLOW_API_KEY}"},
            json={
                "question": query,
                "dataset_ids": dataset_ids,
                "similarity_threshold": similarity_threshold,
                "top_k": top_k,
                "vector_similarity_weight": vector_weight,
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        # 统一抛出异常，由上层捕获
        raise e

def _convert_ragflow_image_url(url: str) -> str:
    """将 RAGFlow 图片 URL 转换为代理 URL。
    
    Args:
        url: 原始 RAGFlow 图片 URL，如 http://localhost/v1/document/image/kb-img
        
    Returns:
        代理 URL，如 /api/v1/assets/proxy/ragflow/kb-img
    """
    import re
    # 匹配 /v1/document/image/{image_id} 格式
    match = re.search(r'/v1/document/image/([a-zA-Z0-9\-]+)', url)
    if match:
        image_id = match.group(1)
        return f"/api/v1/assets/proxy/ragflow/{image_id}"
    return url


def _format_retrieval_results(chunks: list) -> tuple[str, dict]:
    """格式化检索结果。
    
    Args:
        chunks: 检索到的文档块列表
        
    Returns:
        tuple: (formatted_text, kb_images)
            - formatted_text: 格式化的文本（包含 [IMG-N] 占位符）
            - kb_images: 图片映射 {索引: URL}
    """
    if not chunks:
        return "未找到相关信息。", {}
    
    results = []
    kb_images = {}  # 图片映射
    # 仅处理前 30 个片段
    chunks = chunks[:30]
    logger.debug("JJK-ragchunks tool返回的前10条: %s", chunks)
    
    for i, chunk in enumerate(chunks, 0):
        content = chunk.get("content", "")
        
        # RAGFlow 使用 document_keyword 而非 document_name
        source = chunk.get("document_keyword") or chunk.get("document_name", "未知来源")
        # similarity 已经是 0-1 范围的浮点数
        score = chunk.get("similarity", 0)
        
        # 尝试获取文档下载链接
        document_id = chunk.get("document_id")
        source_link = ""
        if document_id:
            from urllib.parse import quote
            encoded_name = quote(source)
            source_link = f" ([⬇️ 下载](/api/v1/assets/proxy/ragflow/doc/{document_id}?name={encoded_name}))"

        result_text = f"【{i}】{content}\n   📄 来源: {source}{source_link} | 相关度: {score:.2%}"
        
        # 如果有图片，使用占位符 [IMG-N]
        image_id = chunk.get("image_id") or chunk.get("img_id")
        if image_id:
            image_url = f"/api/v1/assets/proxy/ragflow/{image_id}"
            kb_images[i] = image_url
            result_text += f"\n   相关图片: [IMG-{i}]"

        results.append(result_text)
    
    return "\n\n".join(results), kb_images




@tool(args_schema=KnowledgeSearchInput)
def knowledge_search(query: str, dataset_id: str = None) -> str:
    """从企业知识库检索相关信息。
    
    当用户询问公司规范、制度、流程、项目文档、技术资料等内容时使用此工具。
    返回知识库中与问题最相关的内容及来源。
    
    【图片处理】
    - 检索结果中包含 [IMG-N] 格式的图片占位符
    - 在整合内容时，把相关的 [IMG-N] 放在对应段落附近
    - 系统会自动将占位符替换为实际图片
    """
    import json
    
    # 检查配置
    if not config.RAGFLOW_API_KEY:
        return "⚠️ 知识库未配置：请设置 RAGFLOW_API_KEY 环境变量"
    
    # 确定使用的知识库（支持多个）
    if dataset_id:
        # AI 指定了具体知识库
        target_datasets = [dataset_id]
    elif config.RAGFLOW_DATASET_IDS:
        # 使用配置的多知识库列表
        target_datasets = config.RAGFLOW_DATASET_IDS
    else:
        return "⚠️ 知识库 ID 未配置：请设置 RAGFLOW_DATASET_IDS 或 RAGFLOW_DATASET_ID 环境变量"
    
    try:
        logger.info("RAGFlow 检索: query=%s, datasets=%s", query[:50], target_datasets)
        
        # 调用 RAGFlow API（支持多知识库）
        data = _call_ragflow_retrieval(
            query=query,
            dataset_ids=target_datasets,
            similarity_threshold=config.RAGFLOW_SIMILARITY_THRESHOLD,
            top_k=config.RAGFLOW_TOP_K,
            vector_weight=config.RAGFLOW_VECTOR_WEIGHT,
        )
        
        # 检查响应
        if data.get("code") != 0:
            error_msg = data.get("message", "未知错误")
            
            # 混合检索回退逻辑
            if "hybrid search" in error_msg.lower() and len(target_datasets) > 1:
                logger.warning("多知识库不支持混合检索，尝试逐个检索并合并结果")
                
                all_chunks = []
                for single_id in target_datasets:
                    try:
                        sub_data = _call_ragflow_retrieval(
                            query=query,
                            dataset_ids=[single_id],
                            similarity_threshold=config.RAGFLOW_SIMILARITY_THRESHOLD,
                            top_k=config.RAGFLOW_TOP_K,
                            vector_weight=config.RAGFLOW_VECTOR_WEIGHT,
                        )
                        if sub_data.get("code") == 0:
                            chunks = sub_data.get("data", {}).get("chunks", [])
                            all_chunks.extend(chunks)
                    except Exception as e:
                        logger.warning(f"知识库 {single_id} 检索失败: {e}")
                
                # 按照相似度排序
                all_chunks.sort(key=lambda x: x.get("similarity", 0), reverse=True)
                # 取总的 top_k
                final_chunks = all_chunks[:config.RAGFLOW_TOP_K]
                
                result_text, kb_images = _format_retrieval_results(final_chunks)
                logger.info("混合检索完成: 合并后找到 %d 条结果, 图片=%d", len(final_chunks), len(kb_images))
                
                # 将图片映射附加到返回值（使用特殊分隔符）
                if kb_images:
                    result_text += f"\n\n<!--KB_IMAGES:{json.dumps(kb_images)}-->"
                
                return result_text

            logger.warning("RAGFlow 检索失败: %s", error_msg)
            return f"检索失败: {error_msg}"
        
        # 格式化结果
        chunks = data.get("data", {}).get("chunks", [])
        result_text, kb_images = _format_retrieval_results(chunks)
        
        # 统计图片数量
        logger.info(
            "RAGFlow 检索完成: chunks=%d, 结果长度=%d, 图片映射=%d",
            len(chunks), len(result_text), len(kb_images)
        )
        
        # 调试日志
        logger.debug("="*60)
        logger.debug("knowledge_search 工具返回值（前 1000 字符）:")
        logger.debug(result_text[:1000])
        logger.debug("kb_images 映射: %s", kb_images)
        logger.debug("="*60)
        
        # 将图片映射附加到返回值（使用 HTML 注释格式，LLM 不会输出这部分）
        if kb_images:
            result_text += f"\n\n<!--KB_IMAGES:{json.dumps(kb_images)}-->"
        
        return result_text
        

    except requests.exceptions.RequestException as e:
        logger.error("RAGFlow 请求错误: %s", e)
        return f"知识库服务请求失败: {e}"
    except Exception as e:
        logger.exception("RAGFlow 检索异常: %s", e)
        return f"知识库检索失败: {str(e)}"


def is_ragflow_configured() -> bool:
    """检查 RAGFlow 是否已配置。"""
    return bool(config.RAGFLOW_API_KEY and config.RAGFLOW_DATASET_IDS)
