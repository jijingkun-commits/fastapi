"""Vision 工具 API 协议分支单元测试。"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock, patch

import httpx

from app.ai.tools import vision_tool


@patch("app.ai.tools.vision_tool.httpx.post")
@patch("app.services.asset_service.get_asset_service")
@patch("app.ai.tools.vision_tool._get_vision_model_config")
def test_call_vision_model_uses_responses_endpoint_when_enabled(
    mock_get_model_config: Mock,
    mock_get_asset_service: Mock,
    mock_httpx_post: Mock,
):
    """wire_api/use_responses_api 启用时应调用 /responses。"""

    mock_get_model_config.return_value = SimpleNamespace(
        model_code="gpt-5.2",
        api_key="test-key",
        max_output_tokens=256,
        extra_config={
            "use_responses_api": True,
            "wire_api": "responses",
            "send_x_api_key": True,
            "default_headers": {"User-Agent": "Mozilla/5.0"},
            "request_params": {"store": False},
        },
        base_url="https://gmn.chuangzuoli.com/v1",
    )

    minio_resp = Mock()
    minio_resp.read.return_value = b"fake-image-bytes"
    mock_asset_service = SimpleNamespace(client=Mock(get_object=Mock(return_value=minio_resp)))
    mock_get_asset_service.return_value = mock_asset_service

    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {"output_text": "这是西安"}
    mock_httpx_post.return_value = response

    result = vision_tool._call_vision_model(
        "/api/v1/assets/2/uploads/images/ac9b0861ece1.png",
        "这是哪个城市？",
    )

    assert result == "这是西安"
    assert mock_httpx_post.call_args.args[0] == "https://gmn.chuangzuoli.com/v1/responses"

    sent_payload = mock_httpx_post.call_args.kwargs["json"]
    assert sent_payload["model"] == "gpt-5.2"
    assert sent_payload["input"][0]["content"][0]["type"] == "input_image"
    assert sent_payload["input"][0]["content"][1]["type"] == "input_text"
    assert sent_payload["store"] is False

    sent_headers = mock_httpx_post.call_args.kwargs["headers"]
    assert sent_headers["X-API-Key"] == "test-key"
    assert sent_headers["User-Agent"] == "Mozilla/5.0"


@patch("app.ai.tools.vision_tool.httpx.post")
@patch("app.ai.tools.vision_tool._get_vision_model_config")
def test_call_vision_model_uses_chat_completions_by_default(
    mock_get_model_config: Mock,
    mock_httpx_post: Mock,
):
    """未启用 responses 时应继续走 /chat/completions。"""

    mock_get_model_config.return_value = SimpleNamespace(
        model_code="qwen3-vl-flash-2026-01-22",
        api_key="test-key",
        max_output_tokens=512,
        extra_config=None,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )

    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "choices": [{"message": {"content": "这是贵阳"}}],
    }
    mock_httpx_post.return_value = response

    result = vision_tool._call_vision_model("https://example.com/city.png", "识别城市")

    assert result == "这是贵阳"
    assert (
        mock_httpx_post.call_args.args[0]
        == "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    )

    sent_payload = mock_httpx_post.call_args.kwargs["json"]
    assert sent_payload["messages"][0]["content"][0]["type"] == "image_url"
    assert sent_payload["messages"][0]["content"][1]["type"] == "text"


def test_analyze_image_returns_endpoint_on_http_status_error():
    """Vision 接口报错时，返回信息应明确是接口问题而非图片路径问题。"""

    request = httpx.Request("POST", "https://gmn.chuangzuoli.com/v1/chat/completions")
    response = httpx.Response(404, request=request)

    with patch("app.ai.tools.vision_tool.is_vision_configured", return_value=True), patch(
        "app.ai.tools.vision_tool._call_vision_model",
        side_effect=httpx.HTTPStatusError("404", request=request, response=response),
    ):
        result = vision_tool.analyze_image.invoke({"image_url": "/api/v1/assets/2/uploads/images/a.png"})

    assert "Vision 接口 HTTP 404" in result
    assert "endpoint=https://gmn.chuangzuoli.com/v1/chat/completions" in result

