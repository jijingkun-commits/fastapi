"""文档记忆仓储混合检索测试。"""

import app.repositories.document_memory_repo as repo


class _MappingResult:
    def __init__(self, rows):
        self._rows = rows

    def mappings(self):
        return self

    def all(self):
        return self._rows

    def first(self):
        if not self._rows:
            return None
        return self._rows[0]


class _DummySession:
    def __init__(self, responses):
        self._responses = responses
        self.calls = []

    def execute(self, sql, params):  # noqa: ANN001
        self.calls.append(params)
        return _MappingResult(self._responses.pop(0))


class _StatusDummySession:
    def __init__(self, responses):
        self._responses = responses
        self.calls = []

    def execute(self, sql, params):  # noqa: ANN001
        self.calls.append((str(sql), params))
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


def test_embedding_status_sql_should_use_cast_syntax() -> None:
    """向量状态 SQL 不能使用 psycopg 不兼容的 :param::type 语法。"""

    db = _StatusDummySession(
        [
            [
                {
                    "total": 0,
                    "pending": 0,
                    "ready": 0,
                    "failed": 0,
                }
            ]
        ]
    )

    payload = repo.get_embedding_status_counts(db, source="memory")

    assert payload["total"] == 0
    executed_sql, executed_params = db.calls[0]
    assert ":user_id::int" not in executed_sql
    assert ":doc_id::bigint" not in executed_sql
    assert "COALESCE(CAST(:user_id AS int), c.user_id)" in executed_sql
    assert "COALESCE(CAST(:doc_id AS bigint), c.doc_id)" in executed_sql
    assert executed_params["user_id"] is None
    assert executed_params["doc_id"] is None
