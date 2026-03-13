"""Supervisor 上下文预算与工具输出压缩测试。"""

from types import SimpleNamespace

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool

from app.ai.context_engineering import build_llm_input_context, resolve_context_budget_metadata
from app.services.llm_config_service import LLMConfigService
from app.ai.workflow.multi_agent_graph import (
    SUPERVISOR_CONTEXT_MIN_TOKENS,
    _prepare_messages_for_supervisor_inference,
    _truncate_tool_message_text,
)


def test_resolve_context_budget_metadata_has_floor_without_model_window() -> None:
    """缺少模型窗口时，预算计算仍应有最小值保护。"""
    budget_meta = resolve_context_budget_metadata(
        {},
        scene_key=None,
        configured_max_tokens=128,
        ratio=0.85,
        min_tokens=SUPERVISOR_CONTEXT_MIN_TOKENS,
    )
    assert budget_meta["context_window"] == SUPERVISOR_CONTEXT_MIN_TOKENS
    assert budget_meta["token_budget"] == SUPERVISOR_CONTEXT_MIN_TOKENS


def test_resolve_context_budget_metadata_uses_ratio_without_model_window() -> None:
    """缺少模型窗口时，预算计算仍应按 configured tokens 比例裁剪。"""
    budget_meta = resolve_context_budget_metadata(
        {},
        scene_key=None,
        configured_max_tokens=4000,
        ratio=0.85,
        min_tokens=SUPERVISOR_CONTEXT_MIN_TOKENS,
    )
    assert budget_meta["context_window"] == 4000
    assert budget_meta["token_budget"] == 3400


def test_truncate_tool_message_text_keeps_head_and_tail() -> None:
    """超长工具输出应保留首尾关键信息并添加省略提示。"""
    raw = "A" * 5000
    compacted = _truncate_tool_message_text(
        raw,
        char_limit=1000,
        head_chars=300,
        tail_chars=200,
    )

    assert len(compacted) < len(raw)
    assert compacted.startswith("A" * 300)
    assert compacted.endswith("A" * 200)
    assert "已省略" in compacted


def test_prepare_messages_compacts_only_tool_message() -> None:
    """仅 ToolMessage 参与压缩，普通消息保持原对象引用。"""
    ai_message = AIMessage(content="正常回复", id="ai-msg-1")
    tool_message = ToolMessage(
        content="B" * 5000,
        tool_call_id="tool-1",
        name="knowledge_search",
        id="tool-msg-1",
    )

    prepared = _prepare_messages_for_supervisor_inference([ai_message, tool_message])

    assert prepared[0] is ai_message
    assert prepared[1] is not tool_message
    assert prepared[1].tool_call_id == tool_message.tool_call_id
    assert prepared[1].name == tool_message.name
    assert prepared[1].id == tool_message.id
    assert "已省略" in str(prepared[1].content)


def test_prepare_messages_keeps_short_tool_message() -> None:
    """短工具结果不应被无谓改写。"""
    tool_message = ToolMessage(content="短结果", tool_call_id="tool-2", name="search")
    prepared = _prepare_messages_for_supervisor_inference([tool_message])
    assert prepared[0] is tool_message


def test_resolve_context_budget_metadata_model_aware_budget_prefers_context_window(monkeypatch) -> None:
    """模型感知预算应优先使用场景模型的 context_window。"""

    monkeypatch.setattr(
        LLMConfigService,
        "get_model_config",
        classmethod(lambda cls, model_code: SimpleNamespace(context_window=16000, provider_code="openai")),
    )

    budget_meta = resolve_context_budget_metadata(
        {"model_id": "gpt-5.2"},
        scene_key=None,
        configured_max_tokens=4000,
        ratio=0.85,
        min_tokens=1024,
    )

    assert budget_meta["context_window"] == 16000
    assert budget_meta["token_budget"] == 13600
    assert budget_meta["provider_code"] == "openai"


def test_build_llm_input_context_tracks_prompt_or_tool_schema_budget() -> None:
    """预算账本应独立记录 prompt 与 tool schema 开销。"""

    @tool("knowledge_search")
    def knowledge_search(query: str) -> str:
        """查询知识库。"""
        return query

    state = {
        "system_context": "当前时间: 2026-03-11 18:00:00",
        "skill_catalog_context": "可见技能目录：knowledge-search",
        "loaded_skill_registry": {
            "knowledge-search": {"version": "v1", "truncated": False}
        },
        "skill_catalog_manifest": [
            {
                "skill_id": "knowledge-search",
                "display_name": "Knowledge Search",
                "when_to_use": "查知识库与检索事实",
            }
        ],
    }

    llm_input_messages, ledger, prepared_tokens, pruned_tokens = build_llm_input_context(
        prepared_messages=[HumanMessage(content="帮我查一下知识库")],
        state=state,
        token_budget=4096,
        model_code="gpt-5.2",
        provider_code="openai",
        context_window=16384,
        prompt_text="你是一个擅长调度工具的 supervisor",
        tool_objects=[knowledge_search],
    )

    assert prepared_tokens > 0
    assert pruned_tokens > 0
    assert ledger.prompt_token_estimate > 0
    assert ledger.tool_schema_token_estimate > 0
    assert ledger.system_token_estimate > 0
    assert ledger.skill_catalog_token_estimate > 0
    assert ledger.loaded_skill_token_estimate > 0
    assert ledger.total_token_estimate_before_send >= ledger.message_token_estimate
    assert ledger.selected_tools_for_turn == ["knowledge_search"]
    assert any(
        isinstance(message, SystemMessage) and "以下技能已加载到当前会话，可直接复用其能力摘要" in message.content
        for message in llm_input_messages
    )
