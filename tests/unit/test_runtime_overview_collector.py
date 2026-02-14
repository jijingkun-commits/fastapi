"""运行时总览采集器测试。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.services.overview_runtime_collector import RuntimeOverviewMetricCollector
from app.services.runtime_request_metrics import RuntimeRequestMetricsStore


def test_collect_returns_observed_metrics_when_has_recent_events() -> None:
    """有流量时应返回可观测指标与模块矩阵。"""

    fixed_now = datetime(2026, 2, 14, 10, 0, 0, tzinfo=timezone.utc)
    store = RuntimeRequestMetricsStore(now_provider=lambda: fixed_now)

    store.record(
        path="/api/v1/chat/completions",
        status_code=200,
        duration_ms=420,
        recorded_at=fixed_now - timedelta(seconds=90),
    )
    store.record(
        path="/api/v1/chat/completions",
        status_code=502,
        duration_ms=1820,
        recorded_at=fixed_now - timedelta(seconds=40),
    )
    store.record(
        path="/api/v1/data-admin/metrics/stats",
        status_code=200,
        duration_ms=660,
        recorded_at=fixed_now - timedelta(seconds=20),
    )

    collector = RuntimeOverviewMetricCollector(store=store)
    snapshot = collector.collect()

    assert snapshot["request_total"] == 3
    assert snapshot["request_success"] == 2
    assert snapshot["request_5xx"] == 1
    assert snapshot["qps"] > 0
    assert snapshot["latency_p95_ms"] is not None
    assert snapshot["budget_per_minute"] >= snapshot["cost_per_minute"]
    assert len(snapshot["modules"]) == 2
    assert any(item["key"] == "chat" for item in snapshot["modules"])
    assert any(item["key"] == "data" for item in snapshot["modules"])


def test_collect_returns_no_traffic_hint_when_window_is_empty() -> None:
    """无流量时应返回提示性告警，避免全空卡片。"""

    fixed_now = datetime(2026, 2, 14, 10, 5, 0, tzinfo=timezone.utc)
    store = RuntimeRequestMetricsStore(now_provider=lambda: fixed_now)

    collector = RuntimeOverviewMetricCollector(store=store)
    snapshot = collector.collect()

    assert snapshot["snapshot_at"].endswith("Z")
    assert "request_total" not in snapshot
    assert snapshot["modules"] == []
    assert len(snapshot["alerts"]) == 1
    assert snapshot["alerts"][0]["code"] == "overview.runtime.no_traffic"

