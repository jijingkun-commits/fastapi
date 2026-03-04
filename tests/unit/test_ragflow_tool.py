"""RAGFlow 工具测试（中文注释）。

验证检索参数、候选去重、证据卡片与图片占位符契约。
"""

import requests

from app.ai.tools import ragflow_tool
from app.ai.tools.ragflow_tool import (
    _build_metadata_condition,
    _build_retrieval_queries,
    _call_ragflow_retrieval,
    _dedup_and_cap_candidates,
    _format_retrieval_results,
    _merge_and_rerank_candidates,
)


def test_call_ragflow_retrieval_payload_should_split_page_size_and_top_k(monkeypatch) -> None:
    """请求 payload 应同时包含 page_size 与 top_k。"""

    captured: dict = {}

    class _FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"code": 0, "data": {"chunks": []}}

    def _fake_post(url: str, headers: dict, json: dict, timeout: float) -> _FakeResponse:
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        captured["timeout"] = timeout
        return _FakeResponse()

    monkeypatch.setattr(ragflow_tool.requests, "post", _fake_post)
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_API_URL", "http://unit.test/api/v1")
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_API_KEY", "test-key")

    response = _call_ragflow_retrieval(
        query="差旅报销流程",
        dataset_ids=["kb-1"],
        similarity_threshold=0.35,
        page_size=3,
        top_k=9,
        vector_weight=0.7,
        timeout_seconds=12,
    )

    assert response["code"] == 0
    assert captured["url"] == "http://unit.test/api/v1/retrieval"
    assert captured["headers"]["Authorization"] == "Bearer test-key"
    assert captured["json"] == {
        "question": "差旅报销流程",
        "dataset_ids": ["kb-1"],
        "similarity_threshold": 0.35,
        "page_size": 3,
        "top_k": 9,
        "vector_similarity_weight": 0.7,
    }
    assert captured["timeout"] == 12


def test_call_ragflow_retrieval_payload_should_include_metadata_condition(monkeypatch) -> None:
    """显式 metadata_condition 时，请求 payload 应透传过滤条件。"""

    captured: dict = {}

    class _FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"code": 0, "data": {"chunks": []}}

    def _fake_post(url: str, headers: dict, json: dict, timeout: float) -> _FakeResponse:
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        captured["timeout"] = timeout
        return _FakeResponse()

    monkeypatch.setattr(ragflow_tool.requests, "post", _fake_post)
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_API_URL", "http://unit.test/api/v1")
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_API_KEY", "test-key")

    response = _call_ragflow_retrieval(
        query="报销流程",
        dataset_ids=["kb-1"],
        similarity_threshold=0.2,
        page_size=4,
        top_k=8,
        vector_weight=0.6,
        timeout_seconds=10,
        metadata_condition={
            "operator": "and",
            "conditions": [
                {
                    "field": "domain",
                    "operator": "eq",
                    "value": "process",
                }
            ],
        },
    )

    assert response["code"] == 0
    assert captured["json"]["metadata_condition"] == {
        "operator": "and",
        "conditions": [
            {
                "field": "domain",
                "operator": "eq",
                "value": "process",
            }
        ],
    }


def test_build_metadata_condition_should_route_query_to_domain() -> None:
    """命中领域提示词时，应构造 metadata 过滤条件。"""

    condition = _build_metadata_condition(
        "报销流程怎么走",
        enable_domain_routing=True,
        domain_hints={"process": ["报销", "流程"], "product": ["功能"]},
        metadata_field="kb_domain",
    )

    assert condition == {
        "operator": "and",
        "conditions": [
            {
                "field": "kb_domain",
                "operator": "eq",
                "value": "process",
            }
        ],
    }


def test_build_metadata_condition_should_fallback_none_when_no_domain_hit() -> None:
    """未命中领域时，应回退无 metadata 过滤。"""

    condition = _build_metadata_condition(
        "天气如何",
        enable_domain_routing=True,
        domain_hints={"process": ["报销", "流程"]},
    )

    assert condition is None


def test_knowledge_search_payload_should_keep_dataset_override_compatibility(monkeypatch) -> None:
    """显式 dataset_id 仍应优先于默认配置。"""

    captured: dict = {}

    def _fake_retrieval(**kwargs) -> dict:
        captured.update(kwargs)
        return {"code": 0, "data": {"chunks": []}}

    monkeypatch.setattr(ragflow_tool, "_call_ragflow_retrieval", _fake_retrieval)
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_API_KEY", "test-key")
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_DATASET_IDS", ["kb-default"])
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_SIMILARITY_THRESHOLD", 0.2)
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_PAGE_SIZE", 4)
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_TOP_K", 8)
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_VECTOR_WEIGHT", 0.6)
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_TIMEOUT_SECONDS", 20)

    result = ragflow_tool.knowledge_search.func(query="公司请假制度", dataset_id="kb-override")

    assert result == "未找到相关信息。"
    assert captured == {
        "query": "公司请假制度",
        "dataset_ids": ["kb-override"],
        "similarity_threshold": 0.2,
        "page_size": 4,
        "top_k": 8,
        "vector_weight": 0.6,
        "timeout_seconds": 20,
    }


def test_knowledge_search_timeout_should_return_degraded_message(monkeypatch) -> None:
    """请求超时应返回可读降级文案，而不是抛异常。"""

    def _raise_timeout(**_: dict) -> dict:
        raise requests.exceptions.Timeout("ragflow timeout")

    monkeypatch.setattr(ragflow_tool, "_call_ragflow_retrieval", _raise_timeout)
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_API_KEY", "test-key")
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_DATASET_IDS", ["kb-default"])
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_SIMILARITY_THRESHOLD", 0.2)
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_PAGE_SIZE", 4)
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_TOP_K", 8)
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_VECTOR_WEIGHT", 0.6)
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_TIMEOUT_SECONDS", 20)

    result = ragflow_tool.knowledge_search.func(query="社保政策", dataset_id=None)

    assert "知识库检索超时" in result


def test_knowledge_search_metadata_should_fallback_to_full_library_on_filter_error(monkeypatch) -> None:
    """metadata 过滤异常时，应自动回退无过滤检索路径。"""

    captured_calls: list[dict] = []

    def _fake_retrieval(**kwargs) -> dict:
        captured_calls.append(dict(kwargs))
        if kwargs.get("metadata_condition"):
            return {
                "code": 1,
                "message": "metadata condition invalid",
                "data": {"chunks": []},
            }

        return {
            "code": 0,
            "data": {
                "chunks": [
                    {
                        "document_id": "doc-main",
                        "document_keyword": "制度文档",
                        "content": "报销需先提交申请",
                        "similarity": 0.91,
                    }
                ]
            },
        }

    monkeypatch.setattr(ragflow_tool, "_call_ragflow_retrieval", _fake_retrieval)
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_API_KEY", "test-key")
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_DATASET_IDS", ["kb-default"])
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_SIMILARITY_THRESHOLD", 0.2)
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_PAGE_SIZE", 4)
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_TOP_K", 8)
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_VECTOR_WEIGHT", 0.6)
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_TIMEOUT_SECONDS", 20)
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_ENABLE_DOMAIN_ROUTING", True, raising=False)
    monkeypatch.setattr(
        ragflow_tool.config,
        "RAGFLOW_DOMAIN_ROUTING_HINTS",
        {"process": ["报销", "流程"]},
        raising=False,
    )
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_DOMAIN_METADATA_FIELD", "domain", raising=False)

    result = ragflow_tool.knowledge_search.func(query="报销流程", dataset_id=None)

    assert "来源: 制度文档" in result
    assert len(captured_calls) == 2
    assert captured_calls[0]["metadata_condition"] == {
        "operator": "and",
        "conditions": [
            {
                "field": "domain",
                "operator": "eq",
                "value": "process",
            }
        ],
    }
    assert "metadata_condition" not in captured_calls[1]


def test_dedup_candidates_should_remove_repeated_content_within_same_document() -> None:
    """dedup 开启时，同文档重复内容只保留最高分。"""

    chunks = [
        {
            "document_id": "doc-a",
            "content": "报销需先走 OA 审批",
            "similarity": 0.96,
        },
        {
            "document_id": "doc-a",
            "content": "报销需先走 OA 审批\n",
            "similarity": 0.80,
        },
        {
            "document_id": "doc-b",
            "content": "交通费需上传发票",
            "similarity": 0.75,
        },
    ]

    selected = _dedup_and_cap_candidates(
        chunks,
        max_chunks_per_doc=3,
        max_total_chunks=10,
        enable_dedup=True,
        enable_doc_cap=True,
    )

    assert len(selected) == 2
    assert selected[0]["document_id"] == "doc-a"
    assert selected[0]["similarity"] == 0.96
    assert selected[1]["document_id"] == "doc-b"


def test_dedup_candidates_should_limit_chunks_per_document() -> None:
    """doc cap 开启时，每个文档返回条数受控。"""

    chunks = [
        {
            "document_id": "doc-a",
            "content": "A1",
            "similarity": 0.95,
        },
        {
            "document_id": "doc-a",
            "content": "A2",
            "similarity": 0.90,
        },
        {
            "document_id": "doc-a",
            "content": "A3",
            "similarity": 0.85,
        },
        {
            "document_id": "doc-b",
            "content": "B1",
            "similarity": 0.80,
        },
    ]

    selected = _dedup_and_cap_candidates(
        chunks,
        max_chunks_per_doc=2,
        max_total_chunks=10,
        enable_dedup=True,
        enable_doc_cap=True,
    )

    doc_a_chunks = [chunk for chunk in selected if chunk["document_id"] == "doc-a"]
    assert len(doc_a_chunks) == 2
    assert [chunk["content"] for chunk in doc_a_chunks] == ["A1", "A2"]
    assert any(chunk["document_id"] == "doc-b" for chunk in selected)


def test_evidence_cards_should_keep_kb_image_placeholder_dedup() -> None:
    """证据卡片化后依然维持 KB 图片占位符兼容。"""

    chunks = [
        {
            "content": "第一段内容",
            "document_keyword": "文档A",
            "similarity": 0.91,
            "image_id": "img-dup",
        },
        {
            "content": "第二段内容",
            "document_keyword": "文档B",
            "similarity": 0.87,
            "img_id": "img-dup",
        },
    ]

    formatted_text, kb_images = _format_retrieval_results(chunks)

    assert kb_images == {0: "/api/v1/assets/proxy/ragflow/img-dup"}
    assert formatted_text.count("[IMG-0]") == 1
    assert "【证据卡片1】 摘要: 第二段内容" in formatted_text
    assert "【证据卡片1】 摘要: 第二段内容\n   相关图片:" not in formatted_text


def test_evidence_cards_should_keep_stable_placeholder_indices() -> None:
    """多个图片时，占位符按首次出现顺序稳定递增。"""

    chunks = [
        {
            "content": "内容1",
            "document_keyword": "文档1",
            "similarity": 0.95,
            "image_id": "img-a",
        },
        {
            "content": "内容2",
            "document_keyword": "文档2",
            "similarity": 0.90,
            "image_id": "img-b",
        },
        {
            "content": "内容3",
            "document_keyword": "文档3",
            "similarity": 0.88,
            "image_id": "img-a",
        },
    ]

    formatted_text, kb_images = _format_retrieval_results(chunks)

    assert kb_images == {
        0: "/api/v1/assets/proxy/ragflow/img-a",
        1: "/api/v1/assets/proxy/ragflow/img-b",
    }
    assert "相关图片: [IMG-0]" in formatted_text
    assert "相关图片: [IMG-1]" in formatted_text
    assert formatted_text.count("相关图片:") == 2


def test_evidence_cards_should_truncate_long_content_with_configured_limit() -> None:
    """证据卡片摘要应按字符预算截断，降低上下文噪声。"""

    chunks = [
        {
            "content": "A" * 80,
            "document_keyword": "文档",
            "similarity": 0.88,
        }
    ]

    formatted_text, _ = _format_retrieval_results(chunks, max_evidence_chars=20)

    assert "摘要: AAAAAAAAAAAAAAAAAAAA..." in formatted_text


def test_evidence_cards_should_ignore_blank_image_id() -> None:
    """空白 image_id 不应产出占位符。"""

    chunks = [
        {
            "content": "内容",
            "document_keyword": "文档",
            "similarity": 0.80,
            "image_id": "   ",
        }
    ]

    formatted_text, kb_images = _format_retrieval_results(chunks)

    assert kb_images == {}
    assert "相关图片:" not in formatted_text


def test_knowledge_search_should_apply_dedup_and_doc_cap(monkeypatch) -> None:
    """knowledge_search 应在结果组装前执行候选去重与文档限额。"""

    def _fake_retrieval(**_: dict) -> dict:
        return {
            "code": 0,
            "data": {
                "chunks": [
                    {
                        "document_id": "doc-a",
                        "document_keyword": "文档A",
                        "content": "同一段证据",
                        "similarity": 0.95,
                    },
                    {
                        "document_id": "doc-a",
                        "document_keyword": "文档A",
                        "content": "同一段证据\n",
                        "similarity": 0.90,
                    },
                    {
                        "document_id": "doc-a",
                        "document_keyword": "文档A",
                        "content": "文档A的第二段",
                        "similarity": 0.89,
                    },
                    {
                        "document_id": "doc-b",
                        "document_keyword": "文档B",
                        "content": "文档B证据",
                        "similarity": 0.87,
                    },
                ]
            },
        }

    monkeypatch.setattr(ragflow_tool, "_call_ragflow_retrieval", _fake_retrieval)
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_API_KEY", "test-key")
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_DATASET_IDS", ["kb-default"])
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_SIMILARITY_THRESHOLD", 0.2)
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_PAGE_SIZE", 10)
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_TOP_K", 10)
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_VECTOR_WEIGHT", 0.6)
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_TIMEOUT_SECONDS", 20)
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_ENABLE_CANDIDATE_DEDUP", True, raising=False)
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_ENABLE_DOC_CAP", True, raising=False)
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_MAX_CHUNKS_PER_DOC", 1, raising=False)
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_EVIDENCE_MAX_CHARS", 120, raising=False)

    result = ragflow_tool.knowledge_search.func(query="报销流程", dataset_id=None)

    assert result.count("来源: 文档A") == 1
    assert result.count("来源: 文档B") == 1
    assert result.count("【证据卡片") == 2


def test_build_retrieval_queries_rewrite_should_keep_main_and_append_rewrites() -> None:
    """改写路应在保留主路前提下追加扩展查询。"""

    routes = _build_retrieval_queries(
        "新渠道有哪些功能",
        enable_query_rewrite=True,
        rewrite_terms={
            "__default__": ["业务场景"],
            "渠道": ["产品能力", "功能特性"],
        },
        max_rewrite_queries=2,
        main_route_weight=1.0,
        rewrite_route_weight=0.7,
    )

    assert len(routes) == 3
    assert routes[0]["route_id"] == "main"
    assert routes[0]["query"] == "新渠道有哪些功能"
    assert routes[0]["route_weight"] == 1.0
    assert routes[1]["query"] == "新渠道有哪些功能 业务场景"
    assert routes[2]["query"] == "新渠道有哪些功能 产品能力"
    assert all(route["route_weight"] == 0.7 for route in routes[1:])


def test_build_retrieval_queries_rewrite_should_fallback_to_main_on_error() -> None:
    """改写构造异常时应自动回退主路。"""

    class _BrokenMap(dict):
        def items(self):
            raise RuntimeError("broken")

    routes = _build_retrieval_queries(
        "员工请假制度",
        enable_query_rewrite=True,
        rewrite_terms=_BrokenMap({"请假": ["休假"]}),
    )

    assert routes == [
        {
            "route_id": "main",
            "route_name": "原问主路",
            "query": "员工请假制度",
            "route_weight": 1.0,
        }
    ]


def test_merge_and_rerank_candidates_should_keep_explainable_scores() -> None:
    """融合重排应保留 final_score 与 route_weight 等可解释分数。"""

    merged = _merge_and_rerank_candidates(
        [
            {
                "document_id": "doc-a",
                "content": "主路命中",
                "similarity": 0.90,
                "_route_id": "main",
                "_route_weight": 1.0,
            },
            {
                "document_id": "doc-a",
                "content": "主路命中",
                "similarity": 0.86,
                "_route_id": "rewrite_1",
                "_route_weight": 0.8,
            },
            {
                "document_id": "doc-b",
                "content": "改写命中",
                "similarity": 0.88,
                "_route_id": "rewrite_1",
                "_route_weight": 0.8,
            },
        ],
        enable_rerank=True,
        similarity_weight=0.6,
        route_weight_weight=0.4,
    )

    assert merged[0]["document_id"] == "doc-a"
    assert merged[0]["route_hits"] == 2
    assert merged[0]["matched_routes"] == ["main", "rewrite_1"]
    assert merged[0]["route_weight"] == 1.0
    assert merged[0]["final_score"] > merged[1]["final_score"]


def test_format_retrieval_results_should_render_final_score_explanation() -> None:
    """融合后候选应在卡片中展示综合分解释字段。"""

    formatted_text, _ = _format_retrieval_results(
        [
            {
                "content": "融合命中证据",
                "document_keyword": "文档A",
                "similarity": 0.90,
                "final_score": 0.94,
                "route_weight": 1.0,
            }
        ]
    )

    assert "综合分:" in formatted_text
    assert "路由权重" in formatted_text


def test_knowledge_search_rewrite_should_fallback_to_main_when_rewrite_times_out(monkeypatch) -> None:
    """改写路超时时不应阻断主路结果。"""

    calls: list[str] = []

    def _fake_retrieval(**kwargs) -> dict:
        calls.append(kwargs["query"])
        if kwargs["query"] == "报销流程":
            return {
                "code": 0,
                "data": {
                    "chunks": [
                        {
                            "document_id": "doc-main",
                            "document_keyword": "主路文档",
                            "content": "先提交申请再上传发票",
                            "similarity": 0.92,
                        }
                    ]
                },
            }

        raise requests.exceptions.Timeout("rewrite timeout")

    monkeypatch.setattr(ragflow_tool, "_call_ragflow_retrieval", _fake_retrieval)
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_API_KEY", "test-key")
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_DATASET_IDS", ["kb-default"])
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_SIMILARITY_THRESHOLD", 0.2)
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_PAGE_SIZE", 4)
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_TOP_K", 8)
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_VECTOR_WEIGHT", 0.6)
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_TIMEOUT_SECONDS", 20)
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_ENABLE_QUERY_REWRITE", True, raising=False)
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_QUERY_REWRITE_TERMS", ["发票规范"], raising=False)
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_ENABLE_MULTI_ROUTE_RERANK", True, raising=False)
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_ENABLE_CANDIDATE_DEDUP", True, raising=False)
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_ENABLE_DOC_CAP", True, raising=False)
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_MAX_CHUNKS_PER_DOC", 2, raising=False)
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_EVIDENCE_MAX_CHARS", 120, raising=False)

    result = ragflow_tool.knowledge_search.func(query="报销流程", dataset_id=None)

    assert "来源: 主路文档" in result
    assert calls == ["报销流程", "报销流程 发票规范"]


def test_build_retrieval_log_should_include_rollout_fields() -> None:
    """检索观测日志应包含灰度档位与回滚字段。"""

    payload = ragflow_tool._build_retrieval_log(
        phase="complete",
        query="报销流程",
        datasets=["kb-1"],
        retrieval_routes=[{"route_id": "main"}, {"route_id": "rewrite_1"}],
        routed_domain="process",
        metadata_condition={"operator": "and", "conditions": []},
        enable_query_rewrite=True,
        enable_multi_route_rerank=True,
        enable_domain_routing=True,
        rollout_stage="g2",
        rollout_traffic_percent=30,
        rollback_target_stage="s4",
        rollback_switch_enabled=True,
        metrics={"selected_chunks": 2},
    )

    assert payload["phase"] == "complete"
    assert payload["route_count"] == 2
    assert payload["route_ids"] == ["main", "rewrite_1"]
    assert payload["rollout"] == {
        "stage": "g2",
        "traffic_percent": 30,
        "rollback_target_stage": "s4",
        "rollback_switch_enabled": True,
    }
    assert payload["metrics"] == {"selected_chunks": 2}


def test_knowledge_search_retrieval_log_should_track_gray_metrics(monkeypatch, caplog) -> None:
    """knowledge_search 应输出可追踪灰度字段的 retrieval_log。"""

    def _fake_retrieval(**kwargs) -> dict:
        return {
            "code": 0,
            "data": {
                "chunks": [
                    {
                        "document_id": "doc-a",
                        "document_keyword": "制度文档",
                        "content": "报销需先提交申请",
                        "similarity": 0.91,
                    }
                ]
            },
        }

    monkeypatch.setattr(ragflow_tool, "_call_ragflow_retrieval", _fake_retrieval)
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_API_KEY", "test-key")
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_DATASET_IDS", ["kb-default"])
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_SIMILARITY_THRESHOLD", 0.2)
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_PAGE_SIZE", 4)
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_TOP_K", 8)
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_VECTOR_WEIGHT", 0.6)
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_TIMEOUT_SECONDS", 20)
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_ENABLE_QUERY_REWRITE", False, raising=False)
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_ENABLE_MULTI_ROUTE_RERANK", False, raising=False)
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_ENABLE_DOMAIN_ROUTING", False, raising=False)
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_ENABLE_CANDIDATE_DEDUP", True, raising=False)
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_ENABLE_DOC_CAP", True, raising=False)
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_MAX_CHUNKS_PER_DOC", 2, raising=False)
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_EVIDENCE_MAX_CHARS", 120, raising=False)
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_ROLLOUT_STAGE", "g2", raising=False)
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_ROLLOUT_TRAFFIC_PERCENT", 30, raising=False)
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_ROLLBACK_TARGET_STAGE", "s4", raising=False)
    monkeypatch.setattr(ragflow_tool.config, "RAGFLOW_ENABLE_ROLLBACK_SWITCH", True, raising=False)

    with caplog.at_level("INFO", logger=ragflow_tool.__name__):
        result = ragflow_tool.knowledge_search.func(query="报销流程", dataset_id=None)

    assert "来源: 制度文档" in result

    retrieval_logs: list[dict] = []
    for record in caplog.records:
        if record.msg != "RAGFlow 检索观测: %s":
            continue

        if isinstance(record.args, tuple) and record.args and isinstance(record.args[0], dict):
            retrieval_logs.append(record.args[0])
            continue

        if isinstance(record.args, dict):
            retrieval_logs.append(record.args)

    assert len(retrieval_logs) == 2

    start_log = next(log for log in retrieval_logs if log.get("phase") == "start")
    complete_log = next(log for log in retrieval_logs if log.get("phase") == "complete")

    assert start_log["rollout"]["stage"] == "g2"
    assert start_log["rollout"]["traffic_percent"] == 30
    assert complete_log["metrics"]["selected_chunks"] == 1
    assert complete_log["metrics"]["selected_document_ids"] == ["doc-a"]
    assert complete_log["metrics"]["kb_image_count"] == 0
