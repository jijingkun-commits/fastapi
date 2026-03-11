from __future__ import annotations

from datetime import datetime

from app.schemas.exam_generation import ExamQuestion, PaperContract, PaperRenderOptions, QuestionEvidence, QuestionOption
from app.services.pdf_render_service import render_exam_pdf


def _build_paper(*, question_count: int = 7, answer_page_break: bool = True) -> PaperContract:
    questions = []
    for idx in range(1, question_count + 1):
        questions.append(
            ExamQuestion(
                question_id=f"Q{idx:03d}",
                question_type="single_choice",
                stem=f"第 {idx} 题：根据资料回答问题。",
                options=[
                    QuestionOption(key="A", text="正确选项"),
                    QuestionOption(key="B", text="错误选项"),
                ],
                answers=["A"],
                explanation="原文依据：测试。",
                evidence=[QuestionEvidence(dataset_id="kb-a", source_name="文档", excerpt="片段")],
            )
        )
    return PaperContract(
        paper_title="PDF 测试卷",
        dataset_ids=["kb-a"],
        generated_at=datetime.now(),
        questions=questions,
        render_options=PaperRenderOptions(answer_page_break=answer_page_break),
    )


def _count_pdf_pages(payload: bytes) -> int:
    return payload.count(b"/Type /Page /Parent")


def test_render_exam_pdf_should_return_pdf_bytes() -> None:
    payload = render_exam_pdf(_build_paper())
    assert payload.startswith(b"%PDF-1.4")
    assert b"/Type /Page" in payload


def test_render_exam_pdf_should_force_answer_section_page_break() -> None:
    with_page_break = render_exam_pdf(_build_paper(question_count=1, answer_page_break=True))
    without_page_break = render_exam_pdf(_build_paper(question_count=1, answer_page_break=False))

    assert _count_pdf_pages(with_page_break) == 2
    assert _count_pdf_pages(without_page_break) == 1
