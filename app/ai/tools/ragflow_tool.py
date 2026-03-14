"""RAGFlow 知识库检索工具（中文注释）。

提供与 RAGFlow 服务的集成，支持从企业知识库检索相关信息。
"""
import re
import requests
import logging
import json
import os
import hashlib
from typing import Any, Optional
from pydantic import BaseModel, Field
from langchain.tools import tool

from app.core import config
from app.ai.protocol import AgentOutputParser, AgentProtocol, build_research_result_payload

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
    metadata_condition: dict[str, Any] | None = None,
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
        metadata_condition: 元数据过滤条件
        
    Returns:
        API 响应数据
    """
    try:
        effective_page_size = top_k if page_size is None else page_size
        payload: dict[str, Any] = {
            "question": query,
            "dataset_ids": dataset_ids,
            "similarity_threshold": similarity_threshold,
            "page_size": effective_page_size,
            "top_k": top_k,
            "vector_similarity_weight": vector_weight,
        }
        if metadata_condition:
            payload["metadata_condition"] = metadata_condition

        response = requests.post(
            f"{config.RAGFLOW_API_URL}/retrieval",
            headers={"Authorization": f"Bearer {config.RAGFLOW_API_KEY}"},
            json=payload,
            timeout=timeout_seconds,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        # 统一抛出异常，由上层捕获
        raise e

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


def _to_non_negative_float(value: Any, default: float) -> float:
    """将配置值转换为非负浮点数，非法值回退默认值。"""
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed >= 0 else default


def _to_percent_int(value: Any, default: int) -> int:
    """将配置值转换为 0-100 的百分比整数。"""
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(0, min(parsed, 100))


def _get_config_value(key: str, default: Any) -> Any:
    """优先读取 config 属性，不存在时回退环境变量。"""
    if hasattr(config, key):
        return getattr(config, key)
    env_value = os.getenv(key)
    if env_value is None:
        return default
    return env_value


def _collect_selected_document_ids(chunks: list[dict[str, Any]]) -> list[str]:
    """提取去重后的文档 ID 列表，便于检索观测统计。"""
    document_ids: list[str] = []
    seen: set[str] = set()

    for chunk in chunks:
        raw_doc_id = chunk.get("document_id") or chunk.get("doc_id")
        doc_id = str(raw_doc_id).strip() if raw_doc_id is not None else ""
        if not doc_id:
            doc_id = _resolve_chunk_document_key(chunk)
        if not doc_id or doc_id in seen:
            continue
        seen.add(doc_id)
        document_ids.append(doc_id)

    return document_ids


def _build_retrieval_log(
    *,
    phase: str,
    query: str,
    datasets: list[str],
    retrieval_routes: list[dict[str, Any]],
    routed_domain: str | None,
    metadata_condition: dict[str, Any] | None,
    enable_query_rewrite: bool,
    enable_multi_route_rerank: bool,
    enable_domain_routing: bool,
    rollout_stage: str,
    rollout_traffic_percent: int,
    rollback_target_stage: str,
    rollback_switch_enabled: bool,
    metrics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """构建统一检索观测日志，便于灰度追踪与回滚排障。"""
    route_ids = [str(route.get("route_id") or "unknown") for route in retrieval_routes]
    payload: dict[str, Any] = {
        "phase": phase,
        "query_preview": query[:80],
        "dataset_count": len(datasets),
        "datasets": [str(dataset) for dataset in datasets],
        "route_count": len(route_ids),
        "route_ids": route_ids,
        "rewrite_enabled": bool(enable_query_rewrite),
        "rerank_enabled": bool(enable_multi_route_rerank),
        "domain_routing_enabled": bool(enable_domain_routing),
        "metadata_filter_enabled": bool(metadata_condition),
        "routed_domain": routed_domain,
        "rollout": {
            "stage": rollout_stage,
            "traffic_percent": rollout_traffic_percent,
            "rollback_target_stage": rollback_target_stage,
            "rollback_switch_enabled": rollback_switch_enabled,
        },
    }
    if metrics:
        payload["metrics"] = metrics
    return payload


def _chunk_similarity(chunk: dict) -> float:
    """读取 chunk 相似度。"""
    try:
        return float(chunk.get("similarity", 0) or 0)
    except (TypeError, ValueError):
        return 0.0


def _chunk_rank_score(chunk: dict) -> float:
    """读取用于候选筛选排序的分数。"""
    try:
        return float(chunk.get("final_score", chunk.get("similarity", 0)) or 0)
    except (TypeError, ValueError):
        return _chunk_similarity(chunk)


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


def _normalize_rewrite_terms(raw_terms: Any) -> dict[str, list[str]]:
    """归一化改写词配置。"""

    def _as_term_list(value: Any) -> list[str]:
        if isinstance(value, str):
            return [part.strip() for part in value.split(",") if part.strip()]
        if isinstance(value, (list, tuple, set)):
            terms = []
            for item in value:
                text = str(item).strip()
                if text:
                    terms.append(text)
            return terms
        return []

    if raw_terms is None:
        return {}

    source: Any = raw_terms
    if isinstance(raw_terms, str):
        payload = raw_terms.strip()
        if not payload:
            return {}
        try:
            source = json.loads(payload)
        except json.JSONDecodeError:
            source = payload

    if isinstance(source, dict):
        normalized: dict[str, list[str]] = {}
        for key, value in source.items():
            key_text = str(key).strip() or "__default__"
            terms = _as_term_list(value)
            if terms:
                normalized[key_text] = terms
        return normalized

    terms = _as_term_list(source)
    return {"__default__": terms} if terms else {}


_DEFAULT_DOMAIN_HINTS: dict[str, list[str]] = {
    "todo": ["待办", "任务", "提醒", "清单", "todo"],
    "data": ["数据", "指标", "报表", "统计", "sql", "数据库", "分析"],
    "process": ["制度", "流程", "规范", "审批", "报销", "请假"],
    "product": ["产品", "功能", "渠道", "能力", "特性"],
}


def _normalize_domain_hints(raw_hints: Any) -> dict[str, list[str]]:
    """归一化领域路由提示词配置。"""

    def _as_term_list(value: Any) -> list[str]:
        if isinstance(value, str):
            return [part.strip() for part in value.split(",") if part.strip()]
        if isinstance(value, (list, tuple, set)):
            terms = []
            for item in value:
                text = str(item).strip()
                if text:
                    terms.append(text)
            return terms
        return []

    if raw_hints is None:
        return dict(_DEFAULT_DOMAIN_HINTS)

    source: Any = raw_hints
    if isinstance(raw_hints, str):
        payload = raw_hints.strip()
        if not payload:
            return dict(_DEFAULT_DOMAIN_HINTS)
        try:
            source = json.loads(payload)
        except json.JSONDecodeError:
            logger.warning("RAGFLOW_DOMAIN_ROUTING_HINTS 不是合法 JSON，回退默认领域词典")
            return dict(_DEFAULT_DOMAIN_HINTS)

    if not isinstance(source, dict):
        logger.warning("RAGFLOW_DOMAIN_ROUTING_HINTS 类型非法，回退默认领域词典")
        return dict(_DEFAULT_DOMAIN_HINTS)

    normalized: dict[str, list[str]] = {}
    for raw_domain, raw_terms in source.items():
        domain = str(raw_domain).strip().lower()
        if not domain:
            continue
        terms = _as_term_list(raw_terms)
        if terms:
            normalized[domain] = terms

    return normalized or dict(_DEFAULT_DOMAIN_HINTS)


def _detect_query_domain(raw_query: str, domain_hints: dict[str, list[str]]) -> str | None:
    """根据 query 命中情况推断领域。"""
    normalized_query = str(raw_query or "").strip().lower()
    if not normalized_query:
        return None

    best_domain: str | None = None
    best_hits = 0
    best_position = len(normalized_query) + 1

    for domain, hints in domain_hints.items():
        hits = 0
        first_position = len(normalized_query) + 1
        for hint in hints:
            normalized_hint = str(hint).strip().lower()
            if not normalized_hint:
                continue
            position = normalized_query.find(normalized_hint)
            if position < 0:
                continue
            hits += 1
            first_position = min(first_position, position)

        if hits > best_hits or (hits == best_hits and hits > 0 and first_position < best_position):
            best_domain = domain
            best_hits = hits
            best_position = first_position

    return best_domain if best_hits > 0 else None


def _build_metadata_condition(
    raw_query: str,
    *,
    enable_domain_routing: bool,
    domain_hints: Any,
    metadata_field: str = "domain",
) -> dict[str, Any] | None:
    """根据 query 领域构造 metadata 过滤条件。"""
    if not enable_domain_routing:
        return None

    safe_metadata_field = str(metadata_field or "").strip() or "domain"

    try:
        normalized_hints = _normalize_domain_hints(domain_hints)
        detected_domain = _detect_query_domain(raw_query, normalized_hints)
        if not detected_domain:
            return None

        return {
            "operator": "and",
            "conditions": [
                {
                    "field": safe_metadata_field,
                    "operator": "eq",
                    "value": detected_domain,
                }
            ],
        }
    except Exception as exc:
        logger.warning("构造 metadata 过滤条件失败，回退全库检索: %s", exc)
        return None


def _is_metadata_filter_error(error_msg: str | None) -> bool:
    """判断错误是否来自 metadata 过滤条件。"""
    normalized = str(error_msg or "").strip().lower()
    if not normalized:
        return False

    metadata_error_hints = (
        "metadata",
        "filter",
        "condition",
        "field",
        "where",
    )
    return any(hint in normalized for hint in metadata_error_hints)


def _retrieve_chunks_with_metadata_fallback(
    query: str,
    *,
    dataset_ids: list[str],
    similarity_threshold: float,
    page_size: int,
    top_k: int,
    vector_weight: float,
    timeout_seconds: float,
    metadata_condition: dict[str, Any] | None,
    route_id: str,
) -> tuple[list[dict[str, Any]], str | None, bool]:
    """执行检索，metadata 过滤失败时回退无过滤路径。"""

    def _retrieve(metadata_filter: dict[str, Any] | None) -> tuple[list[dict[str, Any]], str | None]:
        return _retrieve_chunks_for_query(
            query,
            dataset_ids=dataset_ids,
            similarity_threshold=similarity_threshold,
            page_size=page_size,
            top_k=top_k,
            vector_weight=vector_weight,
            timeout_seconds=timeout_seconds,
            metadata_condition=metadata_filter,
        )

    if not metadata_condition:
        chunks, error_msg = _retrieve(None)
        return chunks, error_msg, False

    try:
        chunks, error_msg = _retrieve(metadata_condition)
    except requests.exceptions.RequestException as exc:
        logger.warning("领域路由检索请求异常，回退无过滤检索: route=%s, error=%s", route_id, exc)
        fallback_chunks, fallback_error = _retrieve(None)
        return fallback_chunks, fallback_error, True

    if error_msg and _is_metadata_filter_error(error_msg):
        logger.warning("领域路由 metadata 过滤失败，回退无过滤检索: route=%s, error=%s", route_id, error_msg)
        fallback_chunks, fallback_error = _retrieve(None)
        return fallback_chunks, fallback_error, True

    return chunks, error_msg, False


def _build_retrieval_queries(
    raw_query: str,
    *,
    enable_query_rewrite: bool,
    rewrite_terms: Any,
    max_rewrite_queries: int = 2,
    main_route_weight: float = 1.0,
    rewrite_route_weight: float = 0.7,
) -> list[dict[str, Any]]:
    """构造检索路由：原问主路 + 扩展路。"""
    base_query = str(raw_query or "").strip()
    if not base_query:
        return []

    routes = [
        {
            "route_id": "main",
            "route_name": "原问主路",
            "query": base_query,
            "route_weight": _to_non_negative_float(main_route_weight, 1.0),
        }
    ]
    if not enable_query_rewrite:
        return routes

    try:
        normalized_terms = _normalize_rewrite_terms(rewrite_terms)
        matched_terms: list[str] = []
        for key, terms in normalized_terms.items():
            if key != "__default__" and key not in base_query:
                continue
            matched_terms.extend(terms)

        unique_terms: list[str] = []
        seen_terms: set[str] = set()
        for term in matched_terms:
            normalized = str(term).strip()
            if not normalized or normalized in seen_terms:
                continue
            if normalized in base_query:
                continue
            seen_terms.add(normalized)
            unique_terms.append(normalized)

        rewrite_limit = _to_positive_int(max_rewrite_queries, 2)
        safe_rewrite_weight = _to_non_negative_float(rewrite_route_weight, 0.7)
        for index, term in enumerate(unique_terms[:rewrite_limit], start=1):
            routes.append(
                {
                    "route_id": f"rewrite_{index}",
                    "route_name": f"扩展路{index}",
                    "query": f"{base_query} {term}",
                    "route_weight": safe_rewrite_weight,
                }
            )
        return routes
    except Exception as exc:
        logger.warning("构造改写路由失败，回退原问主路: %s", exc)
        return routes


def _merge_and_rerank_candidates(
    chunks: list[dict[str, Any]],
    *,
    enable_rerank: bool,
    similarity_weight: float,
    route_weight_weight: float,
) -> list[dict[str, Any]]:
    """多路候选融合并重排，保留可解释分数字段。"""
    if not chunks:
        return []

    safe_similarity_weight = _to_non_negative_float(similarity_weight, 0.6)
    safe_route_weight_weight = _to_non_negative_float(route_weight_weight, 0.4)
    total_weight = safe_similarity_weight + safe_route_weight_weight
    if total_weight <= 0:
        safe_similarity_weight, safe_route_weight_weight = 1.0, 0.0
        total_weight = 1.0

    merged: dict[tuple[str, str], dict[str, Any]] = {}
    for chunk in chunks:
        doc_key = _resolve_chunk_document_key(chunk)
        content_key = _normalize_chunk_content(chunk.get("content", ""))
        if not content_key:
            fallback_id = chunk.get("chunk_id") or chunk.get("id")
            content_key = str(fallback_id or "")

        dedup_key = (doc_key, content_key)
        route_id = str(chunk.get("_route_id") or "main")
        route_weight = _to_non_negative_float(chunk.get("_route_weight"), 1.0)
        similarity = _chunk_similarity(chunk)

        existing = merged.get(dedup_key)
        if existing is None:
            merged_chunk = dict(chunk)
            merged_chunk["similarity"] = similarity
            merged_chunk["similarity_score"] = similarity
            merged_chunk["route_weight"] = route_weight
            merged_chunk["matched_routes"] = [route_id]
            merged_chunk["route_hits"] = 1
            merged[dedup_key] = merged_chunk
            continue

        existing["similarity"] = max(_chunk_similarity(existing), similarity)
        existing["similarity_score"] = existing["similarity"]
        existing["route_weight"] = max(_to_non_negative_float(existing.get("route_weight"), 0), route_weight)

        if route_id not in existing["matched_routes"]:
            existing["matched_routes"].append(route_id)
            existing["route_hits"] = len(existing["matched_routes"])

    reranked = list(merged.values())
    for chunk in reranked:
        similarity_score = _chunk_similarity(chunk)
        route_score = _to_non_negative_float(chunk.get("route_weight"), 0)
        coverage_bonus = 1.0 + 0.05 * max(int(chunk.get("route_hits", 1)) - 1, 0)

        if enable_rerank:
            final_score = (
                (safe_similarity_weight * similarity_score + safe_route_weight_weight * route_score) / total_weight
            ) * coverage_bonus
        else:
            final_score = similarity_score

        chunk["similarity_score"] = similarity_score
        chunk["route_score"] = route_score
        chunk["final_score"] = round(final_score, 6)

    reranked.sort(key=_chunk_rank_score, reverse=True)
    return reranked


def _retrieve_chunks_for_query(
    query: str,
    *,
    dataset_ids: list[str],
    similarity_threshold: float,
    page_size: int,
    top_k: int,
    vector_weight: float,
    timeout_seconds: float,
    metadata_condition: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], str | None]:
    """执行单路检索并兼容多知识库 hybrid fallback。"""
    retrieval_kwargs: dict[str, Any] = {
        "query": query,
        "dataset_ids": dataset_ids,
        "similarity_threshold": similarity_threshold,
        "page_size": page_size,
        "top_k": top_k,
        "vector_weight": vector_weight,
        "timeout_seconds": timeout_seconds,
    }
    if metadata_condition:
        retrieval_kwargs["metadata_condition"] = metadata_condition

    data = _call_ragflow_retrieval(
        **retrieval_kwargs,
    )
    if data.get("code") == 0:
        return data.get("data", {}).get("chunks", []), None

    error_msg = data.get("message", "未知错误")
    if "hybrid search" not in str(error_msg).lower() or len(dataset_ids) <= 1:
        return [], str(error_msg)

    logger.warning("多知识库不支持混合检索，尝试逐个检索并合并结果")
    all_chunks: list[dict[str, Any]] = []
    for single_id in dataset_ids:
        try:
            sub_kwargs = dict(retrieval_kwargs)
            sub_kwargs["dataset_ids"] = [single_id]
            sub_data = _call_ragflow_retrieval(**sub_kwargs)
        except requests.exceptions.RequestException as exc:
            logger.warning("知识库 %s 检索失败: %s", single_id, exc)
            continue

        if sub_data.get("code") == 0:
            all_chunks.extend(sub_data.get("data", {}).get("chunks", []))
            continue

        logger.warning("知识库 %s 检索失败: %s", single_id, sub_data.get("message", "未知错误"))

    if all_chunks:
        return all_chunks, None
    return [], str(error_msg)


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

    sorted_chunks = sorted(chunks, key=_chunk_rank_score, reverse=True)
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
        final_score = _chunk_rank_score(chunk)
        
        # 尝试获取文档下载链接
        document_id = chunk.get("document_id")
        source_link = ""
        if document_id:
            from urllib.parse import quote
            encoded_name = quote(source)
            source_link = f" ([⬇️ 下载](/api/v1/assets/proxy/ragflow/doc/{document_id}?name={encoded_name}))"

        result_text = f"【证据卡片{i}】 摘要: {snippet}\n   来源: {source}{source_link} | 相关度: {score:.2%}"
        if "final_score" in chunk:
            route_weight = _to_non_negative_float(chunk.get("route_weight"), 0)
            result_text += (
                f" | 综合分: {final_score:.4f}"
                f" (相似度: {score:.4f}, 路由权重: {route_weight:.4f})"
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
        enable_candidate_dedup = _to_bool_flag(_get_config_value("RAGFLOW_ENABLE_CANDIDATE_DEDUP", True), True)
        enable_doc_cap = _to_bool_flag(_get_config_value("RAGFLOW_ENABLE_DOC_CAP", True), True)
        enable_query_rewrite = _to_bool_flag(_get_config_value("RAGFLOW_ENABLE_QUERY_REWRITE", False), False)
        enable_multi_route_rerank = _to_bool_flag(_get_config_value("RAGFLOW_ENABLE_MULTI_ROUTE_RERANK", False), False)
        enable_domain_routing = _to_bool_flag(_get_config_value("RAGFLOW_ENABLE_DOMAIN_ROUTING", False), False)
        max_chunks_per_doc = _to_positive_int(_get_config_value("RAGFLOW_MAX_CHUNKS_PER_DOC", 2), 2)
        max_total_chunks = _to_positive_int(config.RAGFLOW_PAGE_SIZE, 8)
        max_evidence_chars = _to_positive_int(_get_config_value("RAGFLOW_EVIDENCE_MAX_CHARS", 320), 320)
        max_rewrite_queries = _to_positive_int(_get_config_value("RAGFLOW_MAX_REWRITE_QUERIES", 2), 2)
        rewrite_terms = _get_config_value("RAGFLOW_QUERY_REWRITE_TERMS", None)
        domain_hints = _get_config_value("RAGFLOW_DOMAIN_ROUTING_HINTS", None)
        metadata_field = (
            str(_get_config_value("RAGFLOW_DOMAIN_METADATA_FIELD", "domain") or "domain").strip()
            or "domain"
        )
        main_route_weight = _to_non_negative_float(_get_config_value("RAGFLOW_MAIN_ROUTE_WEIGHT", 1.0), 1.0)
        rewrite_route_weight = _to_non_negative_float(_get_config_value("RAGFLOW_REWRITE_ROUTE_WEIGHT", 0.7), 0.7)
        similarity_weight = _to_non_negative_float(_get_config_value("RAGFLOW_RERANK_SIMILARITY_WEIGHT", 0.6), 0.6)
        route_weight_weight = _to_non_negative_float(_get_config_value("RAGFLOW_RERANK_ROUTE_WEIGHT", 0.4), 0.4)
        rollout_stage = str(_get_config_value("RAGFLOW_ROLLOUT_STAGE", "baseline") or "baseline").strip() or "baseline"
        rollout_traffic_percent = _to_percent_int(_get_config_value("RAGFLOW_ROLLOUT_TRAFFIC_PERCENT", 100), 100)
        rollback_target_stage = str(_get_config_value("RAGFLOW_ROLLBACK_TARGET_STAGE", "s4") or "s4").strip() or "s4"
        rollback_switch_enabled = _to_bool_flag(
            _get_config_value("RAGFLOW_ENABLE_ROLLBACK_SWITCH", True),
            True,
        )

        retrieval_routes = _build_retrieval_queries(
            query,
            enable_query_rewrite=enable_query_rewrite,
            rewrite_terms=rewrite_terms,
            max_rewrite_queries=max_rewrite_queries,
            main_route_weight=main_route_weight,
            rewrite_route_weight=rewrite_route_weight,
        )
        if not retrieval_routes:
            return "知识库检索失败: 查询内容为空"

        metadata_condition = _build_metadata_condition(
            query,
            enable_domain_routing=enable_domain_routing,
            domain_hints=domain_hints,
            metadata_field=metadata_field,
        )
        routed_domain: str | None = None
        if metadata_condition:
            conditions = metadata_condition.get("conditions", [])
            if conditions:
                routed_domain = str(conditions[0].get("value") or "").strip() or None

        logger.info(
            "RAGFlow 检索观测: %s",
            _build_retrieval_log(
                phase="start",
                query=query,
                datasets=target_datasets,
                retrieval_routes=retrieval_routes,
                routed_domain=routed_domain,
                metadata_condition=metadata_condition,
                enable_query_rewrite=enable_query_rewrite,
                enable_multi_route_rerank=enable_multi_route_rerank,
                enable_domain_routing=enable_domain_routing,
                rollout_stage=rollout_stage,
                rollout_traffic_percent=rollout_traffic_percent,
                rollback_target_stage=rollback_target_stage,
                rollback_switch_enabled=rollback_switch_enabled,
                metrics={
                    "requested_max_chunks": max_total_chunks,
                    "per_doc_limit": max_chunks_per_doc,
                },
            ),
        )

        route_chunks: list[dict[str, Any]] = []
        route_errors: list[str] = []
        raw_chunks_count = 0
        success_count = 0
        metadata_fallback_count = 0

        for route in retrieval_routes:
            route_id = route["route_id"]
            route_query = route["query"]
            try:
                chunks, error_msg, used_metadata_fallback = _retrieve_chunks_with_metadata_fallback(
                    route_query,
                    dataset_ids=target_datasets,
                    similarity_threshold=config.RAGFLOW_SIMILARITY_THRESHOLD,
                    page_size=config.RAGFLOW_PAGE_SIZE,
                    top_k=config.RAGFLOW_TOP_K,
                    vector_weight=config.RAGFLOW_VECTOR_WEIGHT,
                    timeout_seconds=config.RAGFLOW_TIMEOUT_SECONDS,
                    metadata_condition=metadata_condition,
                    route_id=route_id,
                )
            except requests.exceptions.Timeout as exc:
                if route_id == "main":
                    raise
                logger.warning("扩展路检索超时，已回退主路: route=%s, error=%s", route_id, exc)
                route_errors.append(f"{route_id}: timeout")
                continue
            except requests.exceptions.RequestException as exc:
                if route_id == "main":
                    raise
                logger.warning("扩展路检索失败，已回退主路: route=%s, error=%s", route_id, exc)
                route_errors.append(f"{route_id}: request_error")
                continue

            if used_metadata_fallback:
                metadata_fallback_count += 1

            if error_msg:
                if route_id == "main":
                    logger.warning(
                        "RAGFlow 检索失败: domain=%s, metadata=%s, error=%s",
                        routed_domain,
                        bool(metadata_condition),
                        error_msg,
                    )
                    return f"检索失败: {error_msg}"
                logger.warning("扩展路检索失败，已回退主路: route=%s, error=%s", route_id, error_msg)
                route_errors.append(f"{route_id}: {error_msg}")
                continue

            success_count += 1
            raw_chunks_count += len(chunks)
            route_weight = _to_non_negative_float(route.get("route_weight"), 1.0)
            for chunk in chunks:
                enriched_chunk = dict(chunk)
                enriched_chunk["_route_id"] = route_id
                enriched_chunk["_route_name"] = route.get("route_name")
                enriched_chunk["_route_weight"] = route_weight
                route_chunks.append(enriched_chunk)

        if success_count == 0:
            return "知识库检索失败: 所有检索路由均不可用"

        merged_chunks = _merge_and_rerank_candidates(
            route_chunks,
            enable_rerank=enable_multi_route_rerank,
            similarity_weight=similarity_weight,
            route_weight_weight=route_weight_weight,
        )
        selected_chunks = _dedup_and_cap_candidates(
            merged_chunks,
            max_chunks_per_doc=max_chunks_per_doc,
            max_total_chunks=max_total_chunks,
            enable_dedup=enable_candidate_dedup,
            enable_doc_cap=enable_doc_cap,
        )
        result_text, kb_images = _format_retrieval_results(selected_chunks, max_evidence_chars)

        fallback_count = len(retrieval_routes) - success_count
        logger.info(
            "RAGFlow 检索观测: %s",
            _build_retrieval_log(
                phase="complete",
                query=query,
                datasets=target_datasets,
                retrieval_routes=retrieval_routes,
                routed_domain=routed_domain,
                metadata_condition=metadata_condition,
                enable_query_rewrite=enable_query_rewrite,
                enable_multi_route_rerank=enable_multi_route_rerank,
                enable_domain_routing=enable_domain_routing,
                rollout_stage=rollout_stage,
                rollout_traffic_percent=rollout_traffic_percent,
                rollback_target_stage=rollback_target_stage,
                rollback_switch_enabled=rollback_switch_enabled,
                metrics={
                    "fallback_routes": fallback_count,
                    "raw_chunks": raw_chunks_count,
                    "merged_chunks": len(merged_chunks),
                    "selected_chunks": len(selected_chunks),
                    "selected_document_ids": _collect_selected_document_ids(selected_chunks),
                    "metadata_fallback_routes": metadata_fallback_count,
                    "per_doc_limit": max_chunks_per_doc,
                    "doc_cap_enabled": bool(enable_doc_cap),
                    "dedup_enabled": bool(enable_candidate_dedup),
                    "result_chars": len(result_text),
                    "kb_image_count": len(kb_images),
                    "route_errors": list(route_errors),
                },
            ),
        )
        if route_errors:
            logger.info("RAGFlow 扩展路回退详情: %s", route_errors)
        
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



@tool(args_schema=KnowledgeSearchInput)
def knowledge_research(query: str, dataset_id: str = None) -> str:
    """
    用于需要跨多条知识库资料做总结、对比、证据归纳时的 stateless research 入口。
    简单单点直查继续使用 knowledge_search。
    """
    payload = build_research_result_payload(**build_knowledge_research_source_payload(query=query, dataset_id=dataset_id))
    return json.dumps(payload, ensure_ascii=False)


def _strip_kb_images_marker(raw_result: str) -> str:
    return re.sub(AgentProtocol.KB_IMAGES_PATTERN, "", str(raw_result or "")).strip()


def build_knowledge_research_source_payload(query: str, dataset_id: str = None) -> dict[str, Any]:
    """将 knowledge_search 原子结果规整为 research source provider contract。"""
    raw_result = str(knowledge_search.func(query=query, dataset_id=dataset_id) or "").strip()
    summary_markdown = _strip_kb_images_marker(raw_result)
    kb_images = AgentOutputParser.parse_kb_images(raw_result) or {}
    evidence_lines = []
    for line in summary_markdown.splitlines():
        excerpt = str(line or "").strip()
        if not excerpt or excerpt.startswith("[IMG-"):
            continue
        evidence_lines.append({"source": "knowledge_search", "excerpt": excerpt[:240]})
        if len(evidence_lines) >= 3:
            break

    insufficiency = ""
    if not summary_markdown:
        insufficiency = "knowledge_search 未返回可用证据"
    elif any(token in summary_markdown for token in ("知识库检索失败", "知识库服务请求失败", "知识库检索超时")):
        insufficiency = summary_markdown[:240]

    media_refs = [
        {
            "type": "knowledge_image",
            "url": url,
            "alt": "知识库图片",
            "source": "knowledge",
            "index": str(index),
        }
        for index, url in sorted(kb_images.items(), key=lambda item: str(item[0]))
        if str(url or "").strip()
    ]

    return {
        "research_mode": "knowledge",
        "research_task_id": f"knowledge:{hashlib.sha1(str(query or '').encode('utf-8')).hexdigest()[:8]}",
        "summary": (evidence_lines[0]["excerpt"] if evidence_lines else summary_markdown[:240]),
        "summary_markdown": summary_markdown,
        "evidence": evidence_lines,
        "insufficiency": insufficiency,
        "source_count": 1 if evidence_lines else 0,
        "citation_count": max(summary_markdown.count("[IMG-"), len(media_refs)),
        "media_refs": media_refs,
    }

def is_ragflow_configured() -> bool:
    """检查 RAGFlow 是否已配置。"""
    return bool(config.RAGFLOW_API_KEY and config.RAGFLOW_DATASET_IDS)
