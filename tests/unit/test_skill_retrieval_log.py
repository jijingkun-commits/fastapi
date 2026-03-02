"""Skill 检索日志结构测试。"""

from __future__ import annotations

from app.services.skill_service import SkillService


def test_build_retrieval_log_should_include_runtime_source_mode_fields() -> None:
    """结构化日志需包含 runtime_source_mode 与 strict_user 标记。"""

    payload = SkillService._build_retrieval_log(
        query="贷款余额",
        thread_id="thread-1",
        trace_id="trace-1",
        user_id=2001,
        retrieval_mode="hybrid",
        runtime_source_mode=SkillService.RUNTIME_SOURCE_MODE_STRICT_USER,
        strict_user_mode=True,
        scope="data",
        top_k=2,
        base_threshold=0.4,
        effective_threshold=0.35,
        vector_candidates=[{"skill_id": "loan-advice"}],
        lexical_candidates=[{"skill_id": "risk-check"}],
        merged_candidates=[{"skill_id": "loan-advice"}, {"skill_id": "risk-check"}],
        selected_candidates=[{"skill_id": "loan-advice"}],
        dropped_candidates=[{"skill_id": "risk-check", "reason": "below_threshold"}],
    )

    assert payload["runtime_source_mode"] == SkillService.RUNTIME_SOURCE_MODE_STRICT_USER
    assert payload["strict_user_mode"] is True
    assert payload["selected_skill_ids"] == ["loan-advice"]


def test_search_skills_empty_query_should_emit_runtime_source_mode(monkeypatch) -> None:  # noqa: ANN001
    """空查询也应输出 runtime_source_mode 观测字段。"""

    monkeypatch.setattr(
        SkillService,
        "_get_runtime_source_mode",
        classmethod(lambda cls: SkillService.RUNTIME_SOURCE_MODE_STRICT_USER),
    )

    skills, debug = SkillService._search_skills_internal(
        query="   ",
        top_k=2,
        threshold=None,
        scope="global",
        auto_only=True,
        user_id=1001,
    )

    assert skills == []
    retrieval_log = debug["retrieval_log"]
    assert retrieval_log["runtime_source_mode"] == SkillService.RUNTIME_SOURCE_MODE_STRICT_USER
    assert retrieval_log["strict_user_mode"] is True
    assert retrieval_log["reason"] == "empty_query"
