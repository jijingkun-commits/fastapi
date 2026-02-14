"""总览运行时指标采集器。"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from math import ceil
from typing import Any

from app.services.runtime_request_metrics import RuntimeRequestMetricEvent, runtime_request_metrics_store


def _to_iso8601(value: datetime) -> str:
    """将时间格式化为 RFC3339 字符串。"""

    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    else:
        value = value.astimezone(timezone.utc)
    return value.isoformat().replace("+00:00", "Z")


def _percentile(values: list[float], percent: float) -> float | None:
    """计算百分位数（最近秩法）。"""

    if not values:
        return None

    sorted_values = sorted(values)
    index = max(0, ceil(percent * len(sorted_values)) - 1)
    return sorted_values[index]


@dataclass(frozen=True)
class _ModuleRule:
    """请求路径与模块映射规则。"""

    prefix: str
    key: str
    label: str


MODULE_RULES: tuple[_ModuleRule, ...] = (
    _ModuleRule(prefix="/api/v1/admin-overview", key="system", label="总览驾驶舱"),
    _ModuleRule(prefix="/api/v1/access-admin", key="access", label="访问控制"),
    _ModuleRule(prefix="/api/v1/llm-admin", key="llm", label="LLM 模型配置"),
    _ModuleRule(prefix="/api/v1/skill-admin", key="skill", label="技能管理"),
    _ModuleRule(prefix="/api/v1/system-admin", key="system", label="系统配置"),
    _ModuleRule(prefix="/api/v1/data-admin", key="data", label="问数管理"),
    _ModuleRule(prefix="/api/v1/chat", key="chat", label="对话服务"),
    _ModuleRule(prefix="/api/v1/todo", key="todo", label="待办服务"),
    _ModuleRule(prefix="/api/v1/user", key="user", label="用户管理"),
    _ModuleRule(prefix="/api/v1/auth", key="auth", label="认证服务"),
)


class RuntimeOverviewMetricCollector:
    """基于进程内请求观测数据聚合总览指标。"""

    WINDOW_SEC = 300
    COST_PER_REQUEST = 0.015
    BUDGET_PER_MINUTE = 100.0

    def __init__(self, store=runtime_request_metrics_store) -> None:
        self._store = store

    def _resolve_module(self, path: str) -> tuple[str, str]:
        for rule in MODULE_RULES:
            if path.startswith(rule.prefix):
                return rule.key, rule.label
        return "system", "系统接口"

    def collect(self) -> dict[str, Any]:
        now, events = self._store.list_recent(window_sec=self.WINDOW_SEC)

        if not events:
            return {
                "snapshot_at": _to_iso8601(now),
                "alerts": [
                    {
                        "code": "overview.runtime.no_traffic",
                        "severity": "info",
                        "message": "最近 5 分钟暂无 API 请求，指标待下一轮流量进入后更新",
                        "status": "active",
                    }
                ],
                "modules": [],
                "changes": [],
            }

        request_total = len(events)
        request_5xx = sum(1 for event in events if event.status_code >= 500)
        request_success = request_total - request_5xx

        latency_values = [event.duration_ms for event in events]
        latency_p95_ms = _percentile(latency_values, 0.95)

        qps = request_total / max(self.WINDOW_SEC, 1)
        cost_per_minute = qps * 60.0 * self.COST_PER_REQUEST
        budget_per_minute = max(self.BUDGET_PER_MINUTE, cost_per_minute)

        latest_event_time = max(event.recorded_at for event in events)
        data_delay_sec = max(0.0, (now - latest_event_time).total_seconds())

        modules = self._build_modules(now=now, events=events)
        alerts = self._build_alerts(
            request_total=request_total,
            request_5xx=request_5xx,
            latency_p95_ms=latency_p95_ms,
        )

        return {
            "snapshot_at": _to_iso8601(now),
            "request_total": request_total,
            "request_success": request_success,
            "request_5xx": request_5xx,
            "latency_p95_ms": latency_p95_ms,
            "qps": qps,
            "cost_per_minute": cost_per_minute,
            "budget_per_minute": budget_per_minute,
            "data_delay_sec": data_delay_sec,
            "alerts": alerts,
            "modules": modules,
            "changes": [
                {
                    "id": "overview.runtime.window",
                    "title": f"实时观测窗口已更新（最近 5 分钟，共 {request_total} 条请求）",
                    "level": "info",
                    "occurred_at": _to_iso8601(now),
                }
            ],
        }

    def _build_modules(self, *, now: datetime, events: list[RuntimeRequestMetricEvent]) -> list[dict[str, Any]]:
        grouped: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "key": "",
                "label": "",
                "total": 0,
                "errors_5xx": 0,
                "latencies": [],
                "latest_event": None,
            }
        )

        for event in events:
            module_key, module_label = self._resolve_module(event.path)
            slot = grouped[module_key]
            slot["key"] = module_key
            slot["label"] = module_label
            slot["total"] += 1
            if event.status_code >= 500:
                slot["errors_5xx"] += 1
            slot["latencies"].append(event.duration_ms)

            latest_event = slot["latest_event"]
            if latest_event is None or event.recorded_at > latest_event:
                slot["latest_event"] = event.recorded_at

        module_items: list[dict[str, Any]] = []
        for stats in grouped.values():
            total = stats["total"]
            latest_event_time = stats["latest_event"]
            if latest_event_time is None:
                data_delay_sec = None
            else:
                data_delay_sec = max(0.0, (now - latest_event_time).total_seconds())

            module_items.append(
                {
                    "key": stats["key"],
                    "label": stats["label"],
                    "error_rate": (stats["errors_5xx"] / total) if total > 0 else None,
                    "latency_p95_ms": _percentile(list(stats["latencies"]), 0.95),
                    "data_delay_sec": data_delay_sec,
                }
            )

        module_items.sort(key=lambda item: item.get("key") or "")
        return module_items

    def _build_alerts(
        self,
        *,
        request_total: int,
        request_5xx: int,
        latency_p95_ms: float | None,
    ) -> list[dict[str, Any]]:
        alerts: list[dict[str, Any]] = []

        error_rate = (request_5xx / request_total) if request_total > 0 else 0.0
        if error_rate >= 0.03:
            alerts.append(
                {
                    "code": "overview.runtime.5xx.critical",
                    "severity": "critical",
                    "message": f"最近 5 分钟 5xx 占比 {error_rate:.2%}，请优先排查异常接口",
                    "status": "active",
                    "module": "system",
                }
            )
        elif error_rate >= 0.01:
            alerts.append(
                {
                    "code": "overview.runtime.5xx.warning",
                    "severity": "warning",
                    "message": f"最近 5 分钟 5xx 占比 {error_rate:.2%}，建议关注错误趋势",
                    "status": "active",
                    "module": "system",
                }
            )

        if latency_p95_ms is not None and latency_p95_ms >= 2200.0:
            alerts.append(
                {
                    "code": "overview.runtime.latency.critical",
                    "severity": "critical",
                    "message": f"P95 延迟 {latency_p95_ms:.0f}ms，已超过 2200ms 阈值",
                    "status": "active",
                    "module": "system",
                }
            )
        elif latency_p95_ms is not None and latency_p95_ms >= 900.0:
            alerts.append(
                {
                    "code": "overview.runtime.latency.warning",
                    "severity": "warning",
                    "message": f"P95 延迟 {latency_p95_ms:.0f}ms，建议关注接口性能",
                    "status": "active",
                    "module": "system",
                }
            )

        return alerts


__all__ = ["RuntimeOverviewMetricCollector"]
