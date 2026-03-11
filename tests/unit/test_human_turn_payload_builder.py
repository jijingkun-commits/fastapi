from app.services.chat_input_builder import build_human_turn_payload


IMAGE_ATTACHMENT = {
    "name": "invoice.png",
    "url": "/api/v1/assets/invoice.png",
    "mime_type": "image/png",
    "size": 2048,
    "object_key": "obj-image",
}

FILE_ATTACHMENT = {
    "name": "e2e-note.txt",
    "url": "/api/v1/assets/e2e-note.txt",
    "mime_type": "text/plain",
    "size": 12,
    "object_key": "obj-note",
}


def test_build_human_turn_payload_without_attachments_keeps_plain_text() -> None:
    payload = build_human_turn_payload("你好")
    assert payload.model_input == "你好"
    assert payload.display_content == "你好"
    assert payload.title_text == "你好"
    assert payload.attachment_manifest == []
    assert payload.lightweight_probe == []
    assert payload.metadata["attachment_count"] == 0


def test_build_human_turn_payload_renders_image_and_file_for_display() -> None:
    payload = build_human_turn_payload("帮我看下", [IMAGE_ATTACHMENT, FILE_ATTACHMENT])
    assert payload.model_input == "帮我看下"
    assert payload.display_content == (
        "帮我看下\n\n"
        "![invoice.png](/api/v1/assets/invoice.png)\n"
        "- [e2e-note.txt](/api/v1/assets/e2e-note.txt)"
    )
    assert payload.title_text == "帮我看下"
    assert payload.attachment_manifest[0]["attachment_id"] == "obj-image"
    assert payload.attachment_manifest[1]["attachment_id"] == "obj-note"
    assert payload.lightweight_probe[0]["vision_hint"] == "analyze_image"
    assert payload.metadata["attachment_count"] == 2
    assert payload.metadata["attachment_names"] == ["invoice.png", "e2e-note.txt"]


def test_build_human_turn_payload_with_attachment_only_uses_attachment_name_as_title() -> None:
    payload = build_human_turn_payload("", [FILE_ATTACHMENT])
    assert payload.model_input == ""
    assert payload.display_content == "- [e2e-note.txt](/api/v1/assets/e2e-note.txt)"
    assert payload.title_text == "e2e-note.txt"
    assert payload.metadata["attachment_count"] == 1
