"""取消后恢复流测试骨架（中文注释）。

本文件用于 C01 红灯阶段，锁定 resume-after-cancel 的最小契约。
"""

from __future__ import annotations

import inspect

from app.api.v1.endpoints.chat_api import ResumeRequest
from app.schemas.chat import ChatRequest
from app.services.chat_service import sse_resume_stream


def test_chat_request_should_expose_run_id_field() -> None:
    """ChatRequest 需携带 run_id 以支持取消/恢复链路关联。"""

    assert "run_id" in ChatRequest.model_fields, "ChatRequest 缺少 run_id 字段"


def test_resume_request_should_expose_run_id_field() -> None:
    """ResumeRequest 需携带 run_id 以恢复指定被取消运行。"""

    assert "run_id" in ResumeRequest.model_fields, "ResumeRequest 缺少 run_id 字段"


def test_sse_resume_stream_signature_should_accept_run_id() -> None:
    """sse_resume_stream 应显式接收 run_id 参数。"""

    signature = inspect.signature(sse_resume_stream)
    assert "run_id" in signature.parameters, "sse_resume_stream 缺少 run_id 参数"
