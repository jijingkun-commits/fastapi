"""多智能体预处理节点的技能检索状态测试。"""

import asyncio

from langchain_core.messages import HumanMessage

from app.ai.workflow import multi_agent_graph
from app.services.skill_service import SkillService


def test_preprocess_writes_skill_retrieval_fields(monkeypatch) -> None:  # noqa: ANN001
    """预处理节点应写入技能候选、入选与注入元信息。"""

    events = []
    captured = {}
    monkeypatch.setattr(multi_agent_graph, "get_stream_writer", lambda: events.append)
    monkeypatch.setattr("app.ai.message_utils.validate_messages", lambda messages, fix_reasoning=False: messages)

    class _GuardrailRunner:
        async def validate_input(self, content: str):
            return True, content, None

    monkeypatch.setattr("app.ai.guardrails.guardrail_runner", _GuardrailRunner())
    monkeypatch.setattr(
        SkillService,
        "resolve_runtime_mode",
        classmethod(lambda cls: cls.SKILL_RUNTIME_MODE_HYBRID),
    )

    def _fake_search_debug(  # noqa: ANN001
        cls,
        query: str,
        top_k: int = 5,
        threshold: float = None,
        scope: str = "global",
        auto_only: bool = False,
        thread_id=None,
        trace_id=None,
        user_id=None,
    ):
        captured["user_id"] = user_id
        return {
            "query": query,
            "mode": "hybrid",
            "scope": scope,
            "skill_candidates": [
                {
                    "skill_id": "data-loan",
                    "final_score": 0.92,
                    "vector_score": 0.9,
                    "lexical_score": 0.8,
                    "trigger_hit": 1.0,
                    "selected": True,
                    "drop_reasons": [],
                }
            ],
            "selected_skill_ids": ["data-loan"],
            "context_preview": "### 贷款分析技能 · 概要\n按分行统计贷款余额。\n",
            "skill_injection_meta": {
                "budget_chars": 2400,
                "used_chars": 30,
                "truncated": False,
                "included_skill_ids": ["data-loan"],
                "excluded_skill_ids": [],
                "sections_used": 1,
                "selected_count": 1,
            },
        }

    monkeypatch.setattr(SkillService, "search_skills_debug", classmethod(_fake_search_debug))

    updates = asyncio.run(
        multi_agent_graph._preprocess_multimodal(
            {
                "messages": [HumanMessage(content="按分行统计贷款余额")],
                "enable_thinking": False,
                "user_id": 42,
            }
        )
    )

    assert updates["selected_skill_ids"] == ["data-loan"]
    assert updates["skill_context"]
    assert updates["skill_injection_meta"]["selected_count"] == 1
    assert updates["skill_candidates"][0]["skill_id"] == "data-loan"
    assert captured["user_id"] == 42
    assert any(event.get("type") == "status" for event in events)
