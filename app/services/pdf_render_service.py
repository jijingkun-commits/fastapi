"""试卷 PDF 渲染服务（中文注释）。

当前实现采用内置轻量 PDF 写入器，保持 `render_exam_pdf` 作为唯一入口，
后续可在不改调用方的前提下替换为 WeasyPrint 等实现。
"""
from __future__ import annotations

from io import BytesIO

from app.schemas.exam_generation import PaperContract

PAGE_WIDTH = 595
PAGE_HEIGHT = 842
MARGIN_X = 50
MARGIN_TOP = 60
LINE_HEIGHT = 18
FONT_SIZE = 12
TITLE_SIZE = 18
SECTION_SIZE = 14


def _escape_pdf_text(text: str) -> str:
    return str(text).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _paginate_lines(lines: list[tuple[str, int]]) -> list[list[tuple[str, int]]]:
    pages: list[list[tuple[str, int]]] = [[]]
    y = PAGE_HEIGHT - MARGIN_TOP
    for text, size in lines:
        if y < 70:
            pages.append([])
            y = PAGE_HEIGHT - MARGIN_TOP
        pages[-1].append((text, size))
        y -= LINE_HEIGHT if size <= FONT_SIZE else LINE_HEIGHT + 4
    return [page for page in pages if page]


def _build_question_lines(paper: PaperContract) -> list[tuple[str, int]]:
    lines: list[tuple[str, int]] = []
    lines.append((paper.paper_title, TITLE_SIZE))
    lines.append((f"知识库范围: {', '.join(paper.dataset_ids)}", FONT_SIZE))
    lines.append(("", FONT_SIZE))
    current_type = None
    for index, question in enumerate(paper.questions, start=1):
        if question.question_type != current_type:
            current_type = question.question_type
            section_title = {
                "single_choice": "一、单选题",
                "multiple_choice": "二、多选题",
                "judge": "三、判断题",
                "short_answer": "四、简答题",
            }[current_type]
            lines.append((section_title, SECTION_SIZE))
        lines.append((f"{index}. {question.stem}", FONT_SIZE))
        for option in question.options:
            lines.append((f"   {option.key}. {option.text}", FONT_SIZE))
        lines.append(("", FONT_SIZE))
    return lines


def _build_answer_lines(paper: PaperContract) -> list[tuple[str, int]]:
    lines: list[tuple[str, int]] = []
    lines.append(("—— 答案与简短解析 ——", SECTION_SIZE))
    for index, question in enumerate(paper.questions, start=1):
        answer_text = "、".join(question.answers) if question.answers else (question.reference_answer or "参考答案见要点")
        lines.append((f"{index}. 答案：{answer_text}", FONT_SIZE))
        if question.answer_points:
            for point in question.answer_points:
                lines.append((f"   - {point}", FONT_SIZE))
        if paper.render_options.answer_explanation_mode == "short":
            lines.append((f"   解析：{question.explanation}", FONT_SIZE))
        lines.append(("", FONT_SIZE))
    return lines


def _build_page_stream(lines: list[tuple[str, int]]) -> bytes:
    commands: list[str] = ["BT", "/F1 12 Tf"]
    y = PAGE_HEIGHT - MARGIN_TOP
    for text, size in lines:
        escaped = _escape_pdf_text(text)
        commands.append(f"/F1 {size} Tf")
        commands.append(f"1 0 0 1 {MARGIN_X} {y} Tm ({escaped}) Tj")
        y -= LINE_HEIGHT if size <= FONT_SIZE else LINE_HEIGHT + 4
    commands.append("ET")
    return "\n".join(commands).encode("utf-8")


def _build_simple_pdf(page_streams: list[bytes]) -> bytes:
    objects: list[bytes] = []
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    page_refs = [f"{4 + idx * 2} 0 R" for idx in range(len(page_streams))]
    objects.append(f"<< /Type /Pages /Count {len(page_streams)} /Kids [{' '.join(page_refs)}] >>".encode())
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    for idx, stream in enumerate(page_streams):
        page_obj_num = 4 + idx * 2
        content_obj_num = page_obj_num + 1
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] /Resources << /Font << /F1 3 0 R >> >> /Contents {content_obj_num} 0 R >>".encode()
        )
        objects.append(f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream")

    buffer = BytesIO()
    buffer.write(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(buffer.tell())
        buffer.write(f"{index} 0 obj\n".encode())
        buffer.write(obj)
        buffer.write(b"\nendobj\n")
    xref_start = buffer.tell()
    buffer.write(f"xref\n0 {len(objects)+1}\n".encode())
    buffer.write(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        buffer.write(f"{offset:010d} 00000 n \n".encode())
    buffer.write(f"trailer\n<< /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref_start}\n%%EOF".encode())
    return buffer.getvalue()


def render_exam_pdf(paper: PaperContract) -> bytes:
    question_lines = _build_question_lines(paper)
    answer_lines = _build_answer_lines(paper) if paper.render_options.answer_section_enabled else []
    if answer_lines and paper.render_options.answer_page_break:
        pages = _paginate_lines(question_lines) + _paginate_lines(answer_lines)
    else:
        pages = _paginate_lines(question_lines + answer_lines)
    streams = [_build_page_stream(page) for page in pages]
    return _build_simple_pdf(streams)
