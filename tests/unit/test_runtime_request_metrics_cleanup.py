"""总览旧链路清理断言。"""

from __future__ import annotations


def test_record_runtime_request_metric_only_writes_minute_bucket(monkeypatch) -> None:
    """请求埋点只允许进入分钟桶，不应再触碰旧内存 store。"""

    from app.services import runtime_request_metrics as metrics_module

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

    class _ExplodingLegacyStore:
        def record(self, **kwargs) -> None:
            raise AssertionError(f"legacy runtime store should not be used: {kwargs}")

    writer = _WriterStub()
    monkeypatch.setattr(metrics_module, "runtime_metric_bucket_writer", writer)
    monkeypatch.setattr(metrics_module, "runtime_request_metrics_store", _ExplodingLegacyStore(), raising=False)

    metrics_module.record_runtime_request_metric(
        path="/api/v1/chat/stream",
        status_code=200,
        duration_ms=128.5,
    )

    assert len(writer.calls) == 1
    assert writer.calls[0]["path"] == "/api/v1/chat/stream"


def test_services_package_hides_legacy_admin_overview_exports() -> None:
    """服务层出口不应继续暴露旧总览服务与旧 collector。"""

    import app.services as services

    assert "AdminOverviewService" not in services.__all__
    assert "RuntimeOverviewMetricCollector" not in services.__all__
