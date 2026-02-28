"""文档记忆向量补偿脚本集成测试。"""

from __future__ import annotations

import json
import sys

import scripts.memory.rebuild_document_embeddings as rebuild_script


class _DummyDbContext:
    """伪造 DB 上下文。"""

    def __enter__(self):
        return "dummy-db"

    def __exit__(self, exc_type, exc, tb):  # noqa: ANN001
        return False


def test_main_should_process_and_output_summary(monkeypatch, capsys) -> None:  # noqa: ANN001
    """脚本应调用补偿服务并输出 JSON 结果。"""

    captured: dict = {}

    monkeypatch.setattr(rebuild_script, "get_db_context", lambda: _DummyDbContext())

    def _fake_process_pending_chunks(db, **kwargs):  # noqa: ANN001
        captured["db"] = db
        captured.update(kwargs)
        return {
            "total": 2,
            "processed": 2,
            "ready": 2,
            "failed": 0,
            "elapsed_ms": 15,
        }

    monkeypatch.setattr(
        rebuild_script.document_memory_embedding_service,
        "process_pending_chunks",
        _fake_process_pending_chunks,
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "rebuild_document_embeddings.py",
            "--limit",
            "10",
            "--user-id",
            "42",
            "--doc-id",
            "9",
            "--status",
            "pending, failed",
            "--max-retry",
            "5",
        ],
    )

    exit_code = rebuild_script.main()
    payload = json.loads(capsys.readouterr().out.strip())

    assert exit_code == 0
    assert payload["ready"] == 2
    assert captured["db"] == "dummy-db"
    assert captured["limit"] == 10
    assert captured["user_id"] == 42
    assert captured["doc_id"] == 9
    assert captured["status_filter"] == ["pending", "failed"]
    assert captured["max_retry"] == 5


def test_main_should_return_two_when_failed(monkeypatch, capsys) -> None:  # noqa: ANN001
    """脚本在有失败分块时应返回 2。"""

    captured: dict = {}

    monkeypatch.setattr(rebuild_script, "get_db_context", lambda: _DummyDbContext())

    def _fake_process_pending_chunks(db, **kwargs):  # noqa: ANN001
        captured["db"] = db
        captured.update(kwargs)
        return {
            "total": 1,
            "processed": 1,
            "ready": 0,
            "failed": 1,
            "elapsed_ms": 20,
        }

    monkeypatch.setattr(
        rebuild_script.document_memory_embedding_service,
        "process_pending_chunks",
        _fake_process_pending_chunks,
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "rebuild_document_embeddings.py",
            "--limit",
            "0",
            "--status",
            "failed",
            "--max-retry",
            "-3",
        ],
    )

    exit_code = rebuild_script.main()
    payload = json.loads(capsys.readouterr().out.strip())

    assert exit_code == 2
    assert payload["failed"] == 1
    assert captured["db"] == "dummy-db"
    assert captured["limit"] == 1
    assert captured["status_filter"] == ["failed"]
    assert captured["max_retry"] == 0
