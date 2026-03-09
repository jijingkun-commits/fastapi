"""总览旧快照表删除迁移测试。"""

from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


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


def _load_drop_migration_module():
    migration_path = Path('alembic/versions/20260309_0025_drop_ops_metric_snapshot_minute.py')
    spec = spec_from_file_location('drop_ops_metric_snapshot_migration', migration_path)
    assert spec and spec.loader
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_drop_ops_metric_snapshot_migration_revision_chain_and_upgrade_calls() -> None:
    """迁移脚本应从 merge head 往后衔接，并删除旧表。"""

    migration = _load_drop_migration_module()

    assert migration.revision == '20260309_0025'
    assert migration.down_revision == '20260309_0024'

    recorder = _OpRecorder()
    migration.op = recorder

    migration.upgrade()

    assert recorder.calls[0][0] == 'drop_index'
    assert recorder.calls[0][1][0] == 'ix_ops_metric_snapshot_minute_created_at'
    assert recorder.calls[1][0] == 'drop_index'
    assert recorder.calls[1][1][0] == 'ix_ops_metric_snapshot_minute_health_level_minute'
    assert recorder.calls[2][0] == 'drop_table'
    assert recorder.calls[2][1][0] == 't_ops_metric_snapshot_minute'


def test_drop_ops_metric_snapshot_migration_downgrade_calls() -> None:
    """迁移脚本应支持恢复旧表结构。"""

    migration = _load_drop_migration_module()
    recorder = _OpRecorder()
    migration.op = recorder

    migration.downgrade()

    assert recorder.calls[0][0] == 'create_table'
    assert recorder.calls[0][1][0] == 't_ops_metric_snapshot_minute'
    assert recorder.calls[1][0] == 'create_index'
    assert recorder.calls[1][1][0] == 'ix_ops_metric_snapshot_minute_health_level_minute'
    assert recorder.calls[2][0] == 'create_index'
    assert recorder.calls[2][1][0] == 'ix_ops_metric_snapshot_minute_created_at'
