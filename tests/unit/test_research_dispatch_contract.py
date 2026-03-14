import json

from langchain_core.messages import HumanMessage, ToolMessage

from app.ai.workflow import multi_agent_graph
from app.ai.tools import chatTools
from app.ai.tools import ragflow_tool


def test_web_research_should_return_stable_insufficiency_when_search_unavailable(monkeypatch):
    """search_tool 不可用时，web_research 应返回稳定 insufficiency，而不是异常冒泡。"""
    monkeypatch.setattr(chatTools, "search_tool", None, raising=False)

    payload = json.loads(chatTools.web_research.func(query="整理今天的正面新闻"))

    assert payload["contract_version"] == "v2"
    assert payload["research_mode"] == "web"
    assert payload["summary_markdown"] == ""
    assert payload["media_refs"] == []
    assert payload["insufficiency"]
    assert payload["source_count"] == 0


def test_get_supervisor_tool_entries_should_keep_atomic_tools_and_unified_research_entry(monkeypatch):
    """Supervisor 工具集合应保留 atomic tool，并收口为统一 research_subagent 入口。"""
    from app.services.skill_service import SkillService

    def _knowledge_search():
        return "ok"

    class _SearchTool:
        name = "search_tool"

        def invoke(self, _payload):
            return []

    _knowledge_search.__name__ = "knowledge_search"

    monkeypatch.setattr(multi_agent_graph, "_get_common_tool_entries", lambda: [], raising=False)
    monkeypatch.setattr(SkillService, "resolve_runtime_mode", classmethod(lambda cls: "legacy"))
    monkeypatch.setattr(ragflow_tool, "is_ragflow_configured", lambda: True, raising=False)
    monkeypatch.setattr(ragflow_tool, "knowledge_search", _knowledge_search, raising=False)
    monkeypatch.setattr(chatTools, "search_tool", _SearchTool(), raising=False)

    entries = multi_agent_graph._get_supervisor_tool_entries()
    names = {entry["name"]: entry for entry in entries}

    assert "knowledge_search" in names
    assert "search_tool" in names
    assert "research_subagent" in names
    assert "group:knowledge" in names["knowledge_search"]["groups"]
    assert "group:web" in names["search_tool"]["groups"]
    assert "group:research" in names["research_subagent"]["groups"]
    assert "knowledge_research" not in names
    assert "web_research" not in names


def test_build_delivery_artifacts_should_consume_research_subagent_payload() -> None:
    """final composer 应消费统一 research_subagent 结构化结果，而不是遗漏 research goal。"""
    state = {
        "messages": [
            HumanMessage(content="综合知识库和网页资料，帮我对比两种报销口径的差异"),
            ToolMessage(
                content=json.dumps(
                    {
                        "contract_version": "v2",
                        "research_mode": "multi_source",
                        "research_task_id": "research:demo",
                        "summary": "知识库：制度 A 需线下审批；网页：制度 B 可线上审批。",
                        "summary_markdown": "### 知识库\n制度 A 需线下审批。\n\n### 网页\n制度 B 可线上审批。",
                        "evidence": [
                            {"source": "knowledge_search", "excerpt": "制度 A 需线下审批。"},
                            {"source": "search_tool", "excerpt": "制度 B 可线上审批。"},
                        ],
                        "insufficiency": "",
                        "source_count": 2,
                        "citation_count": 1,
                        "media_refs": [],
                    },
                    ensure_ascii=False,
                ),
                tool_call_id="call-research-1",
                name="research_subagent",
            ),
        ],
        "decomposed_goals": [
            {
                "goal_id": "GOAL-01",
                "order": 1,
                "kind": "research.execute",
                "title": "综合研究",
                "must_answer": True,
                "allowed_agents": [],
            }
        ],
        "handoff_execution_trace": [],
    }

    deliverables = multi_agent_graph._build_delivery_artifacts(state)

    assert len(deliverables) == 1
    assert deliverables[0]["kind"] == "research.execute"
    assert deliverables[0]["status"] == "success"
    assert "知识库：制度 A" in deliverables[0]["summary"]
    assert deliverables[0]["payload"]["display_markdown"].startswith("### 知识库")
