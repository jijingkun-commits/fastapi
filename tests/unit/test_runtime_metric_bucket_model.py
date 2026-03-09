"""总览分钟桶模型与迁移测试。"""

from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from sqlalchemy import UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB

import app.models as models
from app.models import RuntimeMetricBucketMinute


class _OpRecorder:
    """Alembic op 调用记录器。"""

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple, dict]] = []

    def create_table(self, *args, **kwargs) -> None:
        self.calls.append(("create_table", args, kwargs))

    def create_index(self, *args, **kwargs) -> None:
        self.calls.append(("create_index", args, kwargs))

    def drop_index(self, *args, **kwargs) -> None:
        self.calls.append(("drop_index", args, kwargs))

    def drop_table(self, *args, **kwargs) -> None:
        self.calls.append(("drop_table", args, kwargs))


def _load_runtime_metric_bucket_migration_module():
    migration_path = next(Path("alembic/versions").glob("*runtime_metric_bucket_minute*.py"))
    spec = spec_from_file_location("runtime_metric_bucket_migration", migration_path)
    assert spec and spec.loader
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_runtime_metric_bucket_minute_table_definition() -> None:
    """分钟桶模型字段应符合观测聚合口径。"""

    table = RuntimeMetricBucketMinute.__table__

    assert table.name == "t_runtime_metric_bucket_minute"
    assert table.c.bucket_minute.nullable is False
    assert table.c.scope.nullable is False
    assert table.c.scope.type.length == 32
    assert table.c.module_key.nullable is False
    assert table.c.module_key.type.length == 64
    assert table.c.request_count.nullable is False
    assert table.c.success_count.nullable is False
    assert table.c.error_4xx_count.nullable is False
    assert table.c.error_5xx_count.nullable is False
    assert isinstance(table.c.latency_histogram.type, JSONB)
    assert table.c.last_event_at.nullable is False


def test_runtime_metric_bucket_minute_constraints_and_indexes() -> None:
    """分钟桶模型应声明唯一约束与核心索引。"""

    table = RuntimeMetricBucketMinute.__table__

    unique_constraints = {
        constraint.name: tuple(constraint.columns.keys())
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    assert unique_constraints["uq_runtime_metric_bucket_minute_bucket_scope_module"] == (
        "bucket_minute",
        "scope",
        "module_key",
    )

    indexes = {index.name: tuple(column.name for column in index.columns) for index in table.indexes}
    assert indexes["ix_runtime_metric_bucket_minute_scope_bucket"] == (
        "scope",
        "bucket_minute",
    )
    assert indexes["ix_runtime_metric_bucket_minute_module_bucket"] == (
        "module_key",
        "bucket_minute",
    )
    assert indexes["ix_runtime_metric_bucket_minute_last_event_at"] == ("last_event_at",)


def test_runtime_metric_bucket_model_exported_by_models_init() -> None:
    """模型应通过 app.models 对外导出。"""

    assert models.RuntimeMetricBucketMinute is RuntimeMetricBucketMinute
    assert "RuntimeMetricBucketMinute" in models.__all__


def test_runtime_metric_bucket_migration_revision_chain_and_upgrade_calls() -> None:
    """迁移脚本应连接到最新 revision 且包含建表逻辑。"""

    migration = _load_runtime_metric_bucket_migration_module()

    assert migration.revision == "20260309_0022"
    assert migration.down_revision == "20260307_0021"

    recorder = _OpRecorder()
    migration.op = recorder

    migration.upgrade()

    create_table_calls = [call for call in recorder.calls if call[0] == "create_table"]
    assert len(create_table_calls) == 1
    assert create_table_calls[0][1][0] == "t_runtime_metric_bucket_minute"

    create_index_calls = [call for call in recorder.calls if call[0] == "create_index"]
    created_index_names = {call[1][0] for call in create_index_calls}
    assert "ix_runtime_metric_bucket_minute_scope_bucket" in created_index_names
    assert "ix_runtime_metric_bucket_minute_module_bucket" in created_index_names
    assert "ix_runtime_metric_bucket_minute_last_event_at" in created_index_names


def test_runtime_metric_bucket_migration_downgrade_calls() -> None:
    """迁移脚本应支持完整回滚。"""

    migration = _load_runtime_metric_bucket_migration_module()
    recorder = _OpRecorder()
    migration.op = recorder

    migration.downgrade()

    assert recorder.calls[0][0] == "drop_index"
    assert recorder.calls[0][1][0] == "ix_runtime_metric_bucket_minute_last_event_at"
    assert recorder.calls[1][0] == "drop_index"
    assert recorder.calls[1][1][0] == "ix_runtime_metric_bucket_minute_module_bucket"
    assert recorder.calls[2][0] == "drop_index"
    assert recorder.calls[2][1][0] == "ix_runtime_metric_bucket_minute_scope_bucket"
    assert recorder.calls[3][0] == "drop_table"
    assert recorder.calls[3][1][0] == "t_runtime_metric_bucket_minute"
