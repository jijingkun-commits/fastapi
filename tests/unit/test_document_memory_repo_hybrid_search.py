"""文档记忆仓储混合检索测试。"""

import app.repositories.document_memory_repo as repo


class _MappingResult:
    def __init__(self, rows):
        self._rows = rows

    def mappings(self):
        return self

    def all(self):
        return self._rows


class _DummySession:
    def __init__(self, responses):
        self._responses = responses
        self.calls = []

    def execute(self, sql, params):  # noqa: ANN001
        self.calls.append(params)
        return _MappingResult(self._responses.pop(0))


def test_search_chunks_should_pass_hybrid_parameters() -> None:
    """混合检索参数应透传到 SQL 层。"""

    db = _DummySession(
        [
            [
                {
                    "doc_id": 1,
                    "doc_kind": "daily",
                    "doc_key": "2026-02-28",
                    "start_line": 1,
                    "end_line": 2,
                    "chunk_text": "记忆片段",
                    "text_score": 0.6,
                    "vector_score": 0.8,
                    "final_score": 0.74,
                }
            ]
        ]
    )

    results = repo.search_chunks(
        db,
        user_id=11,
        query_text="请回忆",
        limit=3,
        query_embedding=[0.1, 0.2],
        text_weight=0.2,
        vector_weight=0.8,
    )

    assert len(results) == 1
    assert db.calls[0]["query_embedding"] == [0.1, 0.2]
    assert db.calls[0]["text_weight"] == 0.2
    assert db.calls[0]["vector_weight"] == 0.8
    assert results[0]["final_score"] == 0.74


def test_search_chunks_should_fallback_when_primary_miss() -> None:
    """主检索未命中时应走 fallback 查询。"""

    db = _DummySession(
        [
            [],
            [
                {
                    "doc_id": 2,
                    "doc_kind": "daily",
                    "doc_key": "2026-02-27",
                    "start_line": 4,
                    "end_line": 5,
                    "chunk_text": "fallback",
                    "text_score": 0.0,
                    "vector_score": 0.0,
                    "final_score": 0.0,
                }
            ],
        ]
    )

    results = repo.search_chunks(
        db,
        user_id=5,
        query_text="query",
        limit=2,
        query_embedding=None,
    )

    assert len(results) == 1
    assert len(db.calls) == 2
    assert results[0]["chunk_text"] == "fallback"
