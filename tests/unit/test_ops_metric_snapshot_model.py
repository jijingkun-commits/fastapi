"""总览观测快照模型与迁移测试。"""

from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from sqlalchemy import CheckConstraint, Numeric, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB

import app.models as models
from app.models import OpsMetricSnapshotMinute


def test_ops_metric_snapshot_minute_table_definition() -> None:
    """模型字段定义应符合分钟快照存储口径。"""

    table = OpsMetricSnapshotMinute.__table__

    assert table.name == "t_ops_metric_snapshot_minute"

    snapshot_minute_col = table.c.snapshot_minute
    assert snapshot_minute_col.nullable is False

    health_score_col = table.c.health_score
    assert isinstance(health_score_col.type, Numeric)
    assert health_score_col.type.precision == 5
    assert health_score_col.type.scale == 2

    health_level_col = table.c.health_level
    assert health_level_col.nullable is False
    assert health_level_col.type.length == 16

    budget_usage_pct_col = table.c.budget_usage_pct
    assert isinstance(budget_usage_pct_col.type, Numeric)
    assert budget_usage_pct_col.type.precision == 6
    assert budget_usage_pct_col.type.scale == 2

    payload_col = table.c.snapshot_payload
    assert isinstance(payload_col.type, JSONB)
    assert payload_col.nullable is False
    assert "{}" in str(payload_col.server_default.arg)


def test_ops_metric_snapshot_minute_constraints_and_indexes() -> None:
    """模型应声明唯一约束、范围约束和查询索引。"""

    table = OpsMetricSnapshotMinute.__table__

    unique_constraints = {
        constraint.name: tuple(constraint.columns.keys())
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    assert unique_constraints["uq_ops_metric_snapshot_minute_snapshot_minute"] == (
        "snapshot_minute",
    )

    check_constraints = {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert "ck_ops_metric_snapshot_minute_health_score_range" in check_constraints
    assert "ck_ops_metric_snapshot_minute_budget_usage_pct_non_negative" in check_constraints

    indexes = {index.name: tuple(column.name for column in index.columns) for index in table.indexes}
    assert indexes["ix_ops_metric_snapshot_minute_health_level_minute"] == (
        "health_level",
        "snapshot_minute",
    )
    assert indexes["ix_ops_metric_snapshot_minute_created_at"] == ("created_at",)


def test_ops_metric_snapshot_model_exported_by_models_init() -> None:
    """模型应通过 app.models 对外导出。"""

    assert models.OpsMetricSnapshotMinute is OpsMetricSnapshotMinute
    assert "OpsMetricSnapshotMinute" in models.__all__


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


def _load_snapshot_migration_module():
    migration_path = next(Path("alembic/versions").glob("*ops_metric_snapshot*.py"))
    spec = spec_from_file_location("ops_metric_snapshot_migration", migration_path)
    assert spec and spec.loader
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_migration_revision_chain_and_upgrade_calls() -> None:
    """迁移脚本应连接到最新 revision 且包含建表逻辑。"""

    migration = _load_snapshot_migration_module()

    assert migration.revision == "20260213_0004"
    assert migration.down_revision == "20260213_0003"

    recorder = _OpRecorder()
    migration.op = recorder

    migration.upgrade()

    create_table_calls = [call for call in recorder.calls if call[0] == "create_table"]
    assert len(create_table_calls) == 1
    assert create_table_calls[0][1][0] == "t_ops_metric_snapshot_minute"

    create_index_calls = [call for call in recorder.calls if call[0] == "create_index"]
    created_index_names = {call[1][0] for call in create_index_calls}
    assert "ix_ops_metric_snapshot_minute_health_level_minute" in created_index_names
    assert "ix_ops_metric_snapshot_minute_created_at" in created_index_names


def test_migration_downgrade_calls() -> None:
    """迁移脚本应支持完整回滚。"""

    migration = _load_snapshot_migration_module()
    recorder = _OpRecorder()
    migration.op = recorder

    migration.downgrade()

    assert recorder.calls[0][0] == "drop_index"
    assert recorder.calls[0][1][0] == "ix_ops_metric_snapshot_minute_created_at"
    assert recorder.calls[1][0] == "drop_index"
    assert recorder.calls[1][1][0] == "ix_ops_metric_snapshot_minute_health_level_minute"
    assert recorder.calls[2][0] == "drop_table"
    assert recorder.calls[2][1][0] == "t_ops_metric_snapshot_minute"
