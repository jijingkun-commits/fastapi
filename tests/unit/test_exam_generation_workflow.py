from __future__ import annotations

import pytest

from app.ai.workflow import exam_generation_workflow as workflow
from app.schemas.exam_generation import PaperTemplateRequest


def _template() -> PaperTemplateRequest:
    return PaperTemplateRequest(
        paper_title="测试试卷",
        single_choice_count=1,
        multiple_choice_count=0,
        judge_count=0,
        short_answer_count=0,
    )


def test_retrieve_exam_evidence_should_prioritize_earlier_dataset(monkeypatch) -> None:
    captured_chunks = []
    monkeypatch.setattr(workflow.ragflow_tool.config, "RAGFLOW_API_KEY", "demo", raising=False)

    def _retrieve_chunks_for_query(**kwargs):
        dataset_id = kwargs["dataset_ids"][0]
        query = kwargs["query"]
        return ([{
            "document_name": f"{dataset_id}-{query}",
            "content": f"{dataset_id}-{query}-知识点",
            "similarity": 0.9,
        }], None)

    def _merge_and_rerank_candidates(route_chunks, **kwargs):
        captured_chunks.extend(route_chunks)
        assert kwargs['enable_rerank'] is True
        return route_chunks

    monkeypatch.setattr(workflow.ragflow_tool, "_retrieve_chunks_for_query", _retrieve_chunks_for_query)
    monkeypatch.setattr(workflow.ragflow_tool, "_merge_and_rerank_candidates", _merge_and_rerank_candidates)
    monkeypatch.setattr(workflow.ragflow_tool, "_dedup_and_cap_candidates", lambda chunks, **kwargs: chunks)

    bundle = workflow.retrieve_exam_evidence(["kb-a", "kb-b"], _template())

    assert bundle.chunks
    kb_a_weights = [chunk["route_weight"] for chunk in captured_chunks if chunk["dataset_id"] == "kb-a"]
    kb_b_weights = [chunk["route_weight"] for chunk in captured_chunks if chunk["dataset_id"] == "kb-b"]
    assert min(kb_a_weights) > max(kb_b_weights)


def test_retrieve_exam_evidence_should_fail_on_dataset_conflict(monkeypatch) -> None:
    monkeypatch.setattr(workflow.ragflow_tool.config, "RAGFLOW_API_KEY", "demo", raising=False)

    def _retrieve_chunks_for_query(**kwargs):
        dataset_id = kwargs["dataset_ids"][0]
        content = "必须执行该步骤。" if dataset_id == "kb-a" else "不得执行该步骤。"
        return ([{
            "document_name": "冲突文档",
            "content": content,
            "similarity": 0.9,
        }], None)

    monkeypatch.setattr(workflow.ragflow_tool, "_retrieve_chunks_for_query", _retrieve_chunks_for_query)
    monkeypatch.setattr(workflow.ragflow_tool, "_merge_and_rerank_candidates", lambda chunks, **kwargs: chunks)
    monkeypatch.setattr(workflow.ragflow_tool, "_dedup_and_cap_candidates", lambda chunks, **kwargs: chunks)

    with pytest.raises(ValueError, match="多数据集知识冲突"):
        workflow.retrieve_exam_evidence(["kb-a", "kb-b"], _template())
