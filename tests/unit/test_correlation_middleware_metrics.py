"""关联 ID 中间件的分钟桶埋点测试。"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from app.core.middlewares.correlation import CorrelationIdMiddleware


class _WriterStub:
    def __init__(self) -> None:
        self.calls: list[dict[str, float | int | str]] = []

    def record_request(self, *, path: str, status_code: int, duration_ms: float, recorded_at=None) -> bool:
        self.calls.append(
            {
                "path": path,
                "status_code": status_code,
                "duration_ms": duration_ms,
            }
        )
        return True


def test_correlation_middleware_records_api_request_into_runtime_writer(monkeypatch) -> None:
    """API 请求经过中间件后应进入分钟桶写入器。"""

    from app.services import runtime_request_metrics as metrics_module

    writer = _WriterStub()
    monkeypatch.setattr(metrics_module, "runtime_metric_bucket_writer", writer)

    app = FastAPI()
    app.add_middleware(CorrelationIdMiddleware)

    @app.get("/api/v1/chat/stream")
    async def chat_stream() -> JSONResponse:
        return JSONResponse({"ok": True})

    client = TestClient(app)
    response = client.get("/api/v1/chat/stream")

    assert response.status_code == 200
    assert len(writer.calls) == 1
    assert writer.calls[0]["path"] == "/api/v1/chat/stream"
    assert writer.calls[0]["status_code"] == 200
    assert writer.calls[0]["duration_ms"] >= 0


def test_correlation_middleware_skips_non_api_request_metrics(monkeypatch) -> None:
    """非 API 路径不应写入分钟桶。"""

    from app.services import runtime_request_metrics as metrics_module

    writer = _WriterStub()
    monkeypatch.setattr(metrics_module, "runtime_metric_bucket_writer", writer)

    app = FastAPI()
    app.add_middleware(CorrelationIdMiddleware)

    @app.get("/")
    async def homepage() -> JSONResponse:
        return JSONResponse({"ok": True})

    client = TestClient(app)
    response = client.get("/")

    assert response.status_code == 200
    assert writer.calls == []
