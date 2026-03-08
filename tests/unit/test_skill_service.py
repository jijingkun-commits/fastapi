"""SkillService 单元测试（中文注释）。"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

from app.models.agent_skill import AgentSkillDefinition, AgentSkillVersion, UserSkillBinding
from app.repositories import config_repo
from app.services.skill_service import SkillService


def _build_skill_file(tmp_path: Path, skill_id: str, content: str) -> Path:
    """创建临时 SKILL.md 文件。"""

    skill_dir = tmp_path / skill_id
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(content, encoding="utf-8")
    return skill_file


def test_skill_ingest_parse_with_metadata(tmp_path: Path) -> None:
    """应正确解析 SKILL frontmatter 元数据。"""

    skill_file = _build_skill_file(
        tmp_path,
        "sql-expert",
        """---
name: SQL Expert
description: SQL 检索与优化
scope: data
priority: 10
auto_enabled: true
is_enabled: false
trigger_phrases: [\"贷款余额\", \"分行统计\"]
conflicts_with: [\"copywriter\"]
---

# SQL Expert

这是技能正文。
""",
    )

    parsed = SkillService._parse_skill_file(skill_file)

    assert parsed is not None
    assert parsed["skill_id"] == "sql-expert"
    assert parsed["name"] == "SQL Expert"
    assert parsed["scope"] == "data"
    assert parsed["priority"] == 10
    assert parsed["auto_enabled"] is True
    assert parsed["is_enabled"] is False
    assert parsed["trigger_phrases"] == ["贷款余额", "分行统计"]
    assert parsed["conflicts_with"] == ["copywriter"]
    assert parsed["frontmatter_status"] == "valid"
    assert parsed["warnings"] == []


def test_skill_ingest_missing_frontmatter_uses_defaults(tmp_path: Path) -> None:
    """缺失 frontmatter 时应按默认值回退。"""

    skill_file = _build_skill_file(
        tmp_path,
        "meeting-minutes",
        """# 会议纪要助手

自动整理会议记录。
""",
    )

    parsed = SkillService._parse_skill_file(skill_file)

    assert parsed is not None
    assert parsed["skill_id"] == "meeting-minutes"
    assert parsed["name"] == "Meeting Minutes"
    assert parsed["scope"] == SkillService.DEFAULT_SCOPE
    assert parsed["priority"] == SkillService.DEFAULT_PRIORITY
    assert parsed["auto_enabled"] is True
    assert parsed["is_enabled"] is True
    assert parsed["trigger_phrases"] == []
    assert parsed["conflicts_with"] == []
    assert parsed["frontmatter_status"] == "missing"
    assert parsed["warnings"] == []


def test_skill_ingest_invalid_frontmatter_fallback(tmp_path: Path) -> None:
    """非法 frontmatter 应回退且记录字段级 warning。"""

    skill_file = _build_skill_file(
        tmp_path,
        "risk-review",
        """---
name: 风险审查
scope: unknown
priority: high
auto_enabled: maybe
is_enabled: 2
trigger_phrases: {}
conflicts_with: [risk-review, copywriter]
---

# 风险审查

正文内容。
""",
    )

    parsed = SkillService._parse_skill_file(skill_file)

    assert parsed is not None
    assert parsed["name"] == "风险审查"
    assert parsed["scope"] == SkillService.DEFAULT_SCOPE
    assert parsed["priority"] == SkillService.DEFAULT_PRIORITY
    assert parsed["auto_enabled"] is True
    assert parsed["is_enabled"] is True
    assert parsed["trigger_phrases"] == []
    assert parsed["conflicts_with"] == ["copywriter"]
    assert parsed["frontmatter_status"] == "invalid"
    assert any("field=scope" in warning for warning in parsed["warnings"])
    assert any("field=priority" in warning for warning in parsed["warnings"])
    assert any("field=auto_enabled" in warning for warning in parsed["warnings"])
    assert any("field=is_enabled" in warning for warning in parsed["warnings"])
    assert any("field=trigger_phrases" in warning for warning in parsed["warnings"])
    assert any("field=conflicts_with" in warning for warning in parsed["warnings"])


def test_skill_ingest_yaml_error_uses_legacy_fallback(tmp_path: Path) -> None:
    """YAML 解析失败时应降级到旧解析策略。"""

    skill_file = _build_skill_file(
        tmp_path,
        "legacy-skill",
        """---
name: Legacy Skill
trigger_phrases: ["贷款余额", "分行统计"
---

# Legacy Skill

正文内容。
""",
    )

    parsed = SkillService._parse_skill_file(skill_file)

    assert parsed is not None
    assert parsed["name"] == "Legacy Skill"
    assert parsed["frontmatter_status"] == "invalid"
    assert any("field=frontmatter" in warning for warning in parsed["warnings"])


def test_pick_sections_prefers_query_relevant_content() -> None:
    """应优先选择与查询关键词相关的章节。"""

    content = """# 概览
通用介绍。

# 贷款分析
分行贷款余额趋势统计方法。

# 附录
附加说明。
"""

    sections = SkillService._pick_sections(content, query="按分行统计贷款余额", max_sections=1)

    assert len(sections) == 1
    assert sections[0][0] == "贷款分析"


def test_apply_policy_filters_resolves_conflicts_by_priority() -> None:
    """冲突技能应按优先级保留。"""

    candidates = [
        {
            "skill_id": "safe-review",
            "priority": 10,
            "final_score": 0.62,
            "trigger_hit": 0.0,
            "is_enabled": True,
            "auto_enabled": True,
            "scope": "global",
            "conflicts_with": ["general-review"],
        },
        {
            "skill_id": "general-review",
            "priority": 100,
            "final_score": 0.95,
            "trigger_hit": 0.0,
            "is_enabled": True,
            "auto_enabled": True,
            "scope": "global",
            "conflicts_with": [],
        },
    ]

    selected, dropped = SkillService._apply_policy_filters(
        candidates,
        top_k=2,
        threshold=0.3,
        scope="global",
        auto_only=True,
    )

    assert [item["skill_id"] for item in selected] == ["safe-review"]
    assert dropped[0]["skill_id"] == "general-review"
    assert dropped[0]["reason"] == "conflict_replaced"


def test_format_skills_as_context_with_meta_respects_budget() -> None:
    """上下文注入应返回预算信息并在超限时截断。"""

    class _SkillContextItem:
        def __init__(self, skill_id: str, fragment: str, section_count: int) -> None:
            self.skill_id = skill_id
            self.name = skill_id
            self.description = ""
            self._lazy_context_fragment = fragment
            self._lazy_section_count = section_count

    first = _SkillContextItem("skill-a", "### A\n" + ("a" * 24) + "\n", 1)
    second = _SkillContextItem("skill-b", "### B\n" + ("b" * 30) + "\n", 1)

    context, meta = SkillService.format_skills_as_context_with_meta(
        [first, second],
        max_length=len(first._lazy_context_fragment) + 4,
    )

    assert "skill-a" in meta["included_skill_ids"]
    assert meta["excluded_skill_ids"] == ["skill-b"]
    assert meta["truncated"] is True
    assert meta["sections_used"] == 1
    assert "### A" in context
    assert "### B" not in context


def test_search_skills_debug_exposes_candidates_and_injection_meta(monkeypatch) -> None:  # noqa: ANN001
    """调试接口应返回候选明细、入选列表与注入元信息。"""

    class _DebugSkill:
        def __init__(self) -> None:
            self.skill_id = "data-loan"
            self.name = "贷款分析技能"
            self.description = "按分行统计贷款余额"
            self._retrieval_score = 0.91
            self._vector_score = 0.88
            self._lexical_score = 0.76
            self._trigger_hit = 1.0
            self._lazy_context_fragment = "### 贷款分析技能 · 概要\n按分行统计贷款余额。\n"
            self._lazy_section_count = 1

    debug_skill = _DebugSkill()

    def _fake_search(  # noqa: ANN001
        cls,
        query: str,
        top_k: int,
        threshold,
        scope: str,
        auto_only: bool,
        thread_id,
        trace_id,
    ):
        return [debug_skill], {
            "query": query,
            "mode": "hybrid",
            "scope": scope,
            "threshold": 0.4,
            "effective_threshold": 0.35,
            "context_budget": 160,
            "merged_candidates": [
                {
                    "skill_id": "data-loan",
                    "vector_score": 0.88,
                    "lexical_score": 0.76,
                    "trigger_hit": 1.0,
                    "final_score": 0.91,
                    "priority": 10,
                    "scope": "data",
                    "is_enabled": True,
                    "auto_enabled": True,
                },
                {
                    "skill_id": "todo-skill",
                    "vector_score": 0.21,
                    "lexical_score": 0.15,
                    "trigger_hit": 0.0,
                    "final_score": 0.19,
                    "priority": 200,
                    "scope": "todo",
                    "is_enabled": False,
                    "auto_enabled": True,
                },
            ],
            "dropped": [{"skill_id": "todo-skill", "reason": "disabled"}],
        }

    monkeypatch.setattr(SkillService, "_search_skills_internal", classmethod(_fake_search))

    debug = SkillService.search_skills_debug(
        query="按分行统计贷款余额",
        top_k=2,
        threshold=0.4,
        scope="data",
        auto_only=True,
    )

    assert debug["selected_skill_ids"] == ["data-loan"]
    assert debug["skill_injection_meta"]["selected_count"] == 1
    assert debug["skill_injection_meta"]["mode"] == "hybrid"
    assert debug["skill_injection_meta"]["scope"] == "data"
    assert debug["skill_injection_meta"]["used_chars"] > 0

    candidates = {item["skill_id"]: item for item in debug["skill_candidates"]}
    assert candidates["data-loan"]["selected"] is True
    assert candidates["todo-skill"]["selected"] is False
    assert candidates["todo-skill"]["drop_reasons"][0]["reason"] == "disabled"


def test_build_retrieval_log_should_include_trace_fields() -> None:
    """结构化检索日志应包含 trace/thread/query_hash 与入选信息。"""

    retrieval_log = SkillService._build_retrieval_log(
        query="按分行统计贷款余额",
        thread_id="thread-skill-001",
        trace_id="trace-skill-001",
        user_id=101,
        retrieval_mode="hybrid",
        runtime_source_mode="compat",
        strict_user_mode=False,
        scope="data",
        top_k=2,
        base_threshold=0.4,
        effective_threshold=0.35,
        vector_candidates=[{"skill_id": "sql-expert"}],
        lexical_candidates=[{"skill_id": "data-insight"}],
        merged_candidates=[{"skill_id": "sql-expert"}, {"skill_id": "data-insight"}],
        selected_candidates=[{"skill_id": "sql-expert"}],
        dropped_candidates=[{"skill_id": "data-insight", "reason": "below_threshold"}],
    )

    assert retrieval_log["thread_id"] == "thread-skill-001"
    assert retrieval_log["trace_id"] == "trace-skill-001"
    assert retrieval_log["user_id"] == 101
    assert len(retrieval_log["query_hash"]) == 16
    assert retrieval_log["selected_skill_ids"] == ["sql-expert"]
    assert retrieval_log["candidate_count"] == 2


def test_search_skills_debug_should_backfill_retrieval_log(monkeypatch) -> None:  # noqa: ANN001
    """内部调试信息缺失 retrieval_log 时应自动补齐。"""

    class _DebugSkill:
        def __init__(self) -> None:
            self.skill_id = "data-loan"
            self.name = "贷款分析技能"
            self.description = "按分行统计贷款余额"
            self._retrieval_score = 0.91
            self._vector_score = 0.88
            self._lexical_score = 0.76
            self._trigger_hit = 1.0
            self._lazy_context_fragment = "### 贷款分析技能 · 概要\n按分行统计贷款余额。\n"
            self._lazy_section_count = 1

    debug_skill = _DebugSkill()

    def _fake_search(  # noqa: ANN001
        cls,
        query: str,
        top_k: int,
        threshold,
        scope: str,
        auto_only: bool,
        thread_id,
        trace_id,
    ):
        _ = cls, threshold, auto_only
        return [debug_skill], {
            "query": query,
            "mode": "hybrid",
            "scope": scope,
            "threshold": 0.4,
            "effective_threshold": 0.35,
            "context_budget": 160,
            "merged_candidates": [
                {
                    "skill_id": "data-loan",
                    "vector_score": 0.88,
                    "lexical_score": 0.76,
                    "trigger_hit": 1.0,
                    "final_score": 0.91,
                    "priority": 10,
                    "scope": "data",
                    "is_enabled": True,
                    "auto_enabled": True,
                }
            ],
            "dropped": [],
            "thread_id_from_internal": thread_id,
            "trace_id_from_internal": trace_id,
        }

    monkeypatch.setattr(SkillService, "_search_skills_internal", classmethod(_fake_search))

    debug = SkillService.search_skills_debug(
        query="按分行统计贷款余额",
        top_k=2,
        threshold=0.4,
        scope="data",
        auto_only=True,
        thread_id="thread-skill-002",
        trace_id="trace-skill-002",
    )

    retrieval_log = debug["retrieval_log"]
    assert retrieval_log["thread_id"] == "thread-skill-002"
    assert retrieval_log["trace_id"] == "trace-skill-002"
    assert len(retrieval_log["query_hash"]) == 16
    assert retrieval_log["selected_skill_ids"] == ["data-loan"]


class _RuntimeExecuteSession:
    """用于检索路径测试的最小 Session。"""

    def __init__(self, rows: Optional[List[Any]] = None, error: Exception | None = None):
        self._rows = rows or []
        self._error = error

    def execute(self, statement, params=None):  # noqa: ANN001
        _ = statement, params
        if self._error is not None:
            raise self._error
        return list(self._rows)


def test_skill_runtime_source_sql_should_not_fallback_to_legacy_table_when_flag_disabled(monkeypatch) -> None:  # noqa: ANN001
    """即使旧版本开关关闭，runtime 仍必须固定走 definition/version 视图。"""

    monkeypatch.setattr(SkillService, "_is_versioning_runtime_enabled", classmethod(lambda cls: False))
    monkeypatch.setattr(SkillService, "_is_user_skill_binding_enabled", classmethod(lambda cls: False))

    sql, params = SkillService._build_runtime_source_sql(user_id=101)

    assert "t_agent_skill_versions" in sql
    assert "FROM t_agent_skills" not in sql
    assert params["binding_enabled"] is False
    assert params["binding_user_id"] == 101


def test_skill_retrieval_vector_should_return_empty_without_legacy_fallback(monkeypatch) -> None:  # noqa: ANN001
    """runtime 视图命中空结果时，应直接返回空，不得回退旧表。"""

    db = _RuntimeExecuteSession(rows=[])

    monkeypatch.setattr(
        SkillService,
        "_build_runtime_source_sql",
        classmethod(lambda cls, user_id: ("SELECT 1", {"binding_user_id": user_id or -1})),
    )

    candidates = SkillService._fetch_vector_candidates(
        db=db,
        query_embedding=[0.01, 0.02],
        limit=3,
        user_id=101,
    )

    assert candidates == []



def test_skill_retrieval_lexical_should_raise_without_legacy_fallback(monkeypatch) -> None:  # noqa: ANN001
    """runtime SQL 异常时应直接抛错，不得回退旧表。"""

    db = _RuntimeExecuteSession(error=RuntimeError("runtime sql failed"))

    monkeypatch.setattr(
        SkillService,
        "_build_runtime_source_sql",
        classmethod(lambda cls, user_id: ("SELECT 1", {"binding_user_id": user_id or -1})),
    )

    with pytest.raises(RuntimeError, match="runtime sql failed"):
        SkillService._fetch_lexical_candidates(
            db=db,
            query="贷款余额",
            limit=3,
            user_id=101,
        )


def test_skill_retrieval_vector_should_raise_without_legacy_fallback(monkeypatch) -> None:  # noqa: ANN001
    """向量 runtime SQL 异常时应直接抛错，不得回退旧表。"""

    db = _RuntimeExecuteSession(error=RuntimeError("runtime vector sql failed"))

    monkeypatch.setattr(
        SkillService,
        "_build_runtime_source_sql",
        classmethod(lambda cls, user_id: ("SELECT 1", {"binding_user_id": user_id or -1})),
    )

    with pytest.raises(RuntimeError, match="runtime vector sql failed"):
        SkillService._fetch_vector_candidates(
            db=db,
            query_embedding=[0.01, 0.02],
            limit=3,
            user_id=101,
        )



class _FakeSession:
    """模拟最小化 Session 行为。"""

    def __init__(self):
        self.commit_count = 0
        self.rollback_count = 0

    def commit(self) -> None:
        self.commit_count += 1

    def rollback(self) -> None:
        self.rollback_count += 1


def test_skill_ingest_import_should_fail_fast_when_local_file_path_used(tmp_path: Path) -> None:
    """本地 SKILL.md 导入入口应显式退役。"""

    skill_file = _build_skill_file(
        tmp_path,
        "copywriter",
        """---
name: 文案润色专家
description: 优化文案表达
---

# 文案润色专家
""",
    )

    with pytest.raises(RuntimeError, match="本地 SKILL.md / skills 目录导入链已退役"):
        SkillService.import_skill(skill_file, object(), force=False)


def test_skill_ingest_import_all_should_fail_fast_when_local_directory_used(tmp_path: Path) -> None:
    """本地目录批量导入入口应显式退役。"""

    with pytest.raises(RuntimeError, match="本地 SKILL.md / skills 目录导入链已退役"):
        SkillService.import_all_skills(tmp_path, force=True)


def test_skill_ingest_sync_changed_skills_should_fail_fast(tmp_path: Path) -> None:
    """本地目录增量同步入口应显式退役。"""

    with pytest.raises(RuntimeError, match="本地 SKILL.md / skills 目录导入链已退役"):
        SkillService.sync_changed_skills(tmp_path)


class _SequentialResult:
    """按调用顺序返回 execute 结果。"""

    def __init__(self, scalar=None, scalars: Optional[List[Any]] = None):  # noqa: ANN001
        self._scalar = scalar
        self._scalars = scalars or []

    def scalar_one_or_none(self):  # noqa: ANN001
        return self._scalar

    def scalars(self):  # noqa: ANN001
        return self

    def all(self) -> List[Any]:
        return list(self._scalars)


class _SequentialSession:
    """顺序消费 execute 结果的轻量 Session。"""

    def __init__(self, results: List[_SequentialResult]):
        self._results = list(results)
        self.added: List[Any] = []
        self.commit_count = 0

    def execute(self, statement):  # noqa: ANN001
        _ = statement
        if not self._results:
            raise AssertionError("execute 调用次数超出预期")
        return self._results.pop(0)

    def add(self, item: Any) -> None:
        self.added.append(item)

    def commit(self) -> None:
        self.commit_count += 1


def test_skill_version_publish_should_switch_active_version(monkeypatch) -> None:  # noqa: ANN001
    """发布新版本时应将旧 published 版本标记为 rollbacked。"""

    version_v1 = AgentSkillVersion(
        definition_id=1,
        skill_id="loan-advice",
        version="v1",
        status=SkillService.VERSION_STATUS_PUBLISHED,
        name="贷款分析",
        content="v1",
    )
    version_v2 = AgentSkillVersion(
        definition_id=1,
        skill_id="loan-advice",
        version="v2",
        status=SkillService.VERSION_STATUS_DRAFT,
        name="贷款分析",
        content="v2",
    )

    session = _SequentialSession(results=[_SequentialResult(scalars=[version_v1, version_v2])])

    monkeypatch.setattr(SkillService, "_is_skill_versioning_enabled", classmethod(lambda cls: True))

    payload = SkillService.publish_skill_version(session, "loan-advice", "v2")

    assert payload["published_version"] == "v2"
    assert payload["previous_version"] == "v1"
    assert version_v1.status == SkillService.VERSION_STATUS_ROLLBACKED
    assert version_v2.status == SkillService.VERSION_STATUS_PUBLISHED
    assert session.commit_count == 1


def test_skill_version_import_all_should_fail_fast_when_local_source_used(tmp_path: Path) -> None:
    """批量导入旧入口已退役，不应再触发模板兜底流程。"""

    _build_skill_file(
        tmp_path,
        "sql-expert",
        """---
name: SQL Expert
description: SQL 检索
---

# SQL Expert
""",
    )

    with pytest.raises(RuntimeError, match="本地 SKILL.md / skills 目录导入链已退役"):
        SkillService.import_all_skills(tmp_path, force=True)


def test_skill_version_template_should_not_fallback_to_legacy_records() -> None:
    """无发布版本时模板应返回空技能列表，不得回退旧表。"""

    session = _SequentialSession(results=[_SequentialResult(scalars=[])])

    payload = SkillService._build_user_bootstrap_template(session)

    assert payload == {"default_version": SkillService.DEFAULT_VERSION, "skills": []}


def test_skill_version_list_should_return_empty_when_no_version_records() -> None:
    """无版本记录时列表应为空，不得再 bootstrap 旧表。"""

    session = _SequentialSession(results=[_SequentialResult(scalars=[])])

    payload = SkillService.list_skill_versions(session, "loan-advice")

    assert payload == []


def test_skill_version_template_config_should_upsert_when_missing(monkeypatch) -> None:  # noqa: ANN001
    """模板配置缺失时应写入默认模板 JSON。"""

    payload = {
        "default_version": "v1",
        "skills": [
            {
                "skill_id": "sql-expert",
                "version": "v2",
                "enabled": True,
                "priority_override": 100,
            }
        ],
    }
    upsert_calls: List[Dict[str, Any]] = []

    monkeypatch.setattr(config_repo, "get_config_by_key", lambda db, key: None)
    monkeypatch.setattr(
        SkillService,
        "_build_user_bootstrap_template",
        classmethod(lambda cls, db: payload),
    )

    def _fake_upsert(db, key, value, value_type="string", category=None, description=None):  # noqa: ANN001
        upsert_calls.append(
            {
                "key": key,
                "value": value,
                "value_type": value_type,
                "category": category,
                "description": description,
            }
        )
        return object()

    monkeypatch.setattr(config_repo, "upsert_config", _fake_upsert)
    db = type("_CommitDB", (), {"commit": lambda self: None})()

    updated = SkillService._ensure_user_bootstrap_template_config(db=db)

    assert updated is True
    assert len(upsert_calls) == 1
    assert upsert_calls[0]["key"] == SkillService.USER_BOOTSTRAP_TEMPLATE_KEY
    assert upsert_calls[0]["value_type"] == "json"
    assert json.loads(upsert_calls[0]["value"]) == payload


def test_skill_binding_bind_user_skill_should_create_binding(monkeypatch) -> None:  # noqa: ANN001
    """用户绑定应写入 version 与状态，避免跨用户污染。"""

    version_v2 = AgentSkillVersion(
        definition_id=1,
        skill_id="loan-advice",
        version="v2",
        status=SkillService.VERSION_STATUS_PUBLISHED,
        name="贷款分析",
        content="v2",
    )

    session = _SequentialSession(
        results=[
            _SequentialResult(scalar=version_v2),
            _SequentialResult(scalar=None),
        ]
    )

    monkeypatch.setattr(SkillService, "_is_skill_versioning_enabled", classmethod(lambda cls: True))
    monkeypatch.setattr(SkillService, "_is_user_skill_binding_enabled", classmethod(lambda cls: True))

    payload = SkillService.bind_user_skill(
        db=session,
        user_id=2001,
        skill_id="loan-advice",
        version="v2",
        is_enabled=True,
        priority_override=12,
    )

    assert payload["user_id"] == 2001
    assert payload["version"] == "v2"
    assert payload["binding_status"] == SkillService.BINDING_STATUS_ENABLED
    assert session.commit_count == 1
    assert len(session.added) == 1
    created_binding = session.added[0]
    assert created_binding.user_id == 2001
    assert created_binding.skill_id == "loan-advice"


def test_skill_binding_rollback_user_binding_should_disable_override(monkeypatch) -> None:  # noqa: ANN001
    """绑定回滚后应停用用户覆盖并回退平台版本。"""

    binding = UserSkillBinding(
        user_id=2002,
        skill_id="loan-advice",
        version="v2",
        binding_status=SkillService.BINDING_STATUS_ENABLED,
        is_enabled=True,
    )
    session = _SequentialSession(results=[_SequentialResult(scalar=binding)])

    monkeypatch.setattr(SkillService, "_is_user_skill_binding_enabled", classmethod(lambda cls: True))

    payload = SkillService.rollback_user_skill_binding(session, user_id=2002, skill_id="loan-advice")

    assert payload["binding_status"] == SkillService.BINDING_STATUS_ROLLBACKED
    assert payload["rolled_back_version"] == "v2"
    assert binding.version is None
    assert binding.is_enabled is False
    assert session.commit_count == 1


def test_admin_skill_list_should_prefer_enabled_binding_over_published(monkeypatch) -> None:  # noqa: ANN001
    """管理面列表应优先展示用户启用绑定版本。"""

    definition = AgentSkillDefinition(
        id=1,
        skill_id="loan-advice",
        name="贷款分析",
        description="定义描述",
        scope="data",
        is_enabled=True,
        catalog_order=10,
    )
    version_v1 = AgentSkillVersion(
        id=11,
        definition_id=1,
        skill_id="loan-advice",
        version="v1",
        status=SkillService.VERSION_STATUS_PUBLISHED,
        name="贷款分析 v1",
        description="发布版本",
        content="v1",
        priority=10,
    )
    version_v2 = AgentSkillVersion(
        id=12,
        definition_id=1,
        skill_id="loan-advice",
        version="v2",
        status=SkillService.VERSION_STATUS_DRAFT,
        name="贷款分析 v2",
        description="绑定版本",
        content="v2",
        priority=5,
    )
    binding = UserSkillBinding(
        user_id=3101,
        skill_id="loan-advice",
        version="v2",
        binding_status=SkillService.BINDING_STATUS_ENABLED,
        is_enabled=True,
    )
    session = _SequentialSession(
        results=[
            _SequentialResult(scalars=[definition]),
            _SequentialResult(scalars=[version_v1, version_v2]),
            _SequentialResult(scalars=[binding]),
        ]
    )

    monkeypatch.setattr(SkillService, "_is_user_skill_binding_enabled", classmethod(lambda cls: True))

    payload = SkillService.list_admin_skills(session, user_id=3101)

    assert len(payload) == 1
    assert payload[0]["published_version"] == "v1"
    assert payload[0]["bound_version"] == "v2"
    assert payload[0]["effective_version"] == "v2"
    assert payload[0]["name"] == "贷款分析 v2"


def test_admin_skill_list_should_fallback_to_latest_version_without_published() -> None:
    """无 published 版本时管理面应回退 latest version，而不是旧表。"""

    definition = AgentSkillDefinition(
        id=2,
        skill_id="risk-check",
        name="风控检查",
        description="定义描述",
        scope="admin",
        is_enabled=False,
        catalog_order=20,
    )
    version_v3 = AgentSkillVersion(
        id=21,
        definition_id=2,
        skill_id="risk-check",
        version="v3",
        status=SkillService.VERSION_STATUS_DRAFT,
        name="风控检查 v3",
        description="草稿版本",
        content="v3-content",
        file_hash="hash-v3",
        priority=30,
    )
    session = _SequentialSession(
        results=[
            _SequentialResult(scalars=[definition]),
            _SequentialResult(scalars=[version_v3]),
        ]
    )

    payload = SkillService.list_admin_skills(session)

    assert len(payload) == 1
    assert payload[0]["effective_version"] == "v3"
    assert payload[0]["published_version"] is None
    assert payload[0]["content_preview"] == "v3-content"
    assert payload[0]["is_enabled"] is False


def test_admin_skill_regenerate_should_update_published_version_embedding(monkeypatch) -> None:  # noqa: ANN001
    """批量重建向量时应优先写 published 版本记录。"""

    definition = AgentSkillDefinition(
        id=3,
        skill_id="sql-expert",
        name="SQL Expert",
        description="SQL 诊断",
        scope="data",
        is_enabled=True,
        catalog_order=30,
    )
    version_v1 = AgentSkillVersion(
        id=31,
        definition_id=3,
        skill_id="sql-expert",
        version="v1",
        status=SkillService.VERSION_STATUS_PUBLISHED,
        name="SQL Expert v1",
        description="发布描述",
        content="v1",
    )
    version_v2 = AgentSkillVersion(
        id=32,
        definition_id=3,
        skill_id="sql-expert",
        version="v2",
        status=SkillService.VERSION_STATUS_DRAFT,
        name="SQL Expert v2",
        description="草稿描述",
        content="v2",
    )
    session = _SequentialSession(
        results=[
            _SequentialResult(scalars=[definition]),
            _SequentialResult(scalars=[version_v1, version_v2]),
        ]
    )

    monkeypatch.setattr("app.services.skill_service.get_embedding", lambda text: [0.1, 0.2, 0.3])

    payload = SkillService.regenerate_admin_skill_embeddings(session, skill_ids=["sql-expert"])

    assert payload["success_count"] == 1
    assert session.commit_count == 1
    assert version_v1.embedding == [0.1, 0.2, 0.3]
    assert version_v2.embedding is None


def test_skill_get_by_id_should_read_from_versioned_truth_source(monkeypatch) -> None:  # noqa: ANN001
    """get_by_id 应从 versioned 聚合读模型构造技能，而不是查询旧表。"""

    session = object()

    class _ContextManager:
        def __enter__(self):  # noqa: ANN001
            return session

        def __exit__(self, exc_type, exc, tb) -> bool:  # noqa: ANN001
            return False

    monkeypatch.setattr("app.services.skill_service.get_db_context", lambda: _ContextManager())
    monkeypatch.setattr(
        SkillService,
        "get_admin_skill",
        classmethod(
            lambda cls, db, skill_id: {
                "id": 301,
                "skill_id": skill_id,
                "name": "Loan Advice",
                "description": "贷款分析",
                "content": "完整版技能",
                "file_hash": "hash-301",
                "has_embedding": True,
                "embedding_dim": 3,
                "is_enabled": True,
                "auto_enabled": False,
                "priority": 12,
                "scope": "data",
                "trigger_phrases": ["贷款余额"],
                "conflicts_with": ["risk-check"],
                "effective_version": "v2",
                "binding_status": "enabled",
            }
        ),
    )

    payload = SkillService.get_by_id("loan-advice")

    assert payload is not None
    assert payload.skill_id == "loan-advice"
    assert payload.content == "完整版技能"
    assert payload.priority == 12
    assert payload.auto_enabled is False
    assert payload._effective_version == "v2"
    assert payload._binding_status == "enabled"
    assert payload.embedding == [0.0, 0.0, 0.0]
