"""管理后台总览 API 测试。"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_admin_user
from app.api.v1.endpoints.admin_overview_api import get_admin_overview_service
from app.main import app


client = TestClient(app)


class _OverviewQueryServiceStub:
    """总览查询服务桩。"""

    def __init__(
        self,
        *,
        snapshot: dict[str, Any] | None = None,
        trends: dict[str, Any] | None = None,
        series: dict[str, Any] | None = None,
        error: Exception | None = None,
    ) -> None:
        self._snapshot = snapshot or {}
        self._trends = trends or {}
        self._series = series or {}
        self._error = error
        self.trace_ids: list[str | None] = []
        self.window_calls: list[str | None] = []

    def get_overview_snapshot(self, trace_id: str | None = None) -> dict[str, Any]:
        self.trace_ids.append(trace_id)
        if self._error is not None:
            raise self._error
        return dict(self._snapshot)

    def get_overview_trends(self, *, window: str | None = None) -> dict[str, Any]:
        self.window_calls.append(window)
        if self._error is not None:
            raise self._error
        if window is None:
            return dict(self._trends)
        return dict(self._series)


@pytest.fixture()
def admin_override():
    """覆盖管理员依赖。"""

    app.dependency_overrides[get_admin_user] = lambda: SimpleNamespace(
        id=1,
        username="admin",
        role="admin",
        is_active=True,
    )
    yield
    app.dependency_overrides.clear()


def test_admin_overview_summary_requires_admin_auth() -> None:
    """未登录访问应被拒绝。"""

    response = client.get("/api/v1/admin-overview/summary")
    assert response.status_code in [401, 403, 422]


def test_admin_overview_summary_returns_v2_snapshot(admin_override) -> None:
    """管理员访问 summary 返回 V2 canonical 快照。"""

    snapshot = {
        "snapshot_at": "2026-03-09T04:00:00Z",
        "source": "bucket",
        "degraded": False,
        "system_status": {"status": "ok", "health_level": "healthy"},
        "traffic_health": {"status": "ok", "sample_count": 12},
        "health_score": 92.5,
        "health_level": "healthy",
        "request_quality": {"status": "ok", "request_total": 12},
        "question_activity": {"status": "ok", "question_total": 4},
        "stability": {"status": "ok", "score": 90.0},
        "capacity_cost": {"status": "ok", "budget_usage_pct": 24.5},
        "alerts": [],
        "freshness": {"status": "fresh", "expired": False},
        "module_matrix": [],
        "change_feed": [],
        "meta": {"generated_at": "2026-03-09T04:00:01Z", "trace_id": "trace-unit-v2"},
    }
    service_stub = _OverviewQueryServiceStub(snapshot=snapshot)
    app.dependency_overrides[get_admin_overview_service] = lambda: service_stub

    try:
        response = client.get(
            "/api/v1/admin-overview/summary",
            headers={"X-Request-Id": "trace-from-header"},
        )
    finally:
        app.dependency_overrides.pop(get_admin_overview_service, None)

    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "bucket"
    assert body["system_status"]["status"] == "ok"
    assert body["request_quality"]["request_total"] == 12
    assert body["question_activity"]["question_total"] == 4
    assert service_stub.trace_ids == ["trace-from-header"]


def test_admin_overview_trends_returns_multi_window_payload(admin_override) -> None:
    """不指定窗口时返回 1h/24h 双窗口结构。"""

    trends = {
        "windows": {
            "1h": [{"timestamp": "2026-03-09T03:59:00Z", "request_qps": 1.0, "question_qps": 0.2}],
            "24h": [{"timestamp": "2026-03-09T03:59:00Z", "request_qps": 1.0, "question_qps": 0.2}],
        },
        "snapshot_at": "2026-03-09T04:00:00Z",
    }
    service_stub = _OverviewQueryServiceStub(trends=trends)
    app.dependency_overrides[get_admin_overview_service] = lambda: service_stub

    try:
        response = client.get("/api/v1/admin-overview/trends")
    finally:
        app.dependency_overrides.pop(get_admin_overview_service, None)

    assert response.status_code == 200
    body = response.json()
    assert set(body["windows"].keys()) == {"1h", "24h"}
    assert body["windows"]["1h"][0]["request_qps"] == 1.0
    assert service_stub.window_calls == [None]


def test_admin_overview_trends_returns_single_window_series(admin_override) -> None:
    """指定窗口时返回单窗口序列。"""

    series = {
        "window": "24h",
        "status": "ok",
        "points": [{"timestamp": "2026-03-09T03:59:00Z", "request_qps": 1.0, "question_qps": 0.2}],
        "snapshot_at": "2026-03-09T04:00:00Z",
    }
    service_stub = _OverviewQueryServiceStub(series=series)
    app.dependency_overrides[get_admin_overview_service] = lambda: service_stub

    try:
        response = client.get("/api/v1/admin-overview/trends?window=24h")
    finally:
        app.dependency_overrides.pop(get_admin_overview_service, None)

    assert response.status_code == 200
    body = response.json()
    assert body["window"] == "24h"
    assert body["status"] == "ok"
    assert len(body["points"]) == 1
    assert service_stub.window_calls == ["24h"]


async def _collect_stream_payload(response) -> str:
    chunks: list[str] = []
    async for chunk in response.body_iterator:
        chunks.append(chunk if isinstance(chunk, str) else chunk.decode("utf-8"))
    return "".join(chunks)


def test_admin_overview_stream_pushes_multiple_results(admin_override, monkeypatch: pytest.MonkeyPatch) -> None:
    """SSE 正常链路应持续推送 result 事件。"""

    snapshots = iter(
        [
            {
                "snapshot_at": "2026-03-09T04:00:00Z",
                "source": "bucket",
                "degraded": False,
                "system_status": {"status": "ok"},
            },
            {
                "snapshot_at": "2026-03-09T04:00:10Z",
                "source": "bucket",
                "degraded": False,
                "system_status": {"status": "ok"},
            },
        ]
    )

    class _StreamingStub(_OverviewQueryServiceStub):
        def get_overview_snapshot(self, trace_id: str | None = None) -> dict[str, Any]:
            self.trace_ids.append(trace_id)
            return next(snapshots)

    class _FakeRequest:
        def __init__(self) -> None:
            self.headers = {"X-Request-Id": "trace-stream-header"}
            self.state = SimpleNamespace(correlation_id=None)
            self._flags = iter([False, False, False, False, True])

        async def is_disconnected(self) -> bool:
            return next(self._flags)

    service_stub = _StreamingStub()

    from app.api.v1.endpoints import admin_overview_api as overview_api

    async def _fake_sleep(seconds: float) -> None:
        return None

    monkeypatch.setattr(overview_api.asyncio, "sleep", _fake_sleep)

    response = asyncio.run(overview_api.stream_admin_overview(_FakeRequest(), service_stub))
    payload = asyncio.run(_collect_stream_payload(response))

    assert "event: result" in payload
    assert '"snapshot_at": "2026-03-09T04:00:00Z"' in payload
    assert '"snapshot_at": "2026-03-09T04:00:10Z"' in payload


def test_admin_overview_stream_emits_interrupt_on_error(admin_override) -> None:
    """SSE 推送失败时应发出 interrupt 事件。"""

    class _FakeRequest:
        def __init__(self) -> None:
            self.headers = {"X-Request-Id": "trace-stream-header"}
            self.state = SimpleNamespace(correlation_id=None)
            self._flags = iter([False, True])

        async def is_disconnected(self) -> bool:
            return next(self._flags)

    from app.api.v1.endpoints import admin_overview_api as overview_api

    service_stub = _OverviewQueryServiceStub(error=RuntimeError("boom"))
    response = asyncio.run(overview_api.stream_admin_overview(_FakeRequest(), service_stub))
    payload = asyncio.run(_collect_stream_payload(response))

    assert "event: interrupt" in payload
    assert '"reason": "stream_disconnected"' in payload
