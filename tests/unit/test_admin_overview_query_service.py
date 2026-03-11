"""管理后台总览查询服务测试。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.models.runtime_metric_bucket import RuntimeMetricBucketMinute
from app.services.admin_overview_query_service import AdminOverviewQueryService


def _row(
    *,
    bucket_minute: datetime,
    scope: str,
    module_key: str,
    request_count: int,
    success_count: int,
    error_4xx_count: int = 0,
    error_5xx_count: int = 0,
    cost_total: str = "0",
    last_event_at: datetime | None = None,
    histogram: dict | None = None,
) -> RuntimeMetricBucketMinute:
    return RuntimeMetricBucketMinute(
        bucket_minute=bucket_minute,
        scope=scope,
        module_key=module_key,
        request_count=request_count,
        success_count=success_count,
        error_4xx_count=error_4xx_count,
        error_5xx_count=error_5xx_count,
        latency_histogram=histogram
        or {"count": request_count, "total_ms": 120.0 * request_count, "min_ms": 120.0, "max_ms": 120.0, "buckets": {"le_300": request_count}},
        cost_total=Decimal(cost_total),
        last_event_at=last_event_at or bucket_minute,
    )


def test_get_overview_snapshot_builds_v2_snapshot_from_minute_buckets() -> None:
    """当前窗口有业务与提问样本时，应返回 V2 快照。"""

    fixed_now = datetime(2026, 3, 9, 4, 0, 0, tzinfo=timezone.utc)
    bucket_minute = fixed_now.replace(second=0, microsecond=0) - timedelta(minutes=1)
    rows = [
        _row(
            bucket_minute=bucket_minute,
            scope="all_business",
            module_key="chat",
            request_count=12,
            success_count=11,
            error_5xx_count=1,
            cost_total="24.50",
            last_event_at=fixed_now - timedelta(seconds=12),
        ),
        _row(
            bucket_minute=bucket_minute,
            scope="user_question",
            module_key="chat",
            request_count=4,
            success_count=4,
            cost_total="8.00",
            last_event_at=fixed_now - timedelta(seconds=12),
            histogram={"count": 4, "total_ms": 2400.0, "min_ms": 400.0, "max_ms": 900.0, "buckets": {"le_1000": 4}},
        ),
    ]
    service = AdminOverviewQueryService(
        bucket_row_loader=lambda start_at: list(rows),
        latest_bucket_loader=lambda: rows[0],
        now_provider=lambda: fixed_now,
    )

    snapshot = service.get_overview_snapshot(trace_id="trace-v2-001")

    assert snapshot["source"] == "bucket"
    assert snapshot["degraded"] is False
    assert snapshot["source"] == "bucket"
    assert snapshot["degraded"] is False
    assert "system_status" not in snapshot
    assert "traffic_health" not in snapshot
    assert "health_score" not in snapshot
    assert "stability" not in snapshot
    assert "capacity_cost" not in snapshot
    assert "change_feed" not in snapshot
    assert snapshot["request_quality"]["status"] == "ok"
    assert snapshot["request_quality"]["request_total"] == 12
    assert snapshot["question_health"]["status"] == "ok"
    assert snapshot["question_health"]["question_total"] == 4
    assert snapshot["freshness"]["status"] == "fresh"
    assert snapshot["meta"]["trace_id"] == "trace-v2-001"


def test_get_overview_snapshot_returns_no_data_when_no_business_rows_in_window() -> None:
    """当前窗口无业务样本时，应返回 no_data，而不是误导性健康分。"""

    fixed_now = datetime(2026, 3, 9, 4, 5, 0, tzinfo=timezone.utc)
    bucket_minute = fixed_now.replace(second=0, microsecond=0) - timedelta(minutes=1)
    admin_row = _row(
        bucket_minute=bucket_minute,
        scope="admin_operation",
        module_key="admin_overview",
        request_count=3,
        success_count=3,
        last_event_at=fixed_now - timedelta(seconds=5),
    )
    service = AdminOverviewQueryService(
        bucket_row_loader=lambda start_at: [admin_row],
        latest_bucket_loader=lambda: admin_row,
        now_provider=lambda: fixed_now,
    )

    snapshot = service.get_overview_snapshot(trace_id="trace-no-data-001")

    assert snapshot["source"] == "bucket"
    assert snapshot["request_quality"]["status"] == "no_data"
    assert snapshot["question_health"]["status"] == "no_data"
    assert "system_status" not in snapshot
    assert "traffic_health" not in snapshot
    assert "health_score" not in snapshot


def test_get_overview_snapshot_degrades_to_explainable_empty_state_when_loader_failed() -> None:
    """分钟桶读取失败时应返回降级空态，而不是读旧快照表。"""

    fixed_now = datetime(2026, 3, 9, 4, 10, 0, tzinfo=timezone.utc)
    service = AdminOverviewQueryService(
        bucket_row_loader=lambda start_at: (_ for _ in ()).throw(RuntimeError("db down")),
        latest_bucket_loader=lambda: None,
        now_provider=lambda: fixed_now,
    )

    snapshot = service.get_overview_snapshot(trace_id="trace-fallback-v2")

    assert snapshot["source"] == "empty"
    assert snapshot["degraded"] is True
    assert snapshot["request_quality"]["status"] == "degraded"
    assert snapshot["question_health"]["status"] == "degraded"
    assert "system_status" not in snapshot
    assert "traffic_health" not in snapshot
    assert snapshot["alerts"][0]["code"] == "overview.bucket.unavailable"
    assert snapshot["meta"]["trace_id"] == "trace-fallback-v2"


def test_get_overview_trends_builds_points_from_same_bucket_source() -> None:
    """趋势应与 summary 共享同一套分钟桶事实源。"""

    fixed_now = datetime(2026, 3, 9, 4, 20, 0, tzinfo=timezone.utc)
    rows = [
        _row(
            bucket_minute=fixed_now.replace(minute=10, second=0, microsecond=0),
            scope="all_business",
            module_key="data",
            request_count=60,
            success_count=59,
            error_5xx_count=1,
            cost_total="10.00",
            last_event_at=fixed_now.replace(minute=10, second=50, microsecond=0),
        ),
        _row(
            bucket_minute=fixed_now.replace(minute=10, second=0, microsecond=0),
            scope="user_question",
            module_key="chat",
            request_count=12,
            success_count=12,
            cost_total="5.00",
            last_event_at=fixed_now.replace(minute=10, second=40, microsecond=0),
        ),
    ]
    service = AdminOverviewQueryService(
        bucket_row_loader=lambda start_at: list(rows),
        latest_bucket_loader=lambda: rows[0],
        now_provider=lambda: fixed_now,
    )

    trends = service.get_overview_trends(window=None)

    assert set(trends["windows"].keys()) == {"1h", "24h"}
    point = trends["windows"]["1h"][0]
    assert point["request_qps"] == 1.0
    assert point["question_qps"] == 0.2


def test_get_overview_trends_returns_degraded_empty_payload_when_loader_failed() -> None:
    """分钟桶读取失败时，trends 不应直接抛错。"""

    fixed_now = datetime(2026, 3, 9, 4, 25, 0, tzinfo=timezone.utc)
    service = AdminOverviewQueryService(
        bucket_row_loader=lambda start_at: (_ for _ in ()).throw(RuntimeError("db down")),
        latest_bucket_loader=lambda: None,
        now_provider=lambda: fixed_now,
    )

    multi = service.get_overview_trends(window=None)
    series = service.get_overview_trends(window="24h")

    assert multi["windows"] == {"1h": [], "24h": []}
    assert multi["snapshot_at"] is None
    assert series["window"] == "24h"
    assert series["status"] == "degraded"
    assert series["points"] == []
    assert series["snapshot_at"] is None


def test_get_overview_snapshot_question_health_uses_question_scope() -> None:
    """question 选择器：提问链路健康只统计 user_question 样本。"""

    fixed_now = datetime(2026, 3, 9, 4, 30, 0, tzinfo=timezone.utc)
    bucket_minute = fixed_now.replace(second=0, microsecond=0) - timedelta(minutes=1)
    rows = [
        _row(
            bucket_minute=bucket_minute,
            scope="all_business",
            module_key="chat",
            request_count=6,
            success_count=6,
            last_event_at=fixed_now - timedelta(seconds=10),
        ),
        _row(
            bucket_minute=bucket_minute,
            scope="user_question",
            module_key="chat",
            request_count=2,
            success_count=2,
            last_event_at=fixed_now - timedelta(seconds=8),
        ),
    ]
    service = AdminOverviewQueryService(
        bucket_row_loader=lambda start_at: list(rows),
        latest_bucket_loader=lambda: rows[0],
        now_provider=lambda: fixed_now,
    )

    snapshot = service.get_overview_snapshot(trace_id="trace-question-health")

    assert snapshot["question_health"]["status"] == "ok"
    assert snapshot["question_health"]["question_total"] == 2
    assert snapshot["question_health"]["question_qps"] == pytest.approx(0.0067, rel=1e-4)


def test_get_overview_snapshot_alerts_only_keep_actionable_items() -> None:
    """alerts 选择器：首页告警只保留可动作异常。"""

    fixed_now = datetime(2026, 3, 9, 4, 35, 0, tzinfo=timezone.utc)
    bucket_minute = fixed_now.replace(second=0, microsecond=0) - timedelta(minutes=1)
    rows = [
        _row(
            bucket_minute=bucket_minute,
            scope="all_business",
            module_key="chat",
            request_count=10,
            success_count=8,
            error_5xx_count=2,
            last_event_at=fixed_now - timedelta(seconds=6),
            histogram={"count": 10, "total_ms": 18000.0, "min_ms": 400.0, "max_ms": 2600.0, "buckets": {"le_3000": 10}},
        ),
    ]
    service = AdminOverviewQueryService(
        bucket_row_loader=lambda start_at: list(rows),
        latest_bucket_loader=lambda: rows[0],
        now_provider=lambda: fixed_now,
    )

    snapshot = service.get_overview_snapshot(trace_id="trace-alerts")

    assert snapshot["alerts"]
    assert snapshot["alerts"][0]["severity"] in {"warning", "critical"}
    assert all(alert["code"] != "overview.runtime.no_data" for alert in snapshot["alerts"])
