from __future__ import annotations

import pytest

from app.schemas.exam_generation import ExamQuestion, PaperContract, PaperTemplateRequest, QuestionEvidence, QuestionOption
from app.ai.workflow.exam_generation_workflow import evaluate_paper_contract


def test_paper_template_requires_positive_total_questions() -> None:
    with pytest.raises(ValueError):
        PaperTemplateRequest(
            paper_title="空试卷",
            single_choice_count=0,
            multiple_choice_count=0,
            judge_count=0,
            short_answer_count=0,
        )


def test_quality_gate_should_block_invalid_single_choice_answer_count() -> None:
    paper = PaperContract(
        paper_title="测试卷",
        dataset_ids=["kb-a"],
        generated_at="2026-03-11T00:00:00",
        questions=[
            ExamQuestion(
                question_id="Q001",
                question_type="single_choice",
                stem="测试题",
                options=[QuestionOption(key="A", text="选项 A")],
                answers=["A", "B"],
                explanation="解析",
                evidence=[QuestionEvidence(dataset_id="kb-a", source_name="文档", excerpt="片段")],
            )
        ],
    )
    report = evaluate_paper_contract(paper)
    assert report.passed is False
    assert any(item.code == "single_choice_answer_invalid" for item in report.issues)


def test_quality_gate_should_block_missing_evidence() -> None:
    paper = PaperContract(
        paper_title="测试卷",
        dataset_ids=["kb-a"],
        generated_at="2026-03-11T00:00:00",
        questions=[
            ExamQuestion(
                question_id="Q001",
                question_type="single_choice",
                stem="缺少证据的题目",
                options=[QuestionOption(key="A", text="选项 A")],
                answers=["A"],
                explanation="解析",
                evidence=[],
            )
        ],
    )
    report = evaluate_paper_contract(paper)
    assert report.passed is False
    assert report.evidence_missing_count == 1
    assert any(item.code == "missing_evidence" for item in report.issues)


def test_quality_gate_should_block_low_coverage() -> None:
    shared_evidence = [QuestionEvidence(dataset_id="kb-a", source_name="同一文档", excerpt="片段")]
    paper = PaperContract(
        paper_title="测试卷",
        dataset_ids=["kb-a"],
        generated_at="2026-03-11T00:00:00",
        questions=[
            ExamQuestion(
                question_id=f"Q{index:03d}",
                question_type="single_choice",
                stem=f"测试题 {index}",
                options=[QuestionOption(key="A", text="选项 A")],
                answers=["A"],
                explanation="解析",
                evidence=shared_evidence,
            )
            for index in range(1, 5)
        ],
    )
    report = evaluate_paper_contract(paper)
    assert report.passed is False
    assert report.coverage_score == 0.25
    assert any(item.code == "coverage_too_low" for item in report.issues)
