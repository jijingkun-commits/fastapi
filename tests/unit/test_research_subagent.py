"""research_subagent 单元测试。"""

import json

from app.ai.protocol import AgentOutputParser
from app.ai.agents import research_subagent as research_module


def test_research_subagent_should_merge_multisource_contract(monkeypatch) -> None:
    """统一 research_subagent 应合并 knowledge/web 结果，并保留媒体引用。"""

    monkeypatch.setattr(
        research_module,
        "build_knowledge_research_source_payload",
        lambda query, dataset_id=None: {
            "research_mode": "knowledge",
            "summary": "知识库结论：制度 A 需要部门审批。",
            "summary_markdown": "知识库结论：制度 A 需要部门审批。[IMG-0]",
            "evidence": [{"source": "knowledge_search", "excerpt": "制度 A 需要部门审批。"}],
            "insufficiency": "",
            "source_count": 1,
            "citation_count": 1,
            "media_refs": [
                {
                    "type": "knowledge_image",
                    "url": "/api/v1/assets/proxy/ragflow/img-0",
                    "alt": "制度图片",
                    "source": "knowledge",
                    "index": "0",
                }
            ],
        },
        raising=False,
    )
    monkeypatch.setattr(
        research_module,
        "build_web_research_source_payload",
        lambda query: {
            "research_mode": "web",
            "summary": "网页补充：制度 B 允许线上审批。",
            "summary_markdown": "- 网页补充：制度 B 允许线上审批。",
            "evidence": [{"source": "search_tool", "excerpt": "制度 B 允许线上审批。"}],
            "insufficiency": "",
            "source_count": 1,
            "citation_count": 1,
            "media_refs": [],
        },
        raising=False,
    )

    payload = json.loads(research_module.research_subagent.func(query="综合制度差异", dataset_id=None))

    assert payload["contract_version"] == "v2"
    assert payload["research_mode"] == "multi_source"
    assert "知识库结论" in payload["summary"]
    assert "网页补充" in payload["summary_markdown"]
    assert len(payload["evidence"]) == 2
    assert payload["media_refs"][0]["type"] == "knowledge_image"
    assert payload["insufficiency"] == ""


def test_research_subagent_should_return_structured_insufficiency_without_raw_noise(monkeypatch) -> None:
    """所有来源都不足时，应返回结构化 insufficiency，而不是工具原始噪声。"""

    monkeypatch.setattr(
        research_module,
        "build_knowledge_research_source_payload",
        lambda query, dataset_id=None: {
            "research_mode": "knowledge",
            "summary": "",
            "summary_markdown": "",
            "evidence": [],
            "insufficiency": "knowledge_search 未返回可用证据",
            "source_count": 0,
            "citation_count": 0,
            "media_refs": [],
        },
        raising=False,
    )
    monkeypatch.setattr(
        research_module,
        "build_web_research_source_payload",
        lambda query: {
            "research_mode": "web",
            "summary": "",
            "summary_markdown": "",
            "evidence": [],
            "insufficiency": "联网搜索不可用，请检查 TAVILY_API_KEY 或工具依赖。",
            "source_count": 0,
            "citation_count": 0,
            "media_refs": [],
        },
        raising=False,
    )

    payload = json.loads(research_module.research_subagent.func(query="整理今天的制度差异", dataset_id=None))

    assert payload["contract_version"] == "v2"
    assert payload["summary"] == ""
    assert payload["summary_markdown"] == ""
    assert payload["media_refs"] == []
    assert "knowledge_search 未返回可用证据" in payload["insufficiency"]
    assert "联网搜索不可用" in payload["insufficiency"]


def test_parse_kb_images_should_extract_knowledge_media_refs_from_research_payload() -> None:
    """research contract 中的 knowledge media_refs 应复用为 canonical kb_images。"""
    payload = {
        "contract_version": "v2",
        "research_mode": "multi_source",
        "research_task_id": "research:demo",
        "summary": "制度摘要",
        "summary_markdown": "### 知识库\n制度摘要 [IMG-0]",
        "evidence": [{"source": "knowledge_search", "excerpt": "制度摘要"}],
        "insufficiency": "",
        "source_count": 1,
        "citation_count": 1,
        "media_refs": [
            {
                "type": "knowledge_image",
                "url": "/api/v1/assets/proxy/ragflow/img-0",
                "alt": "制度图片",
                "source": "knowledge",
                "index": "0",
            }
        ],
    }

    assert AgentOutputParser.parse_kb_images(json.dumps(payload, ensure_ascii=False)) == {
        "0": "/api/v1/assets/proxy/ragflow/img-0",
    }
