"""AgentSkill 元数据迁移与模型约束测试。"""

from __future__ import annotations

import importlib.util
import uuid
from pathlib import Path
from types import ModuleType

from app.models.agent_skill import AgentSkill


def _load_migration_module() -> ModuleType:
    """按文件路径加载迁移模块，避免受模块名数字前缀影响。"""

    migration_path = (
        Path(__file__).resolve().parents[2]
        / "alembic/versions/20260213_0003_enhance_agent_skill_metadata.py"
    )
    module_name = f"migration_20260213_0003_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(module_name, migration_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("无法加载迁移模块")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_agent_skill_model_metadata_columns_defaults() -> None:
    """模型字段默认值应与元数据语义一致。"""

    expected_defaults = {
        "auto_enabled": "true",
        "priority": "100",
        "scope": "'global'",
        "trigger_phrases": "'[]'::jsonb",
        "conflicts_with": "'[]'::jsonb",
    }

    for column_name, default_text in expected_defaults.items():
        column = AgentSkill.__table__.c[column_name]
        assert column.nullable is False
        assert column.server_default is not None
        assert str(column.server_default.arg) == default_text


def test_agent_skill_migration_upgrade_skips_existing_columns() -> None:
    """升级迁移应仅补齐缺失字段，不重复写入已存在列。"""

    module = _load_migration_module()
    added_columns: list[str] = []
    sql_statements: list[str] = []

    class _FakeOp:
        @staticmethod
        def add_column(table_name: str, column) -> None:
            assert table_name == module.TABLE_NAME
            added_columns.append(column.name)

        @staticmethod
        def execute(statement) -> None:
            sql_statements.append(str(statement))

    module.op = _FakeOp()
    module._get_existing_columns = lambda table_name: {"auto_enabled"}

    module.upgrade()

    assert added_columns == ["priority", "scope", "trigger_phrases", "conflicts_with"]
    assert "is_enabled" not in added_columns

    merged_sql = "\n".join(sql_statements)
    assert "idx_agent_skills_embedding_ivfflat" in merged_sql
    assert "idx_agent_skills_fts" in merged_sql
    assert "idx_agent_skills_trigger_phrases_gin" in merged_sql


def test_agent_skill_migration_downgrade_only_drops_existing_columns() -> None:
    """降级迁移应仅删除当前存在的元数据字段。"""

    module = _load_migration_module()
    dropped_columns: list[str] = []

    class _FakeOp:
        @staticmethod
        def execute(statement) -> None:
            _ = statement

        @staticmethod
        def drop_column(table_name: str, column_name: str) -> None:
            assert table_name == module.TABLE_NAME
            dropped_columns.append(column_name)

    module.op = _FakeOp()
    module._get_existing_columns = lambda table_name: {"priority", "scope", "conflicts_with"}

    module.downgrade()

    assert dropped_columns == ["conflicts_with", "scope", "priority"]
    assert "is_enabled" not in dropped_columns
