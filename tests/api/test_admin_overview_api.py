"""管理后台总览 API 测试。"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_admin_user
from app.api.v1.endpoints.admin_overview_api import get_admin_overview_service
from app.main import app


client = TestClient(app)


class _OverviewServiceStub:
    """总览服务桩。"""

    def __init__(self, *, snapshot: dict[str, Any] | None = None, error: Exception | None = None) -> None:
        self._snapshot = snapshot or {}
        self._error = error
        self.trace_ids: list[str | None] = []

    def get_overview_snapshot(self, trace_id: str | None = None) -> dict[str, Any]:
        self.trace_ids.append(trace_id)
        if self._error is not None:
            raise self._error
        return dict(self._snapshot)


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


def test_admin_overview_summary_requires_admin_auth():
    """未登录访问应被拒绝。"""

    response = client.get("/api/v1/admin-overview/summary")
    assert response.status_code in [401, 403, 422]


def test_admin_overview_summary_returns_snapshot(admin_override):
    """管理员访问 summary 返回 canonical 快照。"""

    snapshot = {
        "snapshot_at": "2026-02-14T08:00:00Z",
        "source": "live",
        "degraded": False,
        "health_score": 91.2,
        "health_level": "healthy",
        "budget_usage_pct": 62.1,
        "request_quality": {"status": "healthy", "score": 93.1},
        "stability": {"status": "warning", "score": 78.5},
        "capacity_cost": {"status": "healthy", "score": 86.3, "budget_usage_pct": 62.1},
        "alerts": [],
        "freshness": {"status": "fresh", "score": 95.0, "expired": False},
        "module_matrix": [],
        "change_feed": [],
        "meta": {"generated_at": "2026-02-14T08:00:01Z", "trace_id": "trace-unit-001"},
    }
    service_stub = _OverviewServiceStub(snapshot=snapshot)
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
    assert body["health_score"] == 91.2
    assert body["health_level"] == "healthy"
    assert body["source"] == "live"
    assert service_stub.trace_ids == ["trace-from-header"]


def test_admin_overview_trends_returns_multi_window_payload(
    admin_override,
    monkeypatch: pytest.MonkeyPatch,
):
    """不指定窗口时返回 1h/24h 双窗口结构。"""

    from app.api.v1.endpoints import admin_overview_api as overview_api

    base_time = datetime(2026, 2, 14, 8, 0, tzinfo=timezone.utc)

    def _query_snapshots(_db, *, minutes: int):
        rows = [
            SimpleNamespace(
                snapshot_minute=base_time,
                health_score=Decimal("90.4"),
                budget_usage_pct=Decimal("62.1"),
                snapshot_payload={
                    "request_quality": {
                        "success_rate": 0.9924,
                        "error_5xx_rate": 0.0038,
                        "latency_p95_ms": 612,
                    },
                    "capacity_cost": {"qps": 39.6},
                },
            )
        ]
        if minutes == 24 * 60:
            rows = [
                SimpleNamespace(
                    snapshot_minute=base_time.replace(day=13, hour=9),
                    health_score=Decimal("81.2"),
                    budget_usage_pct=Decimal("54.0"),
                    snapshot_payload={
                        "request_quality": {
                            "success_rate": 0.983,
                            "error_5xx_rate": 0.006,
                            "latency_p95_ms": 710,
                        },
                        "capacity_cost": {"qps": 25.4},
                    },
                ),
                *rows,
            ]
        return rows

    monkeypatch.setattr(overview_api, "_query_snapshots_for_window", _query_snapshots)

    response = client.get("/api/v1/admin-overview/trends")
    assert response.status_code == 200

    body = response.json()
    assert set(body["windows"].keys()) == {"1h", "24h"}
    assert len(body["windows"]["1h"]) == 1
    assert len(body["windows"]["24h"]) == 2
    assert body["windows"]["1h"][0]["qps"] == 39.6
    assert body["snapshot_at"].endswith("Z")


def test_admin_overview_trends_returns_single_window_series(
    admin_override,
    monkeypatch: pytest.MonkeyPatch,
):
    """指定窗口时返回单窗口结构。"""

    from app.api.v1.endpoints import admin_overview_api as overview_api

    base_time = datetime(2026, 2, 14, 8, 0, tzinfo=timezone.utc)

    def _query_snapshots(_db, *, minutes: int):
        assert minutes == 60
        return [
            SimpleNamespace(
                snapshot_minute=base_time,
                health_score=Decimal("90.4"),
                budget_usage_pct=Decimal("62.1"),
                snapshot_payload={"request_quality": {}, "capacity_cost": {}},
            )
        ]

    monkeypatch.setattr(overview_api, "_query_snapshots_for_window", _query_snapshots)

    response = client.get("/api/v1/admin-overview/trends?window=1h")
    assert response.status_code == 200

    body = response.json()
    assert body["window"] == "1h"
    assert len(body["points"]) == 1
    assert body["points"][0]["health_score"] == 90.4


def test_admin_overview_stream_emits_result_and_done(admin_override):
    """正常流应输出 result 与 done。"""

    service_stub = _OverviewServiceStub(
        snapshot={
            "snapshot_at": "2026-02-14T08:00:00Z",
            "source": "live",
            "degraded": False,
            "health_score": 90.4,
            "health_level": "healthy",
            "budget_usage_pct": 62.1,
            "request_quality": {"status": "healthy", "score": 93.1},
            "stability": {"status": "warning", "score": 78.5},
            "capacity_cost": {"status": "healthy", "score": 86.3},
            "alerts": [],
            "freshness": {"status": "fresh", "score": 95.0, "expired": False},
            "module_matrix": [],
            "change_feed": [],
            "meta": {"generated_at": "2026-02-14T08:00:01Z", "trace_id": "trace-stream-001"},
        }
    )
    app.dependency_overrides[get_admin_overview_service] = lambda: service_stub

    try:
        response = client.get("/api/v1/admin-overview/stream")
    finally:
        app.dependency_overrides.pop(get_admin_overview_service, None)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: result" in response.text
    assert "event: done" in response.text
    assert "snapshot_at" in response.text


def test_admin_overview_stream_emits_interrupt_on_error(admin_override):
    """实时采集异常时应输出 interrupt 与 done。"""

    service_stub = _OverviewServiceStub(error=RuntimeError("collector timeout"))
    app.dependency_overrides[get_admin_overview_service] = lambda: service_stub

    try:
        response = client.get("/api/v1/admin-overview/stream")
    finally:
        app.dependency_overrides.pop(get_admin_overview_service, None)

    assert response.status_code == 200
    assert "event: interrupt" in response.text
    assert "stream_disconnected" in response.text
    assert "event: done" in response.text
