"""管理后台总览指标采集与健康聚合服务。"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Mapping, Protocol, Sequence

from app.services.ops_snapshot_service import OpsSnapshotService, StoredOpsSnapshot

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    """返回当前 UTC 时间。"""

    return datetime.now(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    """将时间标准化为 UTC 时区。"""

    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _to_iso8601(value: datetime) -> str:
    """将时间格式化为 RFC3339 字符串。"""

    return _as_utc(value).isoformat().replace("+00:00", "Z")


def _parse_datetime(value: Any, fallback: datetime) -> datetime:
    """解析输入时间，失败则回退。"""

    if isinstance(value, datetime):
        return _as_utc(value)

    if isinstance(value, str) and value.strip():
        candidate = value.strip()
        if candidate.endswith("Z"):
            candidate = candidate[:-1] + "+00:00"
        try:
            return _as_utc(datetime.fromisoformat(candidate))
        except ValueError:
            logger.debug("snapshot_at 解析失败，使用当前时间: %s", value)

    return _as_utc(fallback)


def _to_float(value: Any) -> float | None:
    """尽力将输入转换为浮点数。"""

    if value is None:
        return None

    if isinstance(value, bool):
        return None

    if isinstance(value, (int, float)):
        return float(value)

    if isinstance(value, str):
        candidate = value.strip()
        if not candidate:
            return None
        try:
            return float(candidate)
        except ValueError:
            return None

    return None


def _safe_div(numerator: float | None, denominator: float | None) -> float | None:
    """安全除法，分母为 0 或空时返回 None。"""

    if numerator is None or denominator is None:
        return None
    if denominator <= 0:
        return None
    return numerator / denominator


def _clamp(value: float, lower: float = 0.0, upper: float = 100.0) -> float:
    """将数值限制在指定范围。"""

    return min(upper, max(lower, value))


def _round_optional(value: float | None, digits: int = 2) -> float | None:
    """对可空浮点值做安全四舍五入。"""

    if value is None:
        return None
    return round(value, digits)


def _score_to_level(score: float | None) -> str:
    """将 0-100 分映射为健康等级。"""

    if score is None:
        return "unknown"
    if score >= 85:
        return "healthy"
    if score >= 70:
        return "warning"
    return "critical"


def _combine_weighted_scores(weighted_scores: Sequence[tuple[float | None, float]]) -> float | None:
    """按权重合并多个分值，忽略未知项。"""

    valid_items: list[tuple[float, float]] = []
    for score, weight in weighted_scores:
        if score is None:
            continue
        valid_items.append((score, weight))

    if not valid_items:
        return None

    total_weight = sum(weight for _, weight in valid_items)
    if total_weight <= 0:
        return None

    weighted_total = sum(score * weight for score, weight in valid_items)
    return _clamp(weighted_total / total_weight)


@dataclass(frozen=True)
class ThresholdBand:
    """阈值区间定义。"""

    warning: float
    critical: float
    higher_is_better: bool = True


class OverviewMetricCollector(Protocol):
    """总览指标采集器协议。"""

    def collect(self) -> Mapping[str, Any]:
        """采集总览聚合所需的原始指标。"""


class NoopOverviewMetricCollector:
    """默认采集器：返回空数据，由聚合层输出 unknown。"""

    def collect(self) -> Mapping[str, Any]:
        return {}


class AdminOverviewService:
    """总览指标采集与健康聚合服务。"""

    SUCCESS_RATE_BAND = ThresholdBand(warning=0.97, critical=0.90, higher_is_better=True)
    LATENCY_P95_BAND = ThresholdBand(warning=900.0, critical=2200.0, higher_is_better=False)
    ERROR_5XX_RATE_BAND = ThresholdBand(warning=0.01, critical=0.03, higher_is_better=False)
    BUDGET_USAGE_BAND = ThresholdBand(warning=85.0, critical=100.0, higher_is_better=False)
    DATA_DELAY_BAND = ThresholdBand(warning=120.0, critical=300.0, higher_is_better=False)

    def __init__(
        self,
        collector: OverviewMetricCollector | None = None,
        ops_snapshot_service: OpsSnapshotService | None = None,
        now_provider: Callable[[], datetime] = _utc_now,
    ) -> None:
        self._collector = collector or NoopOverviewMetricCollector()
        self._ops_snapshot_service = ops_snapshot_service or OpsSnapshotService()
        self._now_provider = now_provider

    def get_overview_snapshot(self, trace_id: str | None = None) -> dict[str, Any]:
        """采集并聚合总览快照，失败时自动回退。"""

        generated_at = _as_utc(self._now_provider())
        try:
            raw_metrics = self._collector.collect()
        except Exception as exc:
            logger.exception("总览指标采集失败，准备降级到快照兜底")
            return self._build_fallback_snapshot(
                generated_at=generated_at,
                trace_id=trace_id,
                fallback_reason=f"collector_error:{type(exc).__name__}",
            )

        if not isinstance(raw_metrics, Mapping):
            logger.warning("总览采集器返回非映射结构，已回退为空映射")
            raw_metrics = {}

        snapshot_at = _parse_datetime(raw_metrics.get("snapshot_at"), generated_at)
        snapshot = self._build_live_snapshot(
            raw_metrics=raw_metrics,
            snapshot_at=snapshot_at,
            generated_at=generated_at,
            trace_id=trace_id,
        )

        self._ops_snapshot_service.persist_snapshot(
            snapshot_at=snapshot_at,
            health_score=snapshot.get("health_score"),
            health_level=snapshot["health_level"],
            budget_usage_pct=snapshot.get("budget_usage_pct"),
            payload=snapshot,
        )
        return snapshot

    def _build_live_snapshot(
        self,
        *,
        raw_metrics: Mapping[str, Any],
        snapshot_at: datetime,
        generated_at: datetime,
        trace_id: str | None,
    ) -> dict[str, Any]:
        """基于实时采集结果构造 canonical 快照。"""

        request_quality = self._build_request_quality_card(raw_metrics)
        module_matrix = self._build_module_matrix_card(raw_metrics)
        alerts_card = self._build_alerts_card(raw_metrics)
        stability = self._build_stability_card(alerts_card=alerts_card, module_matrix=module_matrix)
        capacity_cost = self._build_capacity_cost_card(raw_metrics)
        freshness = self._build_freshness_card(
            raw_metrics=raw_metrics,
            snapshot_at=snapshot_at,
            generated_at=generated_at,
        )

        health_score = _combine_weighted_scores(
            [
                (request_quality["score"], 0.35),
                (stability["score"], 0.25),
                (capacity_cost["score"], 0.20),
                (freshness["score"], 0.20),
            ]
        )
        health_score = _round_optional(health_score, digits=2)
        health_level = _score_to_level(health_score)

        return {
            "snapshot_at": _to_iso8601(snapshot_at),
            "source": "live",
            "degraded": False,
            "health_score": health_score,
            "health_level": health_level,
            "budget_usage_pct": capacity_cost["budget_usage_pct"],
            "request_quality": request_quality,
            "stability": stability,
            "capacity_cost": capacity_cost,
            "alerts": alerts_card["items"],
            "freshness": freshness,
            "module_matrix": module_matrix["items"],
            "change_feed": self._normalize_change_feed(raw_metrics.get("changes")),
            "meta": {
                "generated_at": _to_iso8601(generated_at),
                "trace_id": trace_id,
            },
        }

    def _build_fallback_snapshot(
        self,
        *,
        generated_at: datetime,
        trace_id: str | None,
        fallback_reason: str,
    ) -> dict[str, Any]:
        """构造降级快照。"""

        stored = self._ops_snapshot_service.get_latest_snapshot()
        if stored is None:
            return self._build_empty_snapshot(
                generated_at=generated_at,
                trace_id=trace_id,
                fallback_reason=fallback_reason,
            )

        snapshot = self._normalize_stored_snapshot(stored)
        snapshot["source"] = "fallback_snapshot"
        snapshot["degraded"] = True
        snapshot["meta"]["generated_at"] = _to_iso8601(generated_at)
        snapshot["meta"]["trace_id"] = trace_id
        snapshot["meta"]["fallback_reason"] = fallback_reason

        age_sec = max(0.0, (generated_at - stored.snapshot_at).total_seconds())
        snapshot["freshness"] = {
            "status": "expired",
            "score": 20.0,
            "health_level": "critical",
            "delay_sec": round(age_sec, 2),
            "expired": True,
            "max_delay_sec": self.DATA_DELAY_BAND.critical,
            "source": "fallback",
        }

        fallback_alert = {
            "code": "overview.snapshot.fallback",
            "severity": "warning",
            "message": "实时聚合失败，已降级到最近快照",
            "status": "active",
        }
        alerts = snapshot.get("alerts")
        if not isinstance(alerts, list):
            alerts = []
        alerts = [dict(item) for item in alerts]
        alerts.append(fallback_alert)
        snapshot["alerts"] = alerts

        return snapshot

    def _build_empty_snapshot(
        self,
        *,
        generated_at: datetime,
        trace_id: str | None,
        fallback_reason: str,
    ) -> dict[str, Any]:
        """当实时与历史都不可用时返回空快照。"""

        return {
            "snapshot_at": _to_iso8601(generated_at),
            "source": "empty",
            "degraded": True,
            "health_score": None,
            "health_level": "unknown",
            "budget_usage_pct": None,
            "request_quality": {
                "status": "unknown",
                "score": None,
                "success_rate": None,
                "error_5xx_rate": None,
                "latency_p95_ms": None,
            },
            "stability": {
                "status": "unknown",
                "score": None,
                "critical_alerts": None,
                "warning_alerts": None,
            },
            "capacity_cost": {
                "status": "unknown",
                "score": None,
                "qps": None,
                "cost_per_minute": None,
                "budget_per_minute": None,
                "budget_usage_pct": None,
                "budget_health_level": "unknown",
            },
            "alerts": [
                {
                    "code": "overview.snapshot.unavailable",
                    "severity": "warning",
                    "message": "实时聚合与历史快照均不可用",
                    "status": "active",
                }
            ],
            "freshness": {
                "status": "unknown",
                "score": None,
                "health_level": "unknown",
                "delay_sec": None,
                "expired": True,
                "max_delay_sec": self.DATA_DELAY_BAND.critical,
                "source": "empty",
            },
            "module_matrix": [],
            "change_feed": [],
            "meta": {
                "generated_at": _to_iso8601(generated_at),
                "trace_id": trace_id,
                "fallback_reason": fallback_reason,
            },
        }

    def _build_request_quality_card(self, raw_metrics: Mapping[str, Any]) -> dict[str, Any]:
        """计算请求质量维度。"""

        request_total = _to_float(raw_metrics.get("request_total"))
        request_success = _to_float(raw_metrics.get("request_success"))
        request_5xx = _to_float(raw_metrics.get("request_5xx"))

        success_rate = _to_float(raw_metrics.get("success_rate"))
        if success_rate is None:
            success_rate = _safe_div(request_success, request_total)

        error_5xx_rate = _to_float(raw_metrics.get("error_5xx_rate"))
        if error_5xx_rate is None:
            error_5xx_rate = _safe_div(request_5xx, request_total)

        latency_p95_ms = _to_float(raw_metrics.get("latency_p95_ms"))

        success_eval = self._evaluate_numeric_metric(success_rate, self.SUCCESS_RATE_BAND)
        error_eval = self._evaluate_numeric_metric(error_5xx_rate, self.ERROR_5XX_RATE_BAND)
        latency_eval = self._evaluate_numeric_metric(latency_p95_ms, self.LATENCY_P95_BAND)

        score = _combine_weighted_scores(
            [
                (success_eval["score"], 0.5),
                (error_eval["score"], 0.3),
                (latency_eval["score"], 0.2),
            ]
        )
        score = _round_optional(score, 2)

        return {
            "status": _score_to_level(score),
            "score": score,
            "request_total": _round_optional(request_total, 0),
            "success_rate": _round_optional(success_rate, 4),
            "error_5xx_rate": _round_optional(error_5xx_rate, 4),
            "latency_p95_ms": _round_optional(latency_p95_ms, 2),
            "signals": {
                "success_rate": success_eval,
                "error_5xx_rate": error_eval,
                "latency_p95_ms": latency_eval,
            },
        }

    def _build_capacity_cost_card(self, raw_metrics: Mapping[str, Any]) -> dict[str, Any]:
        """计算容量与成本维度。"""

        qps = _to_float(raw_metrics.get("qps"))
        cost_per_minute = _to_float(raw_metrics.get("cost_per_minute"))
        budget_per_minute = _to_float(raw_metrics.get("cost_budget_per_minute"))
        if budget_per_minute is None:
            budget_per_minute = _to_float(raw_metrics.get("budget_per_minute"))

        budget_usage_pct = _to_float(raw_metrics.get("budget_usage_pct"))
        if budget_usage_pct is None:
            usage_ratio = _safe_div(cost_per_minute, budget_per_minute)
            if usage_ratio is not None:
                budget_usage_pct = usage_ratio * 100.0

        budget_eval = self._evaluate_numeric_metric(budget_usage_pct, self.BUDGET_USAGE_BAND)

        score = _round_optional(budget_eval["score"], 2)
        return {
            "status": _score_to_level(score),
            "score": score,
            "qps": _round_optional(qps, 2),
            "cost_per_minute": _round_optional(cost_per_minute, 2),
            "budget_per_minute": _round_optional(budget_per_minute, 2),
            "budget_usage_pct": _round_optional(budget_usage_pct, 2),
            "budget_health_level": budget_eval["level"],
            "signals": {
                "budget_usage_pct": budget_eval,
            },
        }

    def _build_freshness_card(
        self,
        *,
        raw_metrics: Mapping[str, Any],
        snapshot_at: datetime,
        generated_at: datetime,
    ) -> dict[str, Any]:
        """计算数据新鲜度维度。"""

        delay_sec = _to_float(raw_metrics.get("data_delay_sec"))
        if delay_sec is None:
            delay_sec = max(0.0, (generated_at - snapshot_at).total_seconds())
            if abs(delay_sec) < 1e-6:
                delay_sec = None

        freshness_eval = self._evaluate_numeric_metric(delay_sec, self.DATA_DELAY_BAND)
        status = "unknown"
        expired = False
        if delay_sec is None:
            status = "unknown"
            expired = False
        elif delay_sec > self.DATA_DELAY_BAND.critical:
            status = "expired"
            expired = True
        else:
            status = "fresh"
            expired = False

        return {
            "status": status,
            "score": _round_optional(freshness_eval["score"], 2),
            "health_level": freshness_eval["level"],
            "delay_sec": _round_optional(delay_sec, 2),
            "expired": expired,
            "max_delay_sec": self.DATA_DELAY_BAND.critical,
            "source": "live",
            "signals": {
                "data_delay_sec": freshness_eval,
            },
        }

    def _build_module_matrix_card(self, raw_metrics: Mapping[str, Any]) -> dict[str, Any]:
        """计算模块健康矩阵。"""

        raw_modules = raw_metrics.get("modules")
        if not isinstance(raw_modules, list):
            return {
                "status": "unknown",
                "score": None,
                "total": 0,
                "items": [],
            }

        matrix_items: list[dict[str, Any]] = []
        module_scores: list[tuple[float | None, float]] = []

        for index, raw_module in enumerate(raw_modules):
            if not isinstance(raw_module, Mapping):
                continue

            key = str(raw_module.get("key") or f"module_{index}")
            label = str(raw_module.get("label") or key)
            error_rate = _to_float(raw_module.get("error_rate"))
            latency_p95_ms = _to_float(raw_module.get("latency_p95_ms"))
            data_delay_sec = _to_float(raw_module.get("data_delay_sec"))

            error_eval = self._evaluate_numeric_metric(error_rate, self.ERROR_5XX_RATE_BAND)
            latency_eval = self._evaluate_numeric_metric(latency_p95_ms, self.LATENCY_P95_BAND)
            freshness_eval = self._evaluate_numeric_metric(data_delay_sec, self.DATA_DELAY_BAND)

            module_score = _combine_weighted_scores(
                [
                    (error_eval["score"], 0.45),
                    (latency_eval["score"], 0.35),
                    (freshness_eval["score"], 0.20),
                ]
            )
            module_score = _round_optional(module_score, 2)
            module_level = _score_to_level(module_score)

            matrix_items.append(
                {
                    "key": key,
                    "label": label,
                    "health_level": module_level,
                    "score": module_score,
                    "error_rate": _round_optional(error_rate, 4),
                    "latency_p95_ms": _round_optional(latency_p95_ms, 2),
                    "data_delay_sec": _round_optional(data_delay_sec, 2),
                    "signals": {
                        "error_rate": error_eval,
                        "latency_p95_ms": latency_eval,
                        "data_delay_sec": freshness_eval,
                    },
                }
            )
            module_scores.append((module_score, 1.0))

        matrix_score = _combine_weighted_scores(module_scores)
        matrix_score = _round_optional(matrix_score, 2)

        return {
            "status": _score_to_level(matrix_score),
            "score": matrix_score,
            "total": len(matrix_items),
            "items": matrix_items,
        }

    def _build_alerts_card(self, raw_metrics: Mapping[str, Any]) -> dict[str, Any]:
        """聚合告警信息。"""

        has_alert_key = "alerts" in raw_metrics
        normalized_alerts = self._normalize_alerts(raw_metrics.get("alerts"))

        if not has_alert_key:
            return {
                "status": "unknown",
                "score": None,
                "critical": None,
                "warning": None,
                "info": None,
                "total": None,
                "items": normalized_alerts,
            }

        critical_count = sum(1 for item in normalized_alerts if item["severity"] == "critical")
        warning_count = sum(1 for item in normalized_alerts if item["severity"] == "warning")
        info_count = sum(1 for item in normalized_alerts if item["severity"] == "info")

        base_score = 100.0
        penalty = critical_count * 30.0 + warning_count * 12.0 + info_count * 3.0
        score = _round_optional(_clamp(base_score - penalty), 2)

        return {
            "status": _score_to_level(score),
            "score": score,
            "critical": critical_count,
            "warning": warning_count,
            "info": info_count,
            "total": len(normalized_alerts),
            "items": normalized_alerts,
        }

    def _build_stability_card(self, *, alerts_card: Mapping[str, Any], module_matrix: Mapping[str, Any]) -> dict[str, Any]:
        """计算稳定性维度。"""

        score = _combine_weighted_scores(
            [
                (_to_float(alerts_card.get("score")), 0.6),
                (_to_float(module_matrix.get("score")), 0.4),
            ]
        )
        score = _round_optional(score, 2)

        return {
            "status": _score_to_level(score),
            "score": score,
            "critical_alerts": alerts_card.get("critical"),
            "warning_alerts": alerts_card.get("warning"),
            "module_score": module_matrix.get("score"),
        }

    def _normalize_stored_snapshot(self, stored: StoredOpsSnapshot) -> dict[str, Any]:
        """将数据库中的历史快照规范化为 canonical 结构。"""

        payload = dict(stored.payload or {})

        payload.setdefault("snapshot_at", _to_iso8601(stored.snapshot_at))
        payload.setdefault("source", "fallback_snapshot")
        payload.setdefault("degraded", True)
        payload.setdefault("health_score", _round_optional(stored.health_score, 2))
        payload.setdefault("health_level", stored.health_level)
        payload.setdefault("budget_usage_pct", _round_optional(stored.budget_usage_pct, 2))

        request_quality = payload.get("request_quality")
        if not isinstance(request_quality, Mapping):
            payload["request_quality"] = {
                "status": "unknown",
                "score": None,
                "success_rate": None,
                "error_5xx_rate": None,
                "latency_p95_ms": None,
            }

        capacity_cost = payload.get("capacity_cost")
        if not isinstance(capacity_cost, Mapping):
            payload["capacity_cost"] = {
                "status": "unknown",
                "score": None,
                "qps": None,
                "cost_per_minute": None,
                "budget_per_minute": None,
                "budget_usage_pct": _round_optional(stored.budget_usage_pct, 2),
                "budget_health_level": _score_to_level(stored.health_score),
            }

        module_matrix = payload.get("module_matrix")
        if not isinstance(module_matrix, list):
            payload["module_matrix"] = []

        alerts = payload.get("alerts")
        if not isinstance(alerts, list):
            payload["alerts"] = []

        change_feed = payload.get("change_feed")
        if not isinstance(change_feed, list):
            payload["change_feed"] = []

        meta = payload.get("meta")
        if not isinstance(meta, Mapping):
            payload["meta"] = {"generated_at": _to_iso8601(_utc_now()), "trace_id": None}

        return payload

    def _normalize_alerts(self, raw_alerts: Any) -> list[dict[str, Any]]:
        """规范化告警列表。"""

        if not isinstance(raw_alerts, list):
            return []

        alerts: list[dict[str, Any]] = []
        for index, item in enumerate(raw_alerts):
            if not isinstance(item, Mapping):
                continue

            severity = str(item.get("severity") or "warning").lower()
            if severity not in {"critical", "warning", "info"}:
                severity = "warning"

            alert = {
                "code": str(item.get("code") or f"alert_{index}"),
                "severity": severity,
                "message": str(item.get("message") or "系统告警"),
                "module": item.get("module"),
                "status": str(item.get("status") or "active"),
            }
            alerts.append(alert)

        return alerts

    def _normalize_change_feed(self, raw_changes: Any) -> list[dict[str, Any]]:
        """规范化关键变更流。"""

        if not isinstance(raw_changes, list):
            return []

        normalized: list[dict[str, Any]] = []
        for index, item in enumerate(raw_changes):
            if not isinstance(item, Mapping):
                continue

            normalized.append(
                {
                    "id": str(item.get("id") or f"change_{index}"),
                    "title": str(item.get("title") or "配置变更"),
                    "level": str(item.get("level") or "info"),
                    "occurred_at": str(item.get("occurred_at") or ""),
                }
            )

        return normalized

    def _evaluate_numeric_metric(self, value: float | None, band: ThresholdBand) -> dict[str, Any]:
        """按阈值评估单指标得分。"""

        if value is None:
            return {
                "value": None,
                "score": None,
                "level": "unknown",
            }

        score = self._score_by_threshold(value=value, band=band)
        score = _round_optional(score, 2)
        return {
            "value": _round_optional(value, 4),
            "score": score,
            "level": _score_to_level(score),
        }

    @staticmethod
    def _score_by_threshold(*, value: float, band: ThresholdBand) -> float:
        """依据阈值区间计算 0-100 评分。"""

        if band.higher_is_better:
            if value >= band.warning:
                return 100.0
            if value >= band.critical:
                ratio = (value - band.critical) / max(band.warning - band.critical, 1e-6)
                return 70.0 + ratio * 15.0
            if band.critical <= 0:
                return 30.0
            ratio = max(0.0, value / band.critical)
            return 20.0 + ratio * 45.0

        if value <= band.warning:
            return 100.0
        if value <= band.critical:
            ratio = (value - band.warning) / max(band.critical - band.warning, 1e-6)
            return 85.0 - ratio * 15.0

        ratio = (value - band.critical) / max(band.critical, 1.0)
        return _clamp(70.0 - min(ratio, 1.0) * 55.0)


__all__ = [
    "AdminOverviewService",
    "NoopOverviewMetricCollector",
    "OverviewMetricCollector",
]
