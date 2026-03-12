"""message_display_blocks 单元测试。"""

from app.core.message_display_blocks import compile_message_display_blocks


def test_compile_message_display_blocks_should_place_knowledge_image_between_text_segments() -> None:
    blocks = compile_message_display_blocks(
        final_text="第一段 [IMG-0] 第二段",
        kb_images={"0": "/api/v1/assets/proxy/ragflow/img-0"},
        result_events=[],
    )

    assert blocks == [
        {"type": "markdown", "data": {"text": "第一段 "}},
        {
            "type": "image",
            "data": {
                "url": "/api/v1/assets/proxy/ragflow/img-0",
                "alt": "知识库图片",
                "source": "knowledge",
            },
        },
        {"type": "markdown", "data": {"text": " 第二段"}},
    ]


def test_compile_message_display_blocks_should_sort_result_events_by_sequence_number() -> None:
    blocks = compile_message_display_blocks(
        final_text="结果如下",
        kb_images={},
        result_events=[
            {
                "data_type": "todo_list",
                "data": {"todos": [{"title": "later"}]},
                "sequence_number": 2,
                "message": "待办",
            },
            {
                "data_type": "sql_result",
                "data": {"rows": [{"name": "earlier"}], "columns": ["name"]},
                "sequence_number": 1,
                "message": "表格",
            },
        ],
    )

    assert [block["type"] for block in blocks] == ["markdown", "sql_result", "todo_list"]
    assert blocks[1]["data"]["rows"][0]["name"] == "earlier"


def test_compile_message_display_blocks_should_keep_unknown_result_as_fallback() -> None:
    blocks = compile_message_display_blocks(
        final_text="有未知结果",
        kb_images={},
        result_events=[
            {
                "data_type": "strange_card",
                "data": {"foo": "bar"},
                "message": "未知结构",
                "sequence_number": 0,
            }
        ],
    )

    assert blocks[-1]["type"] == "fallback_result"
    assert blocks[-1]["data"]["data_type"] == "strange_card"


def test_compile_message_display_blocks_should_keep_unresolved_placeholder_as_text() -> None:
    blocks = compile_message_display_blocks(
        final_text="第一段 [IMG-9] 第二段",
        kb_images={"0": "/api/v1/assets/proxy/ragflow/img-0"},
        result_events=[],
    )

    assert blocks == [{"type": "markdown", "data": {"text": "第一段 [IMG-9] 第二段"}}]


def test_compile_message_display_blocks_should_preserve_repeated_knowledge_image_references() -> None:
    blocks = compile_message_display_blocks(
        final_text="第一段 [IMG-0] 第二段 [IMG-0] 第三段",
        kb_images={"0": "/api/v1/assets/proxy/ragflow/img-0"},
        result_events=[],
    )

    assert [block["type"] for block in blocks] == ["markdown", "image", "markdown", "image", "markdown"]


def test_compile_message_display_blocks_should_replace_known_placeholder_without_dropping_unknown_one() -> None:
    blocks = compile_message_display_blocks(
        final_text="第一段 [IMG-0] 第二段 [IMG-9] 第三段",
        kb_images={"0": "/api/v1/assets/proxy/ragflow/img-0"},
        result_events=[],
    )

    assert blocks == [
        {"type": "markdown", "data": {"text": "第一段 "}},
        {
            "type": "image",
            "data": {
                "url": "/api/v1/assets/proxy/ragflow/img-0",
                "alt": "知识库图片",
                "source": "knowledge",
            },
        },
        {"type": "markdown", "data": {"text": " 第二段 [IMG-9] 第三段"}},
    ]
