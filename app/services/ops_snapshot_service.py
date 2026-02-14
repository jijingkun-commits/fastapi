"""总览分钟快照读写服务。"""

from __future__ import annotations

import logging
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Callable, Mapping

from sqlalchemy.orm import Session

from app.db.session import get_db_context
from app.models import OpsMetricSnapshotMinute

logger = logging.getLogger(__name__)


@dataclass
class StoredOpsSnapshot:
    """数据库中保存的总览快照。"""

    snapshot_at: datetime
    health_score: float
    health_level: str
    budget_usage_pct: float
    payload: dict[str, Any]


def _ensure_aware_datetime(value: datetime) -> datetime:
    """将时间标准化为带时区的 UTC 时间。"""

    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class OpsSnapshotService:
    """负责管理 `t_ops_metric_snapshot_minute` 快照。"""

    def __init__(
        self,
        session_context_factory: Callable[[], AbstractContextManager[Session]] = get_db_context,
    ) -> None:
        self._session_context_factory = session_context_factory

    @staticmethod
    def normalize_snapshot_minute(snapshot_at: datetime) -> datetime:
        """将时间向下取整到分钟。"""

        aware_snapshot = _ensure_aware_datetime(snapshot_at)
        return aware_snapshot.replace(second=0, microsecond=0)

    def persist_snapshot(
        self,
        *,
        snapshot_at: datetime,
        health_score: float | None,
        health_level: str,
        budget_usage_pct: float | None,
        payload: Mapping[str, Any],
    ) -> bool:
        """写入或更新分钟快照。"""

        if health_score is None or budget_usage_pct is None:
            logger.debug("总览快照缺少必填数值字段，跳过持久化")
            return False

        snapshot_minute = self.normalize_snapshot_minute(snapshot_at)
        snapshot_payload = dict(payload)

        try:
            with self._session_context_factory() as session:
                existing = (
                    session.query(OpsMetricSnapshotMinute)
                    .filter(OpsMetricSnapshotMinute.snapshot_minute == snapshot_minute)
                    .one_or_none()
                )

                if existing is None:
                    existing = OpsMetricSnapshotMinute(
                        snapshot_minute=snapshot_minute,
                        health_score=Decimal(str(round(health_score, 2))),
                        health_level=health_level,
                        budget_usage_pct=Decimal(str(round(budget_usage_pct, 2))),
                        snapshot_payload=snapshot_payload,
                    )
                    session.add(existing)
                else:
                    existing.health_score = Decimal(str(round(health_score, 2)))
                    existing.health_level = health_level
                    existing.budget_usage_pct = Decimal(str(round(budget_usage_pct, 2)))
                    existing.snapshot_payload = snapshot_payload

                session.commit()
                return True
        except Exception:
            logger.exception("写入总览分钟快照失败")
            return False

    def get_latest_snapshot(self) -> StoredOpsSnapshot | None:
        """获取最近一条分钟快照。"""

        try:
            with self._session_context_factory() as session:
                row = (
                    session.query(OpsMetricSnapshotMinute)
                    .order_by(OpsMetricSnapshotMinute.snapshot_minute.desc())
                    .first()
                )
        except Exception:
            logger.exception("读取总览分钟快照失败")
            return None

        if row is None:
            return None

        return StoredOpsSnapshot(
            snapshot_at=_ensure_aware_datetime(row.snapshot_minute),
            health_score=float(row.health_score),
            health_level=row.health_level,
            budget_usage_pct=float(row.budget_usage_pct),
            payload=dict(row.snapshot_payload or {}),
        )

