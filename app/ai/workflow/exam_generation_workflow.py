"""AI 出题独立工作流（中文注释）。"""
from __future__ import annotations

import json
import logging
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.ai.llm_util import _normalize_text_content, get_scene_llm
from app.ai.scene_registry import SCENE_KEY_MULTI_AGENT_SUPERVISOR
from app.ai.tools import ragflow_tool
from app.schemas.exam_generation import (
    ExamQuestion,
    ExamQualityIssue,
    ExamQualityReport,
    PaperContract,
    PaperRenderOptions,
    PaperTemplateRequest,
    QuestionEvidence,
    QuestionOption,
)

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class RetrievalBundle:
    chunks: list[dict[str, Any]]
    queries: list[str]


def _build_render_options(template: PaperTemplateRequest) -> PaperRenderOptions:
    return template.build_render_options()


def _attach_render_options(paper: PaperContract, template: PaperTemplateRequest) -> PaperContract:
    return paper.model_copy(update={"render_options": _build_render_options(template)})


def _extract_json_object(raw: str) -> str:
    text = str(raw or "").strip()
    if not text:
        raise ValueError("LLM 返回为空")
    if "```" in text:
        match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, flags=re.DOTALL)
        if match:
            return match.group(1)
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("LLM 返回不包含 JSON 对象")
    return text[start : end + 1]


def _sanitize_excerpt(raw: Any, max_chars: int = 120) -> str:
    text = " ".join(str(raw or "").split())
    return text[:max_chars] if len(text) > max_chars else text


def _build_retrieval_queries(template: PaperTemplateRequest) -> list[str]:
    base = [
        f"{template.paper_title} 核心知识点",
        f"{template.paper_title} 关键概念与判断依据",
    ]
    if template.short_answer_count > 0:
        base.append(f"{template.paper_title} 简答题要点")
    if template.multiple_choice_count > 0:
        base.append(f"{template.paper_title} 多选题知识点")
    return base


def _has_conflict_keywords(text: str) -> tuple[bool, bool]:
    normalized = str(text or "").strip()
    positive = any(token in normalized for token in ("必须", "应", "需要", "可以", "允许"))
    negative = any(token in normalized for token in ("不得", "禁止", "不可", "无需", "不需要"))
    return positive, negative


def _detect_dataset_conflict(chunks: list[dict[str, Any]]) -> bool:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for chunk in chunks:
        source = str(chunk.get("document_keyword") or chunk.get("document_name") or "").strip()
        if not source:
            continue
        grouped.setdefault(source, []).append(chunk)

    for items in grouped.values():
        dataset_ids = {str(item.get("dataset_id") or "").strip() for item in items if str(item.get("dataset_id") or "").strip()}
        if len(dataset_ids) < 2:
            continue
        flags = [_has_conflict_keywords(str(item.get("content") or "")) for item in items]
        has_positive = any(item[0] for item in flags)
        has_negative = any(item[1] for item in flags)
        if has_positive and has_negative:
            return True
    return False


def retrieve_exam_evidence(dataset_ids: list[str], template: PaperTemplateRequest) -> RetrievalBundle:
    if not dataset_ids:
        raise ValueError("dataset_ids 不能为空")
    if not ragflow_tool.config.RAGFLOW_API_KEY:
        raise ValueError("知识库未配置：缺少 RAGFLOW_API_KEY")

    queries = _build_retrieval_queries(template)
    route_chunks: list[dict[str, Any]] = []
    for dataset_index, dataset_id in enumerate(dataset_ids):
        for route_index, query in enumerate(queries):
            chunks, error_msg = ragflow_tool._retrieve_chunks_for_query(  # type: ignore[attr-defined]
                query=query,
                dataset_ids=[dataset_id],
                similarity_threshold=ragflow_tool.config.RAGFLOW_SIMILARITY_THRESHOLD,
                page_size=max(template.total_question_count * 2, ragflow_tool.config.RAGFLOW_PAGE_SIZE),
                top_k=max(template.total_question_count * 2, ragflow_tool.config.RAGFLOW_TOP_K),
                vector_weight=ragflow_tool.config.RAGFLOW_VECTOR_WEIGHT,
                timeout_seconds=ragflow_tool.config.RAGFLOW_TIMEOUT_SECONDS,
                metadata_condition=None,
            )
            if error_msg:
                logger.warning("exam_generation_retrieval_route_error: dataset=%s query=%s error=%s", dataset_id, query, error_msg)
            for chunk in chunks:
                enriched = dict(chunk)
                enriched["dataset_id"] = dataset_id
                enriched["route_query"] = query
                enriched["route_weight"] = max(0.1, 1.0 - (dataset_index * 0.15) - (route_index * 0.05))
                route_chunks.append(enriched)

    merged = ragflow_tool._merge_and_rerank_candidates(  # type: ignore[attr-defined]
        route_chunks,
        enable_rerank=True,
        similarity_weight=0.7,
        route_weight_weight=0.3,
    )
    selected = ragflow_tool._dedup_and_cap_candidates(  # type: ignore[attr-defined]
        merged,
        max_chunks_per_doc=2,
        max_total_chunks=max(template.total_question_count * 2, 12),
        enable_dedup=True,
        enable_doc_cap=True,
    )
    if not selected:
        raise ValueError("知识证据不足，无法按模板生成")
    if _detect_dataset_conflict(selected):
        raise ValueError("多数据集知识冲突，请缩小知识库范围后重试")
    return RetrievalBundle(chunks=selected, queries=queries)


def _build_evidence(chunk: dict[str, Any], dataset_id: str | None = None) -> QuestionEvidence:
    source_name = str(chunk.get("document_keyword") or chunk.get("document_name") or "知识片段").strip() or "知识片段"
    return QuestionEvidence(
        dataset_id=str(chunk.get("dataset_id") or dataset_id or ""),
        document_id=str(chunk.get("document_id") or chunk.get("doc_id") or "") or None,
        source_name=source_name,
        excerpt=_sanitize_excerpt(chunk.get("content", ""), 160),
        score=float(chunk.get("final_score", chunk.get("similarity", 0)) or 0),
    )


def _split_sentences(text: str) -> list[str]:
    parts = [part.strip() for part in re.split(r"[；;。.!？?\n]", text) if part.strip()]
    return parts[:4] or [text.strip()]


def _build_single_choice(question_id: str, evidence: QuestionEvidence) -> ExamQuestion:
    key_fact = _split_sentences(evidence.excerpt)[0]
    options = [
        QuestionOption(key="A", text=key_fact),
        QuestionOption(key="B", text="资料明确否定该知识点。"),
        QuestionOption(key="C", text="资料未涉及该知识点。"),
        QuestionOption(key="D", text="该知识点与原文无关。"),
    ]
    return ExamQuestion(
        question_id=question_id,
        question_type="single_choice",
        stem=f"根据资料《{evidence.source_name}》，下列哪一项最符合原文？",
        options=options,
        answers=["A"],
        explanation=f"原文依据：{key_fact}",
        evidence=[evidence],
    )


def _build_multiple_choice(question_id: str, evidence: QuestionEvidence) -> ExamQuestion:
    facts = _split_sentences(evidence.excerpt)
    first = facts[0]
    second = facts[1] if len(facts) > 1 else f"资料围绕《{evidence.source_name}》展开说明。"
    options = [
        QuestionOption(key="A", text=first),
        QuestionOption(key="B", text=second),
        QuestionOption(key="C", text="资料说明该事项完全无需处理。"),
        QuestionOption(key="D", text="资料与该主题完全无关。"),
    ]
    return ExamQuestion(
        question_id=question_id,
        question_type="multiple_choice",
        stem=f"根据资料《{evidence.source_name}》，以下哪些说法符合原文？",
        options=options,
        answers=["A", "B"],
        explanation=f"原文同时强调：{first}；{second}",
        evidence=[evidence],
    )


def _build_judge(question_id: str, evidence: QuestionEvidence) -> ExamQuestion:
    fact = _split_sentences(evidence.excerpt)[0]
    return ExamQuestion(
        question_id=question_id,
        question_type="judge",
        stem=f"判断题：{fact}",
        options=[QuestionOption(key="A", text="对"), QuestionOption(key="B", text="错")],
        answers=["A"],
        explanation=f"判断依据：{fact}",
        evidence=[evidence],
    )


def _build_short_answer(question_id: str, evidence: QuestionEvidence) -> ExamQuestion:
    points = _split_sentences(evidence.excerpt)[:3]
    return ExamQuestion(
        question_id=question_id,
        question_type="short_answer",
        stem=f"请简述资料《{evidence.source_name}》中的关键要点。",
        options=[],
        answers=[],
        explanation=f"参考要点：{'；'.join(points)}",
        reference_answer="；".join(points),
        answer_points=points,
        evidence=[evidence],
    )


def _fallback_generate_paper(template: PaperTemplateRequest, dataset_ids: list[str], bundle: RetrievalBundle) -> PaperContract:
    question_builders = [
        (template.single_choice_count, _build_single_choice, None),
        (template.multiple_choice_count, _build_multiple_choice, None),
        (template.judge_count, _build_judge, None),
        (template.short_answer_count, _build_short_answer, None),
    ]
    questions: list[ExamQuestion] = []
    chunk_index = 0
    for count, builder, dataset_id in question_builders:
        for _ in range(count):
            chunk = bundle.chunks[chunk_index % len(bundle.chunks)]
            chunk_index += 1
            evidence = _build_evidence(chunk, dataset_id)
            questions.append(builder(f"Q{len(questions)+1:03d}", evidence))
    return PaperContract(
        paper_title=template.paper_title,
        dataset_ids=list(dataset_ids),
        generated_at=datetime.now(),
        questions=questions,
    )


def _llm_generate_paper(template: PaperTemplateRequest, dataset_ids: list[str], bundle: RetrievalBundle) -> PaperContract:
    llm = get_scene_llm(scene_key=SCENE_KEY_MULTI_AGENT_SUPERVISOR, temperature=0)
    evidence_payload = []
    for index, chunk in enumerate(bundle.chunks[: max(template.total_question_count * 2, 8)], start=1):
        evidence_payload.append(
            {
                "evidence_id": f"E{index:03d}",
                "dataset_id": chunk.get("dataset_id") or dataset_ids[0],
                "document_id": chunk.get("document_id") or chunk.get("doc_id"),
                "source_name": chunk.get("document_keyword") or chunk.get("document_name") or "知识片段",
                "excerpt": _sanitize_excerpt(chunk.get("content", ""), 220),
            }
        )
    prompt = f"""
你是出题助手。请基于提供的知识证据生成一份结构化试卷 JSON，不得编造证据来源。
输出必须是 JSON 对象，字段：paper_title, dataset_ids, generated_at, questions。
questions[*] 字段：question_id, question_type, stem, options, answers, explanation, reference_answer, answer_points, evidence。
题型固定只允许：single_choice, multiple_choice, judge, short_answer。
要求：
1. 单选题只有 1 个正确答案；多选题至少 2 个正确答案；判断题答案只能是 A(对) 或 B(错)。
2. 每道题必须至少绑定 1 条 evidence。
3. explanation 只能写简短解析。
4. 严格按模板题量输出，不得缺题。
5. dataset_ids 必须原样保留为 {json.dumps(dataset_ids, ensure_ascii=False)}。
模板：{template.model_dump_json(ensure_ascii=False)}
证据：{json.dumps(evidence_payload, ensure_ascii=False)}
"""
    response = llm.invoke(prompt)
    content = _normalize_text_content(response.content if hasattr(response, "content") else response)
    payload = json.loads(_extract_json_object(content))
    return PaperContract.model_validate(payload)


def generate_paper_contract(template: PaperTemplateRequest, dataset_ids: list[str]) -> PaperContract:
    bundle = retrieve_exam_evidence(dataset_ids, template)
    try:
        paper = _llm_generate_paper(template, dataset_ids, bundle)
    except Exception as exc:
        logger.warning("exam_generation_llm_fallback: %s", exc)
        paper = _fallback_generate_paper(template, dataset_ids, bundle)
    return _attach_render_options(paper, template)


def evaluate_paper_contract(paper: PaperContract) -> ExamQualityReport:
    issues: list[ExamQualityIssue] = []
    duplicate_count = 0
    evidence_missing_count = 0
    normalized_stems = [re.sub(r"\s+", "", item.stem) for item in paper.questions]
    stem_counts = Counter(normalized_stems)
    duplicate_count = sum(count - 1 for count in stem_counts.values() if count > 1)
    if duplicate_count > 0:
        for stem, count in stem_counts.items():
            if count > 1:
                issues.append(ExamQualityIssue(code="duplicate_question", message="存在重复题干"))
                break

    unique_docs: set[str] = set()
    for question in paper.questions:
        if not question.evidence:
            evidence_missing_count += 1
            issues.append(ExamQualityIssue(code="missing_evidence", message="题目缺少证据", question_id=question.question_id))
        else:
            for evidence in question.evidence:
                doc_key = f"{evidence.dataset_id}:{evidence.document_id or evidence.source_name}"
                unique_docs.add(doc_key)
        if question.question_type == "single_choice" and len(question.answers) != 1:
            issues.append(ExamQualityIssue(code="single_choice_answer_invalid", message="单选题必须只有一个正确答案", question_id=question.question_id))
        if question.question_type == "multiple_choice" and len(question.answers) < 2:
            issues.append(ExamQualityIssue(code="multiple_choice_answer_invalid", message="多选题至少两个正确答案", question_id=question.question_id))
        if question.question_type == "judge" and not set(question.answers).issubset({"A", "B"}):
            issues.append(ExamQualityIssue(code="judge_answer_invalid", message="判断题答案只能是 A 或 B", question_id=question.question_id))
        if not question.explanation.strip():
            issues.append(ExamQualityIssue(code="missing_explanation", message="缺少简短解析", question_id=question.question_id))

    coverage_score = round(len(unique_docs) / max(1, len(paper.questions)), 4)
    if len(paper.questions) >= 4 and coverage_score < 0.4:
        issues.append(ExamQualityIssue(code="coverage_too_low", message="知识点覆盖度过低"))

    passed = not issues
    return ExamQualityReport(
        passed=passed,
        duplicate_count=duplicate_count,
        evidence_missing_count=evidence_missing_count,
        coverage_score=coverage_score,
        issues=issues,
    )
