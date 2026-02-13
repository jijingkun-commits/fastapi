"""SkillService 单元测试（中文注释）。"""

from pathlib import Path
from typing import Any, Dict, List

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
        retrieval_mode="hybrid",
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



class _FakeSkill:
    """测试导入流程用的假 Skill ORM 对象。"""

    def __init__(self, skill_id: str, file_hash: str):
        self.skill_id = skill_id
        self.file_hash = file_hash
        self.name = ""
        self.description = ""
        self.content = ""
        self.embedding = None
        self.scope = SkillService.DEFAULT_SCOPE
        self.priority = SkillService.DEFAULT_PRIORITY
        self.auto_enabled = True
        self.is_enabled = True
        self.trigger_phrases: List[str] = []
        self.conflicts_with: List[str] = []


class _FakeResult:
    """模拟 SQLAlchemy execute 结果。"""

    def __init__(self, item: Any):
        self._item = item

    def scalar_one_or_none(self) -> Any:
        return self._item


class _FakeSession:
    """模拟最小化 Session 行为。"""

    def __init__(self, records: Dict[str, _FakeSkill]):
        self.records = records
        self.added: List[_FakeSkill] = []
        self.commit_count = 0
        self.rollback_count = 0

    def execute(self, statement) -> _FakeResult:  # noqa: ANN001
        params = statement.compile().params
        skill_id = next(iter(params.values()), None)
        if skill_id is None:
            return _FakeResult(None)
        return _FakeResult(self.records.get(str(skill_id)))

    def add(self, skill: _FakeSkill) -> None:
        self.records[skill.skill_id] = skill
        self.added.append(skill)

    def commit(self) -> None:
        self.commit_count += 1

    def rollback(self) -> None:
        self.rollback_count += 1


def test_skill_ingest_import_is_idempotent_for_unchanged_file(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    """同文件哈希重复导入应跳过写入。"""

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

    parsed = SkillService._parse_skill_file(skill_file)
    assert parsed is not None
    file_hash = SkillService._compute_file_hash(parsed["content"])

    session = _FakeSession(records={"copywriter": _FakeSkill("copywriter", file_hash)})
    monkeypatch.setattr("app.services.skill_service.get_embedding", lambda text: [0.1, 0.2])

    updated = SkillService.import_skill(skill_file, session, force=False)

    assert updated is False
    assert session.commit_count == 0


def test_skill_ingest_import_updates_existing_record(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    """文件变化时应更新已存在技能。"""

    skill_file = _build_skill_file(
        tmp_path,
        "copywriter",
        """---
name: 文案润色专家
description: 新描述
priority: 5
---

# 文案润色专家
""",
    )

    existing = _FakeSkill("copywriter", "old-hash")
    session = _FakeSession(records={"copywriter": existing})
    monkeypatch.setattr("app.services.skill_service.get_embedding", lambda text: [0.9])

    updated = SkillService.import_skill(skill_file, session, force=False)

    assert updated is True
    assert session.commit_count == 1
    assert existing.description == "新描述"
    assert existing.priority == 5
    assert existing.embedding == [0.9]


def test_skill_ingest_import_all_continue_on_error(tmp_path: Path, monkeypatch, caplog) -> None:  # noqa: ANN001
    """批量导入遇到单文件异常时应继续处理并记录错误。"""

    _build_skill_file(
        tmp_path,
        "skill-ok-a",
        """---
name: Skill A
description: A
---

# Skill A
""",
    )
    _build_skill_file(
        tmp_path,
        "skill-fail",
        """---
name: Skill B
description: B
---

# Skill B
""",
    )
    _build_skill_file(
        tmp_path,
        "skill-ok-c",
        """---
name: Skill C
description: C
---

# Skill C
""",
    )

    session = _FakeSession(records={})

    class _ContextManager:
        def __enter__(self) -> _FakeSession:
            return session

        def __exit__(self, exc_type, exc, tb) -> bool:  # noqa: ANN001
            return False

    def _fake_import_skill(skill_path: Path, db: _FakeSession, force: bool) -> bool:  # noqa: ANN001
        if skill_path.parent.name == "skill-fail":
            raise RuntimeError("ingest failed")
        db.commit()
        return True

    monkeypatch.setattr("app.services.skill_service.get_db_context", lambda: _ContextManager())
    monkeypatch.setattr(SkillService, "import_skill", classmethod(lambda cls, p, d, f: _fake_import_skill(p, d, f)))

    with caplog.at_level("ERROR"):
        updated = SkillService.import_all_skills(tmp_path)

    assert updated == 2
    assert session.rollback_count == 1
    assert any("导入技能失败 skill_id=skill-fail" in record.message for record in caplog.records)


def test_skill_ingest_import_all_returns_zero_when_missing_dir(tmp_path: Path) -> None:
    """目录不存在时返回 0。"""

    missing_dir = tmp_path / "missing"
    assert SkillService.import_all_skills(missing_dir) == 0
