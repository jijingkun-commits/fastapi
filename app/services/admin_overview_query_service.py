"""管理后台总览 V2 查询服务。"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Callable, Iterable, Mapping, Sequence

from app.db.session import get_db_context
from app.models import RuntimeMetricBucketMinute
from app.observability.module_registry import get_observed_module_label

logger = logging.getLogger(__name__)


WINDOW_MINUTES: dict[str, int] = {
    "1h": 60,
    "24h": 24 * 60,
}
WINDOW_SECONDS = 300
DATA_FRESH_WARNING_SEC = 120.0
DATA_FRESH_CRITICAL_SEC = 300.0
LATENCY_WARNING_MS = 900.0
LATENCY_CRITICAL_MS = 2200.0
ERROR_5XX_WARNING_RATE = 0.01
ERROR_5XX_CRITICAL_RATE = 0.03
BUDGET_PER_MINUTE = Decimal("100")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _to_iso8601(value: datetime | None) -> str | None:
    if value is None:
        return None
    return _as_utc(value).isoformat().replace("+00:00", "Z")


def _to_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str) and value.strip():
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _round_optional(value: float | None, digits: int = 2) -> float | None:
    if value is None:
        return None
    return round(value, digits)


def _safe_div(numerator: float | int | Decimal | None, denominator: float | int | Decimal | None) -> float | None:
    if numerator is None or denominator is None:
        return None
    denominator_float = float(denominator)
    if denominator_float <= 0:
        return None
    return float(numerator) / denominator_float


def _score_to_level(score: float | None) -> str:
    if score is None:
        return "unknown"
    if score >= 85:
        return "healthy"
    if score >= 70:
        return "warning"
    return "critical"


def _combine_weighted_scores(weighted_scores: Sequence[tuple[float | None, float]]) -> float | None:
    valid_items = [(score, weight) for score, weight in weighted_scores if score is not None]
    if not valid_items:
        return None
    total_weight = sum(weight for _, weight in valid_items)
    if total_weight <= 0:
        return None
    return sum(score * weight for score, weight in valid_items) / total_weight


def _bucket_minute_floor(value: datetime) -> datetime:
    return _as_utc(value).replace(second=0, microsecond=0)


@dataclass(frozen=True)
class _AggregateStats:
    request_count: int
    success_count: int
    error_4xx_count: int
    error_5xx_count: int
    cost_total: Decimal
    latest_event_at: datetime | None
    latency_histogram: dict[str, Any]


def _empty_stats() -> _AggregateStats:
    return _AggregateStats(
        request_count=0,
        success_count=0,
        error_4xx_count=0,
        error_5xx_count=0,
        cost_total=Decimal("0"),
        latest_event_at=None,
        latency_histogram={"count": 0, "total_ms": 0.0, "min_ms": 0.0, "max_ms": 0.0, "buckets": {}},
    )


def _merge_histograms(histograms: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    count = 0
    total_ms = 0.0
    min_ms: float | None = None
    max_ms: float | None = None
    buckets: dict[str, int] = defaultdict(int)

    for histogram in histograms:
        if not isinstance(histogram, Mapping):
            continue
        count += int(histogram.get("count") or 0)
        total_ms += float(histogram.get("total_ms") or 0.0)
        candidate_min = _to_float(histogram.get("min_ms"))
        candidate_max = _to_float(histogram.get("max_ms"))
        if candidate_min is not None:
            min_ms = candidate_min if min_ms is None else min(min_ms, candidate_min)
        if candidate_max is not None:
            max_ms = candidate_max if max_ms is None else max(max_ms, candidate_max)
        raw_buckets = histogram.get("buckets")
        if isinstance(raw_buckets, Mapping):
            for key, value in raw_buckets.items():
                buckets[str(key)] += int(value)

    return {
        "count": count,
        "total_ms": round(total_ms, 4),
        "min_ms": round(min_ms or 0.0, 4),
        "max_ms": round(max_ms or 0.0, 4),
        "buckets": dict(buckets),
    }


def _aggregate_rows(rows: Iterable[RuntimeMetricBucketMinute]) -> _AggregateStats:
    bucket_rows = list(rows)
    latest_event_at = None
    cost_total = Decimal("0")
    request_count = 0
    success_count = 0
    error_4xx_count = 0
    error_5xx_count = 0

    for row in bucket_rows:
        request_count += int(row.request_count or 0)
        success_count += int(row.success_count or 0)
        error_4xx_count += int(row.error_4xx_count or 0)
        error_5xx_count += int(row.error_5xx_count or 0)
        if row.cost_total is not None:
            cost_total += Decimal(str(row.cost_total))
        if latest_event_at is None or row.last_event_at > latest_event_at:
            latest_event_at = row.last_event_at

    return _AggregateStats(
        request_count=request_count,
        success_count=success_count,
        error_4xx_count=error_4xx_count,
        error_5xx_count=error_5xx_count,
        cost_total=cost_total,
        latest_event_at=latest_event_at,
        latency_histogram=_merge_histograms(row.latency_histogram for row in bucket_rows),
    )


def _approximate_p95_ms(histogram: Mapping[str, Any]) -> float | None:
    total_count = int(histogram.get("count") or 0)
    if total_count <= 0:
        return None

    target = max(1, int(total_count * 0.95 + 0.9999))
    buckets = histogram.get("buckets") if isinstance(histogram.get("buckets"), Mapping) else {}
    cumulative = 0
    ordered = (
        ("le_100", 100.0),
        ("le_300", 300.0),
        ("le_1000", 1000.0),
        ("gt_1000", max(1000.0, float(histogram.get("max_ms") or 1000.0))),
    )
    for bucket_key, upper_bound in ordered:
        cumulative += int(buckets.get(bucket_key) or 0)
        if cumulative >= target:
            return upper_bound

    max_ms = _to_float(histogram.get("max_ms"))
    return max_ms


def _metric_status_with_samples(sample_count: int) -> str:
    return "ok" if sample_count > 0 else "no_data"


def _build_metric_meta(*, status: str, sample_count: int, latest_event_at: datetime | None, explain: str, source: str) -> dict[str, Any]:
    return {
        "status": status,
        "sample_count": sample_count,
        "watermark_at": _to_iso8601(latest_event_at),
        "data_source": source,
        "explain": explain,
    }


class AdminOverviewQueryService:
    """管理后台总览 V2 查询服务。"""

    def __init__(
        self,
        *,
        bucket_row_loader: Callable[[datetime], list[RuntimeMetricBucketMinute]] | None = None,
        latest_bucket_loader: Callable[[], RuntimeMetricBucketMinute | None] | None = None,
        now_provider: Callable[[], datetime] = _utc_now,
    ) -> None:
        self._bucket_row_loader = bucket_row_loader or self._load_bucket_rows_since
        self._latest_bucket_loader = latest_bucket_loader or self._load_latest_bucket_row
        self._now_provider = now_provider

    def _load_bucket_rows_since(self, start_at: datetime) -> list[RuntimeMetricBucketMinute]:
        bucket_start = _bucket_minute_floor(start_at)
        with get_db_context() as session:
            return (
                session.query(RuntimeMetricBucketMinute)
                .filter(RuntimeMetricBucketMinute.bucket_minute >= bucket_start)
                .order_by(RuntimeMetricBucketMinute.bucket_minute.asc())
                .all()
            )

    def _load_latest_bucket_row(self) -> RuntimeMetricBucketMinute | None:
        with get_db_context() as session:
            return (
                session.query(RuntimeMetricBucketMinute)
                .order_by(RuntimeMetricBucketMinute.last_event_at.desc())
                .first()
            )

    def get_overview_snapshot(self, trace_id: str | None = None) -> dict[str, Any]:
        now = _as_utc(self._now_provider())
        start_at = now - timedelta(seconds=WINDOW_SECONDS)
        try:
            rows = self._bucket_row_loader(start_at)
            latest_row = self._latest_bucket_loader()
        except Exception as exc:
            logger.exception("读取总览分钟桶失败")
            return self._build_degraded_snapshot(
                generated_at=now,
                trace_id=trace_id,
                fallback_reason=f"bucket_loader_error:{type(exc).__name__}",
            )

        return self._build_live_snapshot(rows=rows, latest_row=latest_row, generated_at=now, trace_id=trace_id)

    def get_overview_trends(self, *, window: str | None = None) -> dict[str, Any]:
        try:
            if window is not None:
                return self._build_trend_series(window)
            windows = {
                trend_window: self._build_trend_series(trend_window)["points"]
                for trend_window in WINDOW_MINUTES
            }
            latest_candidates = [points[-1]["timestamp"] for points in windows.values() if points]
            return {
                "windows": windows,
                "snapshot_at": latest_candidates[-1] if latest_candidates else None,
            }
        except Exception as exc:
            logger.exception("读取总览趋势分钟桶失败")
            return self._build_degraded_trends(window=window, fallback_reason=f"bucket_loader_error:{type(exc).__name__}")

    def _build_degraded_trends(self, *, window: str | None, fallback_reason: str) -> dict[str, Any]:
        if window is not None:
            return {
                "window": window,
                "status": "degraded",
                "points": [],
                "snapshot_at": None,
                "fallback_reason": fallback_reason,
            }

        return {
            "windows": {trend_window: [] for trend_window in WINDOW_MINUTES},
            "snapshot_at": None,
        }

    def _build_trend_series(self, window: str) -> dict[str, Any]:
        now = _as_utc(self._now_provider())
        minutes = WINDOW_MINUTES[window]
        rows = self._bucket_row_loader(now - timedelta(minutes=minutes))
        grouped = self._group_rows_by_minute(rows)
        points = [self._build_trend_point(bucket_minute, bucket_rows) for bucket_minute, bucket_rows in grouped]
        return {
            "window": window,
            "status": "ok" if points else "no_data",
            "points": points,
            "snapshot_at": points[-1]["timestamp"] if points else None,
        }

    def _group_rows_by_minute(self, rows: Iterable[RuntimeMetricBucketMinute]) -> list[tuple[datetime, list[RuntimeMetricBucketMinute]]]:
        grouped: dict[datetime, list[RuntimeMetricBucketMinute]] = defaultdict(list)
        for row in rows:
            grouped[_as_utc(row.bucket_minute)].append(row)
        return sorted(grouped.items(), key=lambda item: item[0])

    def _build_trend_point(self, bucket_minute: datetime, rows: Sequence[RuntimeMetricBucketMinute]) -> dict[str, Any]:
        all_business_rows = [row for row in rows if row.scope == "all_business"]
        question_rows = [row for row in rows if row.scope == "user_question"]
        all_business_stats = _aggregate_rows(all_business_rows)
        question_stats = _aggregate_rows(question_rows)
        capacity_cost = self._build_capacity_cost_card(all_business_stats, question_stats)
        request_quality = self._build_request_quality_card(all_business_stats)
        freshness = self._build_freshness_card(latest_event_at=self._latest_event_from_rows(rows), generated_at=bucket_minute + timedelta(minutes=1))
        stability = self._build_stability_card(
            alerts=self._build_alerts(request_quality=request_quality, freshness=freshness),
            module_matrix=self._build_module_matrix(all_business_rows, generated_at=bucket_minute + timedelta(minutes=1)),
        )
        health_score = self._build_health_score(request_quality=request_quality, stability=stability, capacity_cost=capacity_cost, freshness=freshness)
        return {
            "timestamp": _to_iso8601(bucket_minute),
            "health_score": health_score,
            "request_qps": _round_optional(all_business_stats.request_count / 60.0 if all_business_stats.request_count else 0.0, 2),
            "question_qps": _round_optional(question_stats.request_count / 60.0 if question_stats.request_count else 0.0, 2),
            "budget_usage_pct": capacity_cost.get("budget_usage_pct"),
        }

    def _build_live_snapshot(
        self,
        *,
        rows: Sequence[RuntimeMetricBucketMinute],
        latest_row: RuntimeMetricBucketMinute | None,
        generated_at: datetime,
        trace_id: str | None,
    ) -> dict[str, Any]:
        latest_event_at = _as_utc(latest_row.last_event_at) if latest_row is not None else None
        all_business_rows = [row for row in rows if row.scope == "all_business"]
        question_rows = [row for row in rows if row.scope == "user_question"]
        all_business_stats = _aggregate_rows(all_business_rows)
        question_stats = _aggregate_rows(question_rows)

        system_status = {
            "status": "ok",
            "health_level": "healthy",
            "watermark_at": _to_iso8601(latest_event_at),
            "data_source": "bucket",
            "explain": "聚合链路在线，正在消费分钟桶数据",
        }
        traffic_status = _metric_status_with_samples(all_business_stats.request_count)
        traffic_health = {
            **_build_metric_meta(
                status=traffic_status,
                sample_count=all_business_stats.request_count,
                latest_event_at=all_business_stats.latest_event_at,
                explain=("最近 5 分钟有业务样本" if traffic_status == "ok" else "最近 5 分钟无业务样本"),
                source="bucket",
            ),
            "window_sec": WINDOW_SECONDS,
        }
        request_quality = self._build_request_quality_card(all_business_stats)
        question_activity = self._build_question_activity_card(question_stats)
        capacity_cost = self._build_capacity_cost_card(all_business_stats, question_stats)
        freshness = self._build_freshness_card(latest_event_at=latest_event_at, generated_at=generated_at)
        module_matrix = self._build_module_matrix(all_business_rows, generated_at=generated_at)
        alerts = self._build_alerts(request_quality=request_quality, freshness=freshness)
        stability = self._build_stability_card(alerts=alerts, module_matrix=module_matrix)
        health_score = self._build_health_score(request_quality=request_quality, stability=stability, capacity_cost=capacity_cost, freshness=freshness)
        health_level = _score_to_level(health_score)

        return {
            "snapshot_at": _to_iso8601(generated_at),
            "source": "bucket",
            "degraded": False,
            "system_status": system_status,
            "traffic_health": traffic_health,
            "health_score": health_score,
            "health_level": health_level,
            "budget_usage_pct": capacity_cost.get("budget_usage_pct"),
            "request_quality": request_quality,
            "question_activity": question_activity,
            "stability": stability,
            "capacity_cost": capacity_cost,
            "alerts": alerts,
            "freshness": freshness,
            "module_matrix": module_matrix,
            "change_feed": [],
            "meta": {
                "generated_at": _to_iso8601(generated_at),
                "trace_id": trace_id,
            },
        }

    def _build_request_quality_card(self, stats: _AggregateStats) -> dict[str, Any]:
        request_total = stats.request_count
        status = _metric_status_with_samples(request_total)
        success_rate = _safe_div(stats.success_count, request_total)
        error_4xx_rate = _safe_div(stats.error_4xx_count, request_total)
        error_5xx_rate = _safe_div(stats.error_5xx_count, request_total)
        latency_p95_ms = _approximate_p95_ms(stats.latency_histogram)
        qps = request_total / WINDOW_SECONDS if request_total else 0.0

        score = None
        if status == "ok":
            success_score = 100.0 if (success_rate or 0.0) >= 0.97 else 70.0 if (success_rate or 0.0) >= 0.9 else 35.0
            error_score = 100.0 if (error_5xx_rate or 0.0) < ERROR_5XX_WARNING_RATE else 70.0 if (error_5xx_rate or 0.0) < ERROR_5XX_CRITICAL_RATE else 30.0
            latency_score = 100.0 if (latency_p95_ms or 0.0) < LATENCY_WARNING_MS else 70.0 if (latency_p95_ms or 0.0) < LATENCY_CRITICAL_MS else 30.0
            score = _round_optional(_combine_weighted_scores(((success_score, 0.5), (error_score, 0.3), (latency_score, 0.2))), 2)

        return {
            **_build_metric_meta(
                status=status,
                sample_count=request_total,
                latest_event_at=stats.latest_event_at,
                explain=("最近 5 分钟全业务请求质量可计算" if status == "ok" else "最近 5 分钟无全业务请求样本"),
                source="bucket",
            ),
            "health_level": _score_to_level(score),
            "window_sec": WINDOW_SECONDS,
            "score": score,
            "request_total": request_total,
            "success_rate": _round_optional(success_rate, 4),
            "error_4xx_rate": _round_optional(error_4xx_rate, 4),
            "error_5xx_rate": _round_optional(error_5xx_rate, 4),
            "latency_p95_ms": _round_optional(latency_p95_ms, 2),
            "qps": _round_optional(qps, 4),
        }

    def _build_question_activity_card(self, stats: _AggregateStats) -> dict[str, Any]:
        question_total = stats.request_count
        status = _metric_status_with_samples(question_total)
        success_rate = _safe_div(stats.success_count, question_total)
        latency_p95_ms = _approximate_p95_ms(stats.latency_histogram)
        qps = question_total / WINDOW_SECONDS if question_total else 0.0
        score = None
        if status == "ok":
            success_score = 100.0 if (success_rate or 0.0) >= 0.97 else 70.0 if (success_rate or 0.0) >= 0.9 else 35.0
            latency_score = 100.0 if (latency_p95_ms or 0.0) < LATENCY_WARNING_MS else 70.0 if (latency_p95_ms or 0.0) < LATENCY_CRITICAL_MS else 30.0
            score = _round_optional(_combine_weighted_scores(((success_score, 0.7), (latency_score, 0.3))), 2)

        return {
            **_build_metric_meta(
                status=status,
                sample_count=question_total,
                latest_event_at=stats.latest_event_at,
                explain=("最近 5 分钟用户提问链路可计算" if status == "ok" else "最近 5 分钟无用户提问样本"),
                source="bucket",
            ),
            "health_level": _score_to_level(score),
            "window_sec": WINDOW_SECONDS,
            "score": score,
            "question_total": question_total,
            "question_success_rate": _round_optional(success_rate, 4),
            "question_latency_p95_ms": _round_optional(latency_p95_ms, 2),
            "question_qps": _round_optional(qps, 4),
            "stream_interrupt_rate": None,
        }

    def _build_capacity_cost_card(self, all_business_stats: _AggregateStats, question_stats: _AggregateStats) -> dict[str, Any]:
        sample_count = all_business_stats.request_count
        status = _metric_status_with_samples(sample_count)
        request_qps = all_business_stats.request_count / WINDOW_SECONDS if all_business_stats.request_count else 0.0
        question_qps = question_stats.request_count / WINDOW_SECONDS if question_stats.request_count else 0.0
        cost_per_minute = float(all_business_stats.cost_total) / (WINDOW_SECONDS / 60.0) if sample_count else 0.0
        budget_usage_pct = (cost_per_minute / float(BUDGET_PER_MINUTE) * 100.0) if sample_count else None
        score = None
        if status == "ok":
            usage = budget_usage_pct or 0.0
            score = 100.0 if usage < 85 else 70.0 if usage < 100 else 35.0
        return {
            **_build_metric_meta(
                status=status,
                sample_count=sample_count,
                latest_event_at=all_business_stats.latest_event_at,
                explain=("最近 5 分钟容量与成本可计算" if status == "ok" else "最近 5 分钟无业务样本，容量与成本不可计算"),
                source="bucket",
            ),
            "health_level": _score_to_level(score),
            "score": _round_optional(score, 2),
            "qps": _round_optional(request_qps, 4),
            "question_qps": _round_optional(question_qps, 4),
            "cost_per_minute": _round_optional(cost_per_minute, 4),
            "budget_per_minute": float(BUDGET_PER_MINUTE) if sample_count else None,
            "budget_usage_pct": _round_optional(budget_usage_pct, 2),
        }

    def _build_freshness_card(self, *, latest_event_at: datetime | None, generated_at: datetime) -> dict[str, Any]:
        if latest_event_at is None:
            return {
                "status": "unknown",
                "health_level": "unknown",
                "score": None,
                "delay_sec": None,
                "expired": False,
                "max_delay_sec": DATA_FRESH_CRITICAL_SEC,
                "source": "bucket",
            }
        delay_sec = max(0.0, (_as_utc(generated_at) - _as_utc(latest_event_at)).total_seconds())
        if delay_sec > DATA_FRESH_CRITICAL_SEC:
            status = "stale"
            score = 40.0
            expired = True
        else:
            status = "fresh"
            score = 100.0 if delay_sec <= DATA_FRESH_WARNING_SEC else 75.0
            expired = False
        return {
            "status": status,
            "health_level": _score_to_level(score),
            "score": _round_optional(score, 2),
            "delay_sec": _round_optional(delay_sec, 2),
            "expired": expired,
            "max_delay_sec": DATA_FRESH_CRITICAL_SEC,
            "source": "bucket",
        }

    def _build_module_matrix(self, all_business_rows: Sequence[RuntimeMetricBucketMinute], *, generated_at: datetime) -> list[dict[str, Any]]:
        grouped: dict[str, list[RuntimeMetricBucketMinute]] = defaultdict(list)
        for row in all_business_rows:
            grouped[row.module_key].append(row)
        items: list[dict[str, Any]] = []
        for module_key, rows in sorted(grouped.items()):
            stats = _aggregate_rows(rows)
            latency_p95_ms = _approximate_p95_ms(stats.latency_histogram)
            error_rate = _safe_div(stats.error_5xx_count, stats.request_count)
            delay_sec = max(0.0, (_as_utc(generated_at) - _as_utc(stats.latest_event_at)).total_seconds()) if stats.latest_event_at else None
            error_score = 100.0 if (error_rate or 0.0) < ERROR_5XX_WARNING_RATE else 70.0 if (error_rate or 0.0) < ERROR_5XX_CRITICAL_RATE else 30.0
            latency_score = 100.0 if (latency_p95_ms or 0.0) < LATENCY_WARNING_MS else 70.0 if (latency_p95_ms or 0.0) < LATENCY_CRITICAL_MS else 30.0
            freshness_score = 100.0 if (delay_sec or 0.0) <= DATA_FRESH_WARNING_SEC else 70.0 if (delay_sec or 0.0) <= DATA_FRESH_CRITICAL_SEC else 30.0
            score = _round_optional(_combine_weighted_scores(((error_score, 0.45), (latency_score, 0.35), (freshness_score, 0.2))), 2)
            items.append(
                {
                    "key": module_key,
                    "label": get_observed_module_label(module_key),
                    "health_level": _score_to_level(score),
                    "score": score,
                    "error_rate": _round_optional(error_rate, 4),
                    "latency_p95_ms": _round_optional(latency_p95_ms, 2),
                    "data_delay_sec": _round_optional(delay_sec, 2),
                }
            )
        return items

    def _build_alerts(self, *, request_quality: Mapping[str, Any], freshness: Mapping[str, Any]) -> list[dict[str, Any]]:
        alerts: list[dict[str, Any]] = []
        if request_quality.get("status") == "no_data":
            alerts.append(
                {
                    "code": "overview.runtime.no_data",
                    "severity": "info",
                    "message": "最近 5 分钟暂无业务请求样本",
                    "status": "active",
                }
            )
        error_5xx_rate = _to_float(request_quality.get("error_5xx_rate"))
        if error_5xx_rate is not None and error_5xx_rate >= ERROR_5XX_CRITICAL_RATE:
            alerts.append(
                {
                    "code": "overview.runtime.5xx.critical",
                    "severity": "critical",
                    "message": f"最近 5 分钟 5xx 占比 {error_5xx_rate:.2%}，请优先排查异常接口",
                    "status": "active",
                }
            )
        elif error_5xx_rate is not None and error_5xx_rate >= ERROR_5XX_WARNING_RATE:
            alerts.append(
                {
                    "code": "overview.runtime.5xx.warning",
                    "severity": "warning",
                    "message": f"最近 5 分钟 5xx 占比 {error_5xx_rate:.2%}，建议关注错误趋势",
                    "status": "active",
                }
            )
        latency_p95_ms = _to_float(request_quality.get("latency_p95_ms"))
        if latency_p95_ms is not None and latency_p95_ms >= LATENCY_CRITICAL_MS:
            alerts.append(
                {
                    "code": "overview.runtime.latency.critical",
                    "severity": "critical",
                    "message": f"P95 延迟 {latency_p95_ms:.0f}ms，已超过 {LATENCY_CRITICAL_MS:.0f}ms 阈值",
                    "status": "active",
                }
            )
        elif latency_p95_ms is not None and latency_p95_ms >= LATENCY_WARNING_MS:
            alerts.append(
                {
                    "code": "overview.runtime.latency.warning",
                    "severity": "warning",
                    "message": f"P95 延迟 {latency_p95_ms:.0f}ms，建议关注接口性能",
                    "status": "active",
                }
            )
        if freshness.get("status") == "stale":
            alerts.append(
                {
                    "code": "overview.runtime.freshness.stale",
                    "severity": "warning",
                    "message": "当前总览数据已过期，请检查分钟桶写入链路",
                    "status": "active",
                }
            )
        return alerts

    def _build_stability_card(self, *, alerts: Sequence[Mapping[str, Any]], module_matrix: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        critical_count = sum(1 for alert in alerts if alert.get("severity") == "critical")
        warning_count = sum(1 for alert in alerts if alert.get("severity") == "warning")
        info_count = sum(1 for alert in alerts if alert.get("severity") == "info")
        alerts_score = max(0.0, 100.0 - critical_count * 30.0 - warning_count * 12.0 - info_count * 3.0)
        module_scores = [item.get("score") for item in module_matrix if item.get("score") is not None]
        module_score = _round_optional(sum(module_scores) / len(module_scores), 2) if module_scores else None
        score = _round_optional(_combine_weighted_scores(((alerts_score, 0.6), (module_score, 0.4))), 2)
        return {
            "status": "ok" if score is not None else "no_data",
            "health_level": _score_to_level(score),
            "score": score,
            "critical_alerts": critical_count,
            "warning_alerts": warning_count,
            "module_score": module_score,
        }

    def _build_health_score(
        self,
        *,
        request_quality: Mapping[str, Any],
        stability: Mapping[str, Any],
        capacity_cost: Mapping[str, Any],
        freshness: Mapping[str, Any],
    ) -> float | None:
        if request_quality.get("status") != "ok":
            return None
        return _round_optional(
            _combine_weighted_scores(
                (
                    (_to_float(request_quality.get("score")), 0.35),
                    (_to_float(stability.get("score")), 0.25),
                    (_to_float(capacity_cost.get("score")), 0.20),
                    (_to_float(freshness.get("score")), 0.20),
                )
            ),
            2,
        )

    def _latest_event_from_rows(self, rows: Sequence[RuntimeMetricBucketMinute]) -> datetime | None:
        latest_event = None
        for row in rows:
            if latest_event is None or row.last_event_at > latest_event:
                latest_event = row.last_event_at
        return latest_event

    def _build_degraded_snapshot(self, *, generated_at: datetime, trace_id: str | None, fallback_reason: str) -> dict[str, Any]:
        return {
            "snapshot_at": _to_iso8601(generated_at),
            "source": "empty",
            "degraded": True,
            "system_status": {
                "status": "degraded",
                "health_level": "critical",
                "watermark_at": None,
                "data_source": "empty",
                "explain": "分钟桶读取失败，当前总览已降级到可解释空态",
            },
            "traffic_health": {
                "status": "no_data",
                "sample_count": 0,
                "watermark_at": None,
                "data_source": "empty",
                "explain": "分钟桶不可用，当前窗口无法确认业务样本",
                "window_sec": WINDOW_SECONDS,
            },
            "health_score": None,
            "health_level": "unknown",
            "budget_usage_pct": None,
            "request_quality": {"status": "degraded", "health_level": "unknown", "window_sec": WINDOW_SECONDS, "sample_count": 0},
            "question_activity": {"status": "degraded", "health_level": "unknown", "window_sec": WINDOW_SECONDS, "sample_count": 0},
            "stability": {"status": "degraded", "health_level": "critical", "score": None, "critical_alerts": 1, "warning_alerts": 0, "module_score": None},
            "capacity_cost": {"status": "degraded", "health_level": "unknown", "score": None, "qps": None, "question_qps": None, "cost_per_minute": None, "budget_per_minute": None, "budget_usage_pct": None},
            "alerts": [
                {
                    "code": "overview.bucket.unavailable",
                    "severity": "warning",
                    "message": "实时分钟桶不可用，总览已降级为空态",
                    "status": "active",
                }
            ],
            "freshness": {"status": "unknown", "health_level": "unknown", "score": None, "delay_sec": None, "expired": True, "max_delay_sec": DATA_FRESH_CRITICAL_SEC, "source": "empty"},
            "module_matrix": [],
            "change_feed": [],
            "meta": {"generated_at": _to_iso8601(generated_at), "trace_id": trace_id, "fallback_reason": fallback_reason},
        }


__all__ = ["AdminOverviewQueryService"]
