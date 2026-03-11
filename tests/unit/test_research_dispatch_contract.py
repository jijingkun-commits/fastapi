import json

from app.ai.workflow import multi_agent_graph
from app.ai.tools import chatTools
from app.ai.tools import ragflow_tool


def test_web_research_should_return_stable_insufficiency_when_search_unavailable(monkeypatch):
    """search_tool 不可用时，web_research 应返回稳定 insufficiency，而不是异常冒泡。"""
    monkeypatch.setattr(chatTools, "search_tool", None, raising=False)

    payload = json.loads(chatTools.web_research.func(query="整理今天的正面新闻"))

    assert payload["research_mode"] == "web"
    assert payload["insufficiency"]
    assert payload["source_count"] == 0


def test_get_supervisor_tool_entries_should_keep_atomic_tools_and_research_entries(monkeypatch):
    """Supervisor 工具集合应同时保留 atomic tool 和 research 入口。"""
    from app.services.skill_service import SkillService

    def _knowledge_search():
        return "ok"

    def _knowledge_research():
        return "ok"

    class _SearchTool:
        name = "search_tool"

        def invoke(self, _payload):
            return []

    def _web_research():
        return "ok"

    _knowledge_search.__name__ = "knowledge_search"
    _knowledge_research.__name__ = "knowledge_research"
    _web_research.__name__ = "web_research"

    monkeypatch.setattr(multi_agent_graph, "_get_common_tool_entries", lambda: [], raising=False)
    monkeypatch.setattr(SkillService, "resolve_runtime_mode", classmethod(lambda cls: "legacy"))
    monkeypatch.setattr(ragflow_tool, "is_ragflow_configured", lambda: True, raising=False)
    monkeypatch.setattr(ragflow_tool, "knowledge_search", _knowledge_search, raising=False)
    monkeypatch.setattr(ragflow_tool, "knowledge_research", _knowledge_research, raising=False)
    monkeypatch.setattr(chatTools, "search_tool", _SearchTool(), raising=False)
    monkeypatch.setattr(chatTools, "web_research", _web_research, raising=False)

    entries = multi_agent_graph._get_supervisor_tool_entries()
    names = {entry["name"]: entry for entry in entries}

    assert "knowledge_search" in names
    assert "knowledge_research" in names
    assert "web_research" in names
    assert "group:knowledge" in names["knowledge_search"]["groups"]
    assert "group:research" in names["knowledge_research"]["groups"]
    assert "group:research" in names["web_research"]["groups"]
