"""分钟桶写入器测试。"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal

from app.models.runtime_metric_bucket import RuntimeMetricBucketMinute
from app.services.runtime_metric_bucket_writer import RuntimeMetricBucketWriter


class _FakeQuery:
    def __init__(self, rows: list[RuntimeMetricBucketMinute]) -> None:
        self._rows = rows
        self._predicates = []

    def filter(self, *predicates):
        self._predicates.extend(predicates)
        return self

    def one_or_none(self):
        for row in self._rows:
            if all(getattr(row, predicate.left.name) == predicate.right.value for predicate in self._predicates):
                return row
        return None


class _FakeSession:
    def __init__(self) -> None:
        self.rows: list[RuntimeMetricBucketMinute] = []
        self.commit_count = 0

    def query(self, model):
        assert model is RuntimeMetricBucketMinute
        return _FakeQuery(self.rows)

    def add(self, row: RuntimeMetricBucketMinute) -> None:
        self.rows.append(row)

    def commit(self) -> None:
        self.commit_count += 1


@contextmanager
def _session_context(session: _FakeSession):
    yield session


def test_writer_records_business_request_into_all_business_bucket() -> None:
    """普通业务请求应落入 all_business 分钟桶。"""

    fixed_now = datetime(2026, 3, 9, 3, 1, 28, tzinfo=timezone.utc)
    session = _FakeSession()
    writer = RuntimeMetricBucketWriter(
        session_context_factory=lambda: _session_context(session),
        now_provider=lambda: fixed_now,
    )

    ok = writer.record_request(
        path="/api/v1/data-admin/metrics/stats",
        status_code=200,
        duration_ms=128.5,
    )

    assert ok is True
    assert session.commit_count == 1
    assert len(session.rows) == 1

    row = session.rows[0]
    assert row.bucket_minute == datetime(2026, 3, 9, 3, 1, 0, tzinfo=timezone.utc)
    assert row.scope == "all_business"
    assert row.module_key == "data"
    assert row.request_count == 1
    assert row.success_count == 1
    assert row.error_4xx_count == 0
    assert row.error_5xx_count == 0
    assert row.cost_total == Decimal("0")
    assert row.last_event_at == fixed_now


def test_writer_records_chat_request_into_both_business_and_question_buckets() -> None:
    """聊天提问请求应同时落入 all_business 和 user_question。"""

    fixed_now = datetime(2026, 3, 9, 3, 2, 12, tzinfo=timezone.utc)
    session = _FakeSession()
    writer = RuntimeMetricBucketWriter(
        session_context_factory=lambda: _session_context(session),
        now_provider=lambda: fixed_now,
    )

    ok = writer.record_request(
        path="/api/v1/chat/stream",
        status_code=200,
        duration_ms=860.0,
    )

    assert ok is True
    assert len(session.rows) == 2
    scopes = {row.scope for row in session.rows}
    assert scopes == {"all_business", "user_question"}
    assert {row.module_key for row in session.rows} == {"chat"}


def test_writer_records_admin_overview_request_only_into_admin_operation_bucket() -> None:
    """总览自身请求不应计入业务请求质量。"""

    fixed_now = datetime(2026, 3, 9, 3, 3, 5, tzinfo=timezone.utc)
    session = _FakeSession()
    writer = RuntimeMetricBucketWriter(
        session_context_factory=lambda: _session_context(session),
        now_provider=lambda: fixed_now,
    )

    ok = writer.record_request(
        path="/api/v1/admin-overview/summary",
        status_code=200,
        duration_ms=35.0,
    )

    assert ok is True
    assert len(session.rows) == 1
    row = session.rows[0]
    assert row.scope == "admin_operation"
    assert row.module_key == "admin_overview"
    assert row.request_count == 1


def test_writer_updates_existing_bucket_counters() -> None:
    """命中同一分钟同 scope/module 的请求应聚合到同一行。"""

    fixed_now = datetime(2026, 3, 9, 3, 4, 45, tzinfo=timezone.utc)
    session = _FakeSession()
    existing = RuntimeMetricBucketMinute(
        bucket_minute=datetime(2026, 3, 9, 3, 4, 0, tzinfo=timezone.utc),
        scope="all_business",
        module_key="data",
        request_count=1,
        success_count=1,
        error_4xx_count=0,
        error_5xx_count=0,
        latency_histogram={"count": 1, "max_ms": 40.0, "min_ms": 40.0},
        cost_total=Decimal("0"),
        last_event_at=datetime(2026, 3, 9, 3, 4, 10, tzinfo=timezone.utc),
    )
    session.rows.append(existing)
    writer = RuntimeMetricBucketWriter(
        session_context_factory=lambda: _session_context(session),
        now_provider=lambda: fixed_now,
    )

    ok = writer.record_request(
        path="/api/v1/data-admin/metrics/stats",
        status_code=503,
        duration_ms=220.0,
    )

    assert ok is True
    assert len(session.rows) == 1
    assert existing.request_count == 2
    assert existing.success_count == 1
    assert existing.error_5xx_count == 1
    assert existing.last_event_at == fixed_now
