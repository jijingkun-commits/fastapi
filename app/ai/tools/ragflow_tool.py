"""RAGFlow 知识库检索工具（中文注释）。

提供与 RAGFlow 服务的集成，支持从企业知识库检索相关信息。
"""
import requests
import logging
from typing import Any, Optional
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
    page_size: int | None = None,
    top_k: int = 5,
    vector_weight: float = 0.3,
    timeout_seconds: float = 30,
) -> dict:
    """调用 RAGFlow 检索 API。
    
    Args:
        query: 检索问题
        dataset_ids: 知识库 ID 列表
        similarity_threshold: 相似度阈值
        page_size: 返回结果数量（为空时回退 top_k）
        top_k: 候选召回深度
        vector_weight: 向量相似度权重（0-1），剩余为关键词权重
        timeout_seconds: 请求超时秒数
        
    Returns:
        API 响应数据
    """
    try:
        effective_page_size = top_k if page_size is None else page_size

        response = requests.post(
            f"{config.RAGFLOW_API_URL}/retrieval",
            headers={"Authorization": f"Bearer {config.RAGFLOW_API_KEY}"},
            json={
                "question": query,
                "dataset_ids": dataset_ids,
                "similarity_threshold": similarity_threshold,
                "page_size": effective_page_size,
                "top_k": top_k,
                "vector_similarity_weight": vector_weight,
            },
            timeout=timeout_seconds,
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


def _to_bool_flag(value: Any, default: bool) -> bool:
    """将配置值转换为布尔开关。"""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0

    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def _to_positive_int(value: Any, default: int) -> int:
    """将配置值转换为正整数，非法值回退默认值。"""
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def _chunk_similarity(chunk: dict) -> float:
    """读取 chunk 相似度。"""
    try:
        return float(chunk.get("similarity", 0) or 0)
    except (TypeError, ValueError):
        return 0.0


def _normalize_chunk_content(content: Any) -> str:
    """将 chunk 文本归一化用于去重和卡片摘要。"""
    return " ".join(str(content or "").split())


def _resolve_chunk_document_key(chunk: dict) -> str:
    """提取文档维度主键，用于同文档限额。"""
    for key in ("document_id", "doc_id", "document_keyword", "document_name"):
        value = chunk.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text

    fallback_chunk_id = chunk.get("chunk_id") or chunk.get("id")
    if fallback_chunk_id is not None:
        return f"chunk:{fallback_chunk_id}"

    return f"unknown:{id(chunk)}"


def _dedup_and_cap_candidates(
    chunks: list[dict],
    *,
    max_chunks_per_doc: int,
    max_total_chunks: int,
    enable_dedup: bool,
    enable_doc_cap: bool,
) -> list[dict]:
    """执行候选去重与同文档限额。"""
    if not chunks:
        return []

    safe_doc_cap = _to_positive_int(max_chunks_per_doc, 2)
    safe_total_cap = _to_positive_int(max_total_chunks, 30)

    sorted_chunks = sorted(chunks, key=_chunk_similarity, reverse=True)
    selected: list[dict] = []
    seen_keys: set[tuple[str, str]] = set()
    doc_counts: dict[str, int] = {}

    for chunk in sorted_chunks:
        if len(selected) >= safe_total_cap:
            break

        doc_key = _resolve_chunk_document_key(chunk)
        content_key = _normalize_chunk_content(chunk.get("content", ""))
        if not content_key:
            fallback_chunk_id = chunk.get("chunk_id") or chunk.get("id")
            content_key = str(fallback_chunk_id or "")

        dedup_key = (doc_key, content_key)
        if enable_dedup and content_key and dedup_key in seen_keys:
            continue

        if enable_doc_cap and doc_counts.get(doc_key, 0) >= safe_doc_cap:
            continue

        selected.append(chunk)
        doc_counts[doc_key] = doc_counts.get(doc_key, 0) + 1
        if enable_dedup and content_key:
            seen_keys.add(dedup_key)

    return selected


def _build_evidence_snippet(content: Any, max_chars: int) -> str:
    """生成证据卡片摘要文本。"""
    snippet = _normalize_chunk_content(content)
    if not snippet:
        return "（空片段）"

    safe_max_chars = _to_positive_int(max_chars, 320)
    if len(snippet) <= safe_max_chars:
        return snippet

    return f"{snippet[:safe_max_chars].rstrip()}..."


def _format_retrieval_results(chunks: list, max_evidence_chars: int = 320) -> tuple[str, dict]:
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
    kb_images = {}  # 图片映射 {占位符索引: URL}
    image_url_to_idx: dict[str, int] = {}
    logger.debug("JJK-ragchunks tool返回的前10条: %s", chunks)
    
    for i, chunk in enumerate(chunks, 0):
        content = chunk.get("content", "")
        snippet = _build_evidence_snippet(content, max_evidence_chars)
        
        # RAGFlow 使用 document_keyword 而非 document_name
        source = str(chunk.get("document_keyword") or chunk.get("document_name") or "未知来源")
        score = _chunk_similarity(chunk)
        
        # 尝试获取文档下载链接
        document_id = chunk.get("document_id")
        source_link = ""
        if document_id:
            from urllib.parse import quote
            encoded_name = quote(source)
            source_link = f" ([⬇️ 下载](/api/v1/assets/proxy/ragflow/doc/{document_id}?name={encoded_name}))"

        result_text = (
            f"【证据卡片{i}】 摘要: {snippet}\n"
            f"   来源: {source}{source_link} | 相关度: {score:.2%}"
        )
        
        # 如果有图片，使用占位符 [IMG-N]
        # 约束：同一图片 URL 在一次检索结果中只分配一个占位符，避免回答重复渲染相同图片
        image_id = chunk.get("image_id") or chunk.get("img_id")
        if image_id:
            image_id_str = str(image_id).strip()
            if image_id_str:
                image_url = f"/api/v1/assets/proxy/ragflow/{image_id_str}"
                if image_url not in image_url_to_idx:
                    placeholder_idx = len(image_url_to_idx)
                    image_url_to_idx[image_url] = placeholder_idx
                    kb_images[placeholder_idx] = image_url
                    result_text += f"\n   相关图片: [IMG-{placeholder_idx}]"
                else:
                    logger.info(
                        "跳过重复知识库图片: chunk_idx=%s, image_id=%s, placeholder=IMG-%s",
                        i,
                        image_id_str,
                        image_url_to_idx[image_url],
                    )

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
        enable_candidate_dedup = _to_bool_flag(getattr(config, "RAGFLOW_ENABLE_CANDIDATE_DEDUP", True), True)
        enable_doc_cap = _to_bool_flag(getattr(config, "RAGFLOW_ENABLE_DOC_CAP", True), True)
        max_chunks_per_doc = _to_positive_int(getattr(config, "RAGFLOW_MAX_CHUNKS_PER_DOC", 2), 2)
        max_total_chunks = _to_positive_int(config.RAGFLOW_PAGE_SIZE, 8)
        max_evidence_chars = _to_positive_int(getattr(config, "RAGFLOW_EVIDENCE_MAX_CHARS", 320), 320)

        logger.info("RAGFlow 检索: query=%s, datasets=%s", query[:50], target_datasets)
        
        # 调用 RAGFlow API（支持多知识库）
        data = _call_ragflow_retrieval(
            query=query,
            dataset_ids=target_datasets,
            similarity_threshold=config.RAGFLOW_SIMILARITY_THRESHOLD,
            page_size=config.RAGFLOW_PAGE_SIZE,
            top_k=config.RAGFLOW_TOP_K,
            vector_weight=config.RAGFLOW_VECTOR_WEIGHT,
            timeout_seconds=config.RAGFLOW_TIMEOUT_SECONDS,
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
                            page_size=config.RAGFLOW_PAGE_SIZE,
                            top_k=config.RAGFLOW_TOP_K,
                            vector_weight=config.RAGFLOW_VECTOR_WEIGHT,
                            timeout_seconds=config.RAGFLOW_TIMEOUT_SECONDS,
                        )
                        if sub_data.get("code") == 0:
                            chunks = sub_data.get("data", {}).get("chunks", [])
                            all_chunks.extend(chunks)
                    except Exception as e:
                        logger.warning(f"知识库 {single_id} 检索失败: {e}")
                
                # 按照相似度排序
                final_chunks = _dedup_and_cap_candidates(
                    all_chunks,
                    max_chunks_per_doc=max_chunks_per_doc,
                    max_total_chunks=max_total_chunks,
                    enable_dedup=enable_candidate_dedup,
                    enable_doc_cap=enable_doc_cap,
                )
                
                result_text, kb_images = _format_retrieval_results(final_chunks, max_evidence_chars)
                logger.info(
                    "混合检索完成: raw=%d, selected=%d, doc_cap=%s, dedup=%s, per_doc_limit=%d, 图片=%d",
                    len(all_chunks),
                    len(final_chunks),
                    enable_doc_cap,
                    enable_candidate_dedup,
                    max_chunks_per_doc,
                    len(kb_images),
                )
                
                # 将图片映射附加到返回值（使用特殊分隔符）
                if kb_images:
                    result_text += f"\n\n<!--KB_IMAGES:{json.dumps(kb_images)}-->"
                
                return result_text

            logger.warning("RAGFlow 检索失败: %s", error_msg)
            return f"检索失败: {error_msg}"
        
        # 格式化结果
        chunks = data.get("data", {}).get("chunks", [])
        selected_chunks = _dedup_and_cap_candidates(
            chunks,
            max_chunks_per_doc=max_chunks_per_doc,
            max_total_chunks=max_total_chunks,
            enable_dedup=enable_candidate_dedup,
            enable_doc_cap=enable_doc_cap,
        )
        result_text, kb_images = _format_retrieval_results(selected_chunks, max_evidence_chars)
        
        # 统计图片数量
        logger.info(
            "RAGFlow 检索完成: raw=%d, selected=%d, per_doc_limit=%d, doc_cap=%s, dedup=%s, 结果长度=%d, 图片映射=%d",
            len(chunks),
            len(selected_chunks),
            max_chunks_per_doc,
            enable_doc_cap,
            enable_candidate_dedup,
            len(result_text),
            len(kb_images),
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
        

    except requests.exceptions.Timeout as e:
        logger.warning("RAGFlow 请求超时: %s", e)
        return "知识库检索超时，请稍后重试。"
    except requests.exceptions.RequestException as e:
        logger.error("RAGFlow 请求错误: %s", e)
        return f"知识库服务请求失败: {e}"
    except Exception as e:
        logger.exception("RAGFlow 检索异常: %s", e)
        return f"知识库检索失败: {str(e)}"


def is_ragflow_configured() -> bool:
    """检查 RAGFlow 是否已配置。"""
    return bool(config.RAGFLOW_API_KEY and config.RAGFLOW_DATASET_IDS)
