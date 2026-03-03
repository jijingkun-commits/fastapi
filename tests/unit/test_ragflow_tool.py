"""RAGFlow 工具测试（中文注释）。

验证知识库图片占位符分配与去重行为。
"""

import requests

from app.ai.tools import ragflow_tool
from app.ai.tools.ragflow_tool import _call_ragflow_retrieval, _format_retrieval_results


def test_call_ragflow_retrieval_payload_should_split_page_size_and_top_k(monkeypatch) -> None:
    """请求 payload 应同时包含 page_size 与 top_k。"""

    captured: dict = {}

    class _FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"code": 0, "data": {"chunks": []}}

    def _fake_post(url: str, headers: dict, json: dict, timeout: float) -> _FakeResponse:
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        captured["timeout"] = timeout
        return _FakeResponse()

    monkeypatch.setattr(ragflow_tool.requests, "post", _fake_post)
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_API_URL", "http://unit.test/api/v1")
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_API_KEY", "test-key")

    response = _call_ragflow_retrieval(
        query="差旅报销流程",
        dataset_ids=["kb-1"],
        similarity_threshold=0.35,
        page_size=3,
        top_k=9,
        vector_weight=0.7,
        timeout_seconds=12,
    )

    assert response["code"] == 0
    assert captured["url"] == "http://unit.test/api/v1/retrieval"
    assert captured["headers"]["Authorization"] == "Bearer test-key"
    assert captured["json"] == {
        "question": "差旅报销流程",
        "dataset_ids": ["kb-1"],
        "similarity_threshold": 0.35,
        "page_size": 3,
        "top_k": 9,
        "vector_similarity_weight": 0.7,
    }
    assert captured["timeout"] == 12


def test_knowledge_search_payload_should_keep_dataset_override_compatibility(monkeypatch) -> None:
    """显式 dataset_id 仍应优先于默认配置。"""

    captured: dict = {}

    def _fake_retrieval(**kwargs) -> dict:
        captured.update(kwargs)
        return {"code": 0, "data": {"chunks": []}}

    monkeypatch.setattr(ragflow_tool, "_call_ragflow_retrieval", _fake_retrieval)
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_API_KEY", "test-key")
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_DATASET_IDS", ["kb-default"])
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_SIMILARITY_THRESHOLD", 0.2)
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_PAGE_SIZE", 4)
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_TOP_K", 8)
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_VECTOR_WEIGHT", 0.6)
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_TIMEOUT_SECONDS", 20)

    result = ragflow_tool.knowledge_search.func(query="公司请假制度", dataset_id="kb-override")

    assert result == "未找到相关信息。"
    assert captured == {
        "query": "公司请假制度",
        "dataset_ids": ["kb-override"],
        "similarity_threshold": 0.2,
        "page_size": 4,
        "top_k": 8,
        "vector_weight": 0.6,
        "timeout_seconds": 20,
    }


def test_knowledge_search_timeout_should_return_degraded_message(monkeypatch) -> None:
    """请求超时应返回可读降级文案，而不是抛异常。"""

    def _raise_timeout(**_: dict) -> dict:
        raise requests.exceptions.Timeout("ragflow timeout")

    monkeypatch.setattr(ragflow_tool, "_call_ragflow_retrieval", _raise_timeout)
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_API_KEY", "test-key")
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_DATASET_IDS", ["kb-default"])
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_SIMILARITY_THRESHOLD", 0.2)
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_PAGE_SIZE", 4)
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_TOP_K", 8)
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_VECTOR_WEIGHT", 0.6)
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_TIMEOUT_SECONDS", 20)

    result = ragflow_tool.knowledge_search.func(query="社保政策", dataset_id=None)

    assert "知识库检索超时" in result


def test_format_retrieval_results_should_deduplicate_same_image_url() -> None:
    """同一图片在多个片段出现时，只分配一次占位符。"""
    chunks = [
        {
            "content": "第一段内容",
            "document_keyword": "文档A",
            "similarity": 0.91,
            "image_id": "img-dup",
        },
        {
            "content": "第二段内容",
            "document_keyword": "文档B",
            "similarity": 0.87,
            "img_id": "img-dup",
        },
    ]

    formatted_text, kb_images = _format_retrieval_results(chunks)

    assert kb_images == {0: "/api/v1/assets/proxy/ragflow/img-dup"}
    assert formatted_text.count("[IMG-0]") == 1
    assert "【1】第二段内容" in formatted_text
    assert "【1】第二段内容\n   相关图片:" not in formatted_text


def test_format_retrieval_results_should_keep_stable_placeholder_indices() -> None:
    """多个图片时，占位符按首次出现顺序稳定递增。"""
    chunks = [
        {
            "content": "内容1",
            "document_keyword": "文档1",
            "similarity": 0.95,
            "image_id": "img-a",
        },
        {
            "content": "内容2",
            "document_keyword": "文档2",
            "similarity": 0.90,
            "image_id": "img-b",
        },
        {
            "content": "内容3",
            "document_keyword": "文档3",
            "similarity": 0.88,
            "image_id": "img-a",
        },
    ]

    formatted_text, kb_images = _format_retrieval_results(chunks)

    assert kb_images == {
        0: "/api/v1/assets/proxy/ragflow/img-a",
        1: "/api/v1/assets/proxy/ragflow/img-b",
    }
    assert "相关图片: [IMG-0]" in formatted_text
    assert "相关图片: [IMG-1]" in formatted_text
    assert formatted_text.count("相关图片:") == 2


def test_format_retrieval_results_should_ignore_blank_image_id() -> None:
    """空白 image_id 不应产出占位符。"""
    chunks = [
        {
            "content": "内容",
            "document_keyword": "文档",
            "similarity": 0.80,
            "image_id": "   ",
        }
    ]

    formatted_text, kb_images = _format_retrieval_results(chunks)

    assert kb_images == {}
    assert "相关图片:" not in formatted_text
