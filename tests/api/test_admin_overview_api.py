"""管理后台总览 API 测试。"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.api.deps import get_admin_user
from app.api.v1.endpoints.admin_overview_api import get_admin_overview_gateway
from app.main import app

client = TestClient(app)


class _GatewayStub:
    """总览网关桩。"""

    def __init__(self, summary: dict[str, Any], trends: dict[str, Any], raise_on_summary: bool = False) -> None:
        self._summary = summary
        self._trends = trends
        self._raise_on_summary = raise_on_summary

    def get_summary(self, trace_id: str | None = None) -> dict[str, Any]:
        if self._raise_on_summary:
            raise RuntimeError("stream service unavailable")
        payload = dict(self._summary)
        meta = dict(payload.get("meta") or {})
        meta["trace_id"] = trace_id
        payload["meta"] = meta
        return payload

    def get_trends(self, window: str, trace_id: str | None = None) -> dict[str, Any]:
        payload = dict(self._trends)
        payload["window"] = window
        meta = dict(payload.get("meta") or {})
        meta["trace_id"] = trace_id
        payload["meta"] = meta
        return payload


def _override_admin_user() -> MagicMock:
    user = MagicMock()
    user.id = 1
    user.username = "admin"
    user.role = "admin"
    return user


def _build_summary_payload() -> dict[str, Any]:
    return {
        "snapshot_at": "2026-02-13T12:00:00Z",
        "source": "live",
        "degraded": False,
        "health_score": 92.4,
        "health_level": "healthy",
        "budget_usage_pct": 63.2,
        "request_quality": {
            "status": "healthy",
            "score": 94.0,
            "request_total": 1200,
            "success_rate": 0.985,
            "error_5xx_rate": 0.006,
            "latency_p95_ms": 630,
        },
        "stability": {
            "status": "healthy",
            "score": 90.0,
            "critical_alerts": 0,
            "warning_alerts": 1,
        },
        "capacity_cost": {
            "status": "warning",
            "score": 78.5,
            "qps": 18.6,
            "cost_per_minute": 138.2,
            "budget_per_minute": 210.0,
            "budget_usage_pct": 65.8,
        },
        "alerts": [
            {
                "code": "chat.latency.warning",
                "severity": "warning",
                "message": "聊天链路 p95 抖动",
                "status": "active",
            }
        ],
        "freshness": {
            "status": "fresh",
            "score": 97.0,
            "health_level": "healthy",
            "delay_sec": 18,
            "expired": False,
        },
        "module_matrix": [
            {
                "key": "chat",
                "label": "聊天服务",
                "health_level": "healthy",
                "score": 93.0,
            }
        ],
        "change_feed": [
            {
                "id": "chg_01",
                "title": "模型路由权重更新",
                "level": "info",
                "occurred_at": "2026-02-13T11:59:00Z",
            }
        ],
        "meta": {
            "generated_at": "2026-02-13T12:00:01Z",
            "trace_id": None,
        },
    }


def _build_trends_payload() -> dict[str, Any]:
    return {
        "window": "1h",
        "interval": "1m",
        "points": [
            {
                "snapshot_at": "2026-02-13T11:58:00Z",
                "health_score": 88.2,
                "health_level": "healthy",
                "budget_usage_pct": 61.5,
                "request_total": 1100,
                "error_5xx_rate": 0.008,
                "latency_p95_ms": 690,
            },
            {
                "snapshot_at": "2026-02-13T11:59:00Z",
                "health_score": 89.1,
                "health_level": "healthy",
                "budget_usage_pct": 62.1,
                "request_total": 1120,
                "error_5xx_rate": 0.007,
                "latency_p95_ms": 665,
            },
        ],
        "generated_at": "2026-02-13T12:00:01Z",
        "meta": {
            "trace_id": None,
        },
    }


class TestAdminOverviewAuth:
    """鉴权测试。"""

    def test_summary_requires_admin_auth(self):
        response = client.get("/api/v1/admin-overview/summary")
        assert response.status_code in [401, 403, 422]


class TestAdminOverviewSummaryAndTrends:
    """summary/trends 接口测试。"""

    def test_summary_returns_snapshot_payload(self):
        stub = _GatewayStub(
            summary=_build_summary_payload(),
            trends=_build_trends_payload(),
        )
        app.dependency_overrides[get_admin_user] = _override_admin_user
        app.dependency_overrides[get_admin_overview_gateway] = lambda: stub

        try:
            response = client.get(
                "/api/v1/admin-overview/summary",
                headers={"X-Trace-Id": "trace-summary-001"},
            )
            assert response.status_code == 200
            body = response.json()
            assert body["snapshot_at"] == "2026-02-13T12:00:00Z"
            assert body["health_level"] == "healthy"
            assert body["request_quality"]["request_total"] == 1200
            assert body["meta"]["trace_id"] == "trace-summary-001"
        finally:
            app.dependency_overrides.clear()

    def test_trends_supports_24h_window(self):
        trends = _build_trends_payload()
        trends["interval"] = "1h"
        stub = _GatewayStub(summary=_build_summary_payload(), trends=trends)
        app.dependency_overrides[get_admin_user] = _override_admin_user
        app.dependency_overrides[get_admin_overview_gateway] = lambda: stub

        try:
            response = client.get(
                "/api/v1/admin-overview/trends?window=24h",
                headers={"X-Trace-Id": "trace-trends-001"},
            )
            assert response.status_code == 200
            body = response.json()
            assert body["window"] == "24h"
            assert body["interval"] == "1h"
            assert isinstance(body["points"], list)
            assert body["meta"]["trace_id"] == "trace-trends-001"
        finally:
            app.dependency_overrides.clear()

    def test_trends_rejects_invalid_window(self):
        app.dependency_overrides[get_admin_user] = _override_admin_user
        app.dependency_overrides[get_admin_overview_gateway] = lambda: _GatewayStub(
            summary=_build_summary_payload(),
            trends=_build_trends_payload(),
        )

        try:
            response = client.get("/api/v1/admin-overview/trends?window=7d")
            assert response.status_code == 422
        finally:
            app.dependency_overrides.clear()


class TestAdminOverviewStream:
    """SSE 通道测试。"""

    def test_stream_emits_result_and_done_events(self):
        stub = _GatewayStub(
            summary=_build_summary_payload(),
            trends=_build_trends_payload(),
        )
        app.dependency_overrides[get_admin_user] = _override_admin_user
        app.dependency_overrides[get_admin_overview_gateway] = lambda: stub

        try:
            response = client.get(
                "/api/v1/admin-overview/stream",
                headers={"X-Trace-Id": "trace-stream-001"},
            )
            assert response.status_code == 200
            assert "event: result" in response.text
            assert "event: done" in response.text

            data_payloads = [
                json.loads(line.removeprefix("data: "))
                for line in response.text.splitlines()
                if line.startswith("data: ")
            ]
            result_event = next(item for item in data_payloads if item["type"] == "result")
            assert "snapshot_at" in result_event["data"]
            assert isinstance(result_event["data"]["patch"], dict)
            assert result_event["data"]["trace_id"] == "trace-stream-001"

            done_event = next(item for item in data_payloads if item["type"] == "done")
            assert done_event["data"]["batch_id"]
            assert done_event["data"]["final"] is True
        finally:
            app.dependency_overrides.clear()

    def test_stream_emits_interrupt_when_summary_failed(self):
        stub = _GatewayStub(
            summary=_build_summary_payload(),
            trends=_build_trends_payload(),
            raise_on_summary=True,
        )
        app.dependency_overrides[get_admin_user] = _override_admin_user
        app.dependency_overrides[get_admin_overview_gateway] = lambda: stub

        try:
            response = client.get("/api/v1/admin-overview/stream")
            assert response.status_code == 200
            assert "event: interrupt" in response.text
            assert "event: done" in response.text

            data_payloads = [
                json.loads(line.removeprefix("data: "))
                for line in response.text.splitlines()
                if line.startswith("data: ")
            ]
            interrupt_event = next(item for item in data_payloads if item["type"] == "interrupt")
            assert interrupt_event["data"]["reason"] == "stream_degraded"
            assert interrupt_event["data"]["level"] == "warning"
            assert interrupt_event["data"]["retry_after_sec"] == 10

            done_event = next(item for item in data_payloads if item["type"] == "done")
            assert done_event["data"]["batch_id"]
            assert done_event["data"]["final"] is True
        finally:
            app.dependency_overrides.clear()
