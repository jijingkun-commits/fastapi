from unittest.mock import patch

from app.ai.tools.chatTools import _emit_fig_image_result_event


def test_emit_fig_image_result_event_uses_shared_payload_builder() -> None:
    writer = object()

    with patch("langgraph.config.get_stream_writer", return_value=writer), patch(
        "app.ai.events.emit_result"
    ) as mock_emit_result:
        _emit_fig_image_result_event("/api/v1/assets/proxy/demo/chart.png")

    mock_emit_result.assert_called_once_with(
        writer,
        data_type="image",
        data={"url": "/api/v1/assets/proxy/demo/chart.png"},
        message="图表已生成",
        node="fig_inter",
    )
