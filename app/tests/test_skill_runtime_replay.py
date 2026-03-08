"""Skill runtime canonical / replay 专项测试。"""

import asyncio

from langchain_core.messages import AIMessage, HumanMessage

from app.ai.workflow import multi_agent_graph
from app.services.skill_service import SkillService


def _patch_preprocess_basics(monkeypatch):
    events = []
    monkeypatch.setattr(multi_agent_graph, "get_stream_writer", lambda: events.append)
    monkeypatch.setattr("app.ai.message_utils.validate_messages", lambda messages, fix_reasoning=False: messages)

    class _GuardrailRunner:
        async def validate_input(self, content: str):
            return True, content, None

    monkeypatch.setattr("app.ai.guardrails.guardrail_runner", _GuardrailRunner())
    monkeypatch.setattr(
        SkillService,
        "resolve_runtime_mode",
        classmethod(lambda cls: cls.SKILL_RUNTIME_MODE_PROGRESSIVE),
    )
    monkeypatch.setattr(
        SkillService,
        "build_skill_catalog_manifest",
        classmethod(
            lambda cls, user_id=None: {
                "manifest": [],
                "catalog_version": "cat-000",
                "visible_skill_count": 0,
                "catalog_build_source": SkillService.SKILL_CATALOG_SOURCE,
            }
        ),
    )
    monkeypatch.setattr(
        SkillService,
        "format_skill_catalog_as_context_with_meta",
        classmethod(
            lambda cls, manifest, max_length=2400: (
                "",
                {
                    "budget_chars": 2400,
                    "used_chars": 0,
                    "truncated": False,
                    "included_skill_ids": [],
                    "excluded_skill_ids": [],
                    "visible_skill_count": len(manifest),
                },
            )
        ),
    )
    return events


def test_preprocess_rehydrates_loaded_skill_state_from_ai_message(monkeypatch) -> None:
    """回放时应优先读取历史 AIMessage.skill_runtime 恢复 loaded_skill_registry。"""

    _patch_preprocess_basics(monkeypatch)
    monkeypatch.setattr(
        SkillService,
        "build_loaded_skill_context_from_registry",
        classmethod(
            lambda cls, registry: {
                "loaded_skill_context": "以下技能正文已加载到当前会话，可直接复用：\n\n### SQL Author | skill_id=sql.query.author | version=v2026.03.07\n# SQL Author\n正文",
                "loaded_skills": [{"skill_id": "sql.query.author", "version": "v2026.03.07", "truncated": False}],
                "missing_skills": [],
            }
        ),
    )

    previous_ai = AIMessage(
        content="上一轮答复",
        additional_kwargs={
            "skill_runtime": {
                "runtime_mode": "progressive_loader",
                "catalog_version": "cat-001",
                "visible_skill_count": 1,
                "loaded_skills": [
                    {"skill_id": "sql.query.author", "version": "v2026.03.07", "truncated": False}
                ],
                "replay_source": "live",
            }
        },
    )

    updates = asyncio.run(
        multi_agent_graph._preprocess_multimodal(
            {
                "messages": [previous_ai, HumanMessage(content="继续沿用上轮技能")],
                "enable_thinking": False,
                "user_id": 7,
            }
        )
    )

    assert updates["loaded_skill_registry"]["sql.query.author"]["version"] == "v2026.03.07"
    assert updates["loaded_skill_context"].startswith("以下技能正文已加载到当前会话")


def test_create_ai_message_with_skill_runtime_marks_rehydrated(monkeypatch) -> None:
    """当当前轮未再次触发 load_skills 时，AI 输出应标记 replay_source=rehydrated。"""

    monkeypatch.setattr(
        SkillService,
        "resolve_runtime_mode",
        classmethod(lambda cls: cls.SKILL_RUNTIME_MODE_PROGRESSIVE),
    )

    message = multi_agent_graph._create_ai_message_with_skill_runtime(
        "已完成",
        {
            "messages": [HumanMessage(content="继续")],
            "loaded_skill_registry": {
                "sql.query.author": {
                    "skill_id": "sql.query.author",
                    "version": "v2026.03.07",
                    "truncated": False,
                }
            },
            "loaded_skill_context": "以下技能正文已加载到当前会话，可直接复用：...",
            "skill_catalog_manifest": [{"skill_id": "sql.query.author", "effective_version": "v2026.03.07"}],
            "catalog_version": "cat-001",
            "visible_skill_count": 1,
        },
    )

    skill_runtime = message.additional_kwargs["skill_runtime"]
    assert skill_runtime["loaded_skills"][0]["skill_id"] == "sql.query.author"
    assert skill_runtime["replay_source"] == "rehydrated"
