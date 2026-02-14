"""管理后台总览聚合服务测试。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Mapping

from app.services.admin_overview_service import AdminOverviewService
from app.services.ops_snapshot_service import StoredOpsSnapshot


class _CollectorStub:
    """采集器桩。"""

    def __init__(self, payload: Mapping[str, Any] | None = None, error: Exception | None = None) -> None:
        self._payload = payload or {}
        self._error = error

    def collect(self) -> Mapping[str, Any]:
        if self._error is not None:
            raise self._error
        return dict(self._payload)


class _OpsSnapshotServiceStub:
    """快照存储服务桩。"""

    def __init__(self, latest_snapshot: StoredOpsSnapshot | None = None) -> None:
        self.latest_snapshot = latest_snapshot
        self.persist_calls: list[dict[str, Any]] = []

    def persist_snapshot(
        self,
        *,
        snapshot_at: datetime,
        health_score: float | None,
        health_level: str,
        budget_usage_pct: float | None,
        payload: Mapping[str, Any],
    ) -> bool:
        self.persist_calls.append(
            {
                "snapshot_at": snapshot_at,
                "health_score": health_score,
                "health_level": health_level,
                "budget_usage_pct": budget_usage_pct,
                "payload": dict(payload),
            }
        )
        return True

    def get_latest_snapshot(self) -> StoredOpsSnapshot | None:
        return self.latest_snapshot


def test_get_overview_snapshot_builds_live_snapshot_and_persists() -> None:
    """实时采集成功时应输出 canonical 快照并入库。"""

    fixed_now = datetime(2026, 2, 13, 12, 0, 30, tzinfo=timezone.utc)
    collector = _CollectorStub(
        {
            "snapshot_at": "2026-02-13T12:00:00Z",
            "request_total": 1000,
            "request_success": 980,
            "request_5xx": 8,
            "latency_p95_ms": 680,
            "qps": 16.7,
            "cost_per_minute": 120,
            "cost_budget_per_minute": 200,
            "data_delay_sec": 45,
            "alerts": [
                {"code": "api.latency.high", "severity": "warning", "message": "接口延迟抖动"},
                {"code": "api.timeout.info", "severity": "info", "message": "超时重试已恢复"},
            ],
            "modules": [
                {
                    "key": "chat",
                    "label": "聊天服务",
                    "error_rate": 0.002,
                    "latency_p95_ms": 620,
                    "data_delay_sec": 30,
                },
                {
                    "key": "analytics",
                    "label": "问数服务",
                    "error_rate": 0.011,
                    "latency_p95_ms": 1300,
                    "data_delay_sec": 80,
                },
            ],
            "changes": [
                {
                    "id": "chg_1",
                    "title": "路由权重调整",
                    "level": "info",
                    "occurred_at": "2026-02-13T11:58:00Z",
                }
            ],
        }
    )
    snapshot_store = _OpsSnapshotServiceStub()
    service = AdminOverviewService(
        collector=collector,
        ops_snapshot_service=snapshot_store,
        now_provider=lambda: fixed_now,
    )

    snapshot = service.get_overview_snapshot(trace_id="trace-live-001")

    assert snapshot["source"] == "live"
    assert snapshot["degraded"] is False
    assert snapshot["health_score"] is not None
    assert snapshot["health_score"] > 80
    assert snapshot["health_level"] == "healthy"

    assert snapshot["request_quality"]["success_rate"] == 0.98
    assert snapshot["capacity_cost"]["budget_usage_pct"] == 60.0
    assert snapshot["freshness"]["status"] == "fresh"

    assert len(snapshot["module_matrix"]) == 2
    assert snapshot["module_matrix"][0]["health_level"] == "healthy"
    assert snapshot["module_matrix"][1]["health_level"] in {"healthy", "warning", "critical"}
    assert snapshot["meta"]["trace_id"] == "trace-live-001"

    assert len(snapshot_store.persist_calls) == 1
    persist_call = snapshot_store.persist_calls[0]
    assert persist_call["health_score"] == snapshot["health_score"]
    assert persist_call["health_level"] == snapshot["health_level"]
    assert persist_call["budget_usage_pct"] == snapshot["budget_usage_pct"]


def test_get_overview_snapshot_with_missing_metrics_returns_unknown_not_zero() -> None:
    """缺失关键指标时应返回 unknown，而不是误填 0。"""

    fixed_now = datetime(2026, 2, 13, 13, 0, 0, tzinfo=timezone.utc)
    collector = _CollectorStub(
        {
            "snapshot_at": "2026-02-13T13:00:00Z",
            "qps": 22.5,
        }
    )
    snapshot_store = _OpsSnapshotServiceStub()
    service = AdminOverviewService(
        collector=collector,
        ops_snapshot_service=snapshot_store,
        now_provider=lambda: fixed_now,
    )

    snapshot = service.get_overview_snapshot(trace_id="trace-unknown-001")

    assert snapshot["health_score"] is None
    assert snapshot["health_level"] == "unknown"

    assert snapshot["request_quality"]["status"] == "unknown"
    assert snapshot["request_quality"]["success_rate"] is None
    assert snapshot["request_quality"]["error_5xx_rate"] is None

    assert snapshot["freshness"]["status"] == "unknown"
    assert snapshot["capacity_cost"]["qps"] == 22.5
    assert snapshot["capacity_cost"]["budget_usage_pct"] is None

    assert len(snapshot_store.persist_calls) == 1
    assert snapshot_store.persist_calls[0]["health_score"] is None


def test_get_overview_snapshot_fallbacks_to_latest_snapshot_when_collector_failed() -> None:
    """采集失败时应降级到最近快照，并标记过期状态。"""

    fixed_now = datetime(2026, 2, 13, 14, 0, 0, tzinfo=timezone.utc)
    latest_snapshot = StoredOpsSnapshot(
        snapshot_at=fixed_now - timedelta(minutes=8),
        health_score=91.25,
        health_level="healthy",
        budget_usage_pct=44.3,
        payload={
            "snapshot_at": "2026-02-13T13:52:00Z",
            "health_score": 91.25,
            "health_level": "healthy",
            "budget_usage_pct": 44.3,
            "request_quality": {"status": "healthy", "score": 95.0},
            "capacity_cost": {"status": "healthy", "score": 93.0, "budget_usage_pct": 44.3},
            "alerts": [{"code": "existing", "severity": "info", "message": "历史告警"}],
            "module_matrix": [{"key": "chat", "health_level": "healthy", "score": 92.0}],
            "meta": {"generated_at": "2026-02-13T13:52:01Z", "trace_id": "old-trace"},
        },
    )

    collector = _CollectorStub(error=RuntimeError("collector timeout"))
    snapshot_store = _OpsSnapshotServiceStub(latest_snapshot=latest_snapshot)
    service = AdminOverviewService(
        collector=collector,
        ops_snapshot_service=snapshot_store,
        now_provider=lambda: fixed_now,
    )

    snapshot = service.get_overview_snapshot(trace_id="trace-fallback-001")

    assert snapshot["source"] == "fallback_snapshot"
    assert snapshot["degraded"] is True
    assert snapshot["health_score"] == 91.25
    assert snapshot["health_level"] == "healthy"

    assert snapshot["freshness"]["status"] == "expired"
    assert snapshot["freshness"]["expired"] is True
    assert snapshot["freshness"]["delay_sec"] >= 480

    assert any(alert["code"] == "overview.snapshot.fallback" for alert in snapshot["alerts"])
    assert snapshot["meta"]["trace_id"] == "trace-fallback-001"

    assert snapshot_store.persist_calls == []


def test_get_overview_snapshot_returns_empty_snapshot_when_no_fallback_available() -> None:
    """实时失败且无历史快照时应返回空快照结构。"""

    fixed_now = datetime(2026, 2, 13, 15, 0, 0, tzinfo=timezone.utc)
    collector = _CollectorStub(error=RuntimeError("source down"))
    snapshot_store = _OpsSnapshotServiceStub(latest_snapshot=None)
    service = AdminOverviewService(
        collector=collector,
        ops_snapshot_service=snapshot_store,
        now_provider=lambda: fixed_now,
    )

    snapshot = service.get_overview_snapshot(trace_id="trace-empty-001")

    assert snapshot["source"] == "empty"
    assert snapshot["degraded"] is True
    assert snapshot["health_score"] is None
    assert snapshot["health_level"] == "unknown"
    assert snapshot["freshness"]["status"] == "unknown"
    assert snapshot["alerts"][0]["code"] == "overview.snapshot.unavailable"
    assert snapshot["meta"]["trace_id"] == "trace-empty-001"

    assert snapshot_store.persist_calls == []
