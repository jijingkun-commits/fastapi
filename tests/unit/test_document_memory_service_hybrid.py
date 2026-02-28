"""文档记忆混合检索服务测试。"""

from dataclasses import dataclass

import app.services.document_memory_service as memory_service


@dataclass
class _DummySession:
    """占位 Session。"""


def test_memory_search_should_use_query_embedding(monkeypatch) -> None:  # noqa: ANN001
    """向量权重开启时应传递 query embedding 到仓储层。"""

    captured: dict = {}

    monkeypatch.setattr(memory_service, "get_embedding", lambda text: [0.11, 0.22])

    def _fake_search_chunks(db, **kwargs):  # noqa: ANN001
        captured.update(kwargs)
        return [
            {
                "doc_id": 1,
                "doc_kind": "daily",
                "doc_key": "2026-02-28",
                "start_line": 1,
                "end_line": 2,
                "chunk_text": "请记住：先结论后分析",
                "text_score": 0.6,
                "vector_score": 0.8,
                "final_score": 0.74,
            }
        ]

    monkeypatch.setattr(memory_service.document_memory_repo, "search_chunks", _fake_search_chunks)

    results = memory_service.memory_search(
        _DummySession(),
        user_id=9,
        query_text="以后先给结论",
        max_results=5,
        min_score=0.1,
        vector_weight=0.7,
        text_weight=0.3,
    )

    assert len(results) == 1
    assert captured["query_embedding"] == [0.11, 0.22]
    assert captured["vector_weight"] > 0
    assert results[0]["score"] == 0.74


def test_memory_search_should_downgrade_when_embedding_fails(monkeypatch) -> None:  # noqa: ANN001
    """生成 query embedding 失败时应降级为纯文本检索。"""

    captured: dict = {}

    def _raise_embedding(text: str):  # noqa: ARG001
        raise RuntimeError("embedding unavailable")

    monkeypatch.setattr(memory_service, "get_embedding", _raise_embedding)

    def _fake_search_chunks(db, **kwargs):  # noqa: ANN001
        captured.update(kwargs)
        return [
            {
                "doc_id": 2,
                "doc_kind": "daily",
                "doc_key": "2026-02-28",
                "start_line": 3,
                "end_line": 4,
                "chunk_text": "用户偏好：全程中文",
                "text_score": 0.55,
                "vector_score": 0.0,
                "final_score": 0.55,
            }
        ]

    monkeypatch.setattr(memory_service.document_memory_repo, "search_chunks", _fake_search_chunks)

    results = memory_service.memory_search(
        _DummySession(),
        user_id=3,
        query_text="之后请都用中文",
        max_results=4,
        min_score=0.1,
        vector_weight=0.8,
        text_weight=0.2,
    )

    assert len(results) == 1
    assert captured["query_embedding"] is None
    assert captured["vector_weight"] == 0.0
    assert results[0]["score"] == 0.55
