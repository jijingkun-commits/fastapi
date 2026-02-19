"""RAGFlow 工具测试（中文注释）。

验证知识库图片占位符分配与去重行为。
"""

from app.ai.tools.ragflow_tool import _format_retrieval_results


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
