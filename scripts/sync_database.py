"""数据库同步脚本 - 部署时自动执行所有迁移。

运行方式：python scripts/sync_database.py

功能：
1. 检测并执行 Alembic 迁移（如果有）
2. 执行手动迁移脚本（向后兼容）
3. 校验模型与数据库一致性
"""
import sys
from pathlib import Path
from typing import List, Tuple

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import inspect, text
from app.db.session import engine
from app.db.base import Base

# 导入所有模型
from app.models.user import User
from app.models.todo import Todo, TodoHistory, TodoReminderQueue
from app.models.chat_message import ChatMessage
from app.models.chat_asset import ChatAsset
from app.models.data_agent_metadata import MetaTable, MetaColumn, MetaRelation
from app.models.data_permission import DataPermissionTable, DataPermissionRow, DataPermissionColumn
from app.models.token_blacklist import TokenBlacklist
from app.models.idempotency_key import IdempotencyKey
from app.models.llm_provider import LLMProvider
from app.models.llm_model import LLMModel
from app.models.llm_scene import LLMScene


def get_db_columns(table_name: str) -> set:
    """获取数据库表的列名集合。"""
    inspector = inspect(engine)
    if table_name not in inspector.get_table_names():
        return set()
    return {col["name"] for col in inspector.get_columns(table_name)}


def get_model_columns(model) -> set:
    """获取模型定义的列名集合。"""
    return {col.name for col in model.__table__.columns}


def check_table_exists(table_name: str) -> bool:
    """检查表是否存在。"""
    inspector = inspect(engine)
    return table_name in inspector.get_table_names()


def get_all_models():
    """获取所有需要同步的模型列表。"""
    return [
        User, Todo, TodoHistory, TodoReminderQueue,
        ChatMessage, ChatAsset, MetaTable, MetaColumn,
        MetaRelation, DataPermissionTable, DataPermissionRow,
        DataPermissionColumn, TokenBlacklist, IdempotencyKey,
        LLMProvider, LLMModel, LLMScene,
    ]


def get_db_indexes(table_name: str) -> set:
    """获取数据库表的索引名集合。"""
    inspector = inspect(engine)
    if table_name not in inspector.get_table_names():
        return set()
    return {idx["name"] for idx in inspector.get_indexes(table_name) if idx["name"]}


def sync_missing_indexes():
    """同步缺失的索引（模型有、数据库没有）。"""
    models = get_all_models()
    changes: List[Tuple[str, str, object]] = []
    
    for model in models:
        table_name = model.__tablename__
        if not check_table_exists(table_name):
            continue
        
        # 获取模型定义的索引
        if not hasattr(model, "__table_args__"):
            continue
        
        table_args = model.__table_args__
        if not isinstance(table_args, tuple):
            table_args = (table_args,)
        
        db_indexes = get_db_indexes(table_name)
        
        for arg in table_args:
            # 只处理 Index 对象（跳过 UniqueConstraint 等其他约束）
            if arg.__class__.__name__ == "Index" and hasattr(arg, "name"):
                index_name = arg.name
                if index_name and index_name not in db_indexes:
                    changes.append((table_name, index_name, arg))
    
    if not changes:
        print("所有索引已同步，无需创建。")
        return
    
    print(f"\n发现 {len(changes)} 个缺失索引，开始创建...")
    
    with engine.begin() as conn:
        for table_name, index_name, index_obj in changes:
            print(f"  -> {table_name}.{index_name}")
            try:
                index_obj.create(conn)
                print(f"     ✅ 成功")
            except Exception as e:
                print(f"     ❌ 失败: {e}")


def sync_missing_columns():
    """同步缺失的列（模型有、数据库没有）。"""
    models = get_all_models()
    
    changes: List[Tuple[str, str, str]] = []
    
    for model in models:
        table_name = model.__tablename__
        if not check_table_exists(table_name):
            continue
            
        db_cols = get_db_columns(table_name)
        model_cols = get_model_columns(model)
        missing = model_cols - db_cols
        
        if missing:
            print(f"\n[{table_name}] 发现缺失列: {missing}")
            for col_name in missing:
                col = model.__table__.columns[col_name]
                col_type = col.type.compile(engine.dialect)
                
                # 构建 ALTER TABLE 语句
                default_clause = ""
                if col.default is not None:
                    if hasattr(col.default, 'arg'):
                        default_val = col.default.arg
                        if isinstance(default_val, bool):
                            default_clause = f" DEFAULT {str(default_val).upper()}"
                        elif isinstance(default_val, str):
                            default_clause = f" DEFAULT '{default_val}'"
                        elif default_val is not None:
                            default_clause = f" DEFAULT {default_val}"
                
                sql = f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS {col_name} {col_type}{default_clause}"
                changes.append((table_name, col_name, sql))
    
    if not changes:
        print("\n所有表结构已同步，无需变更。")
        return
    
    print("\n" + "=" * 50)
    print("执行数据库变更")
    print("=" * 50)
    
    with engine.begin() as conn:
        for table_name, col_name, sql in changes:
            print(f"  -> {table_name}.{col_name}")
            try:
                conn.execute(text(sql))
                print(f"     ✅ 成功")
            except Exception as e:
                print(f"     ❌ 失败: {e}")


def create_missing_tables():
    """创建缺失的表。"""
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    
    models = get_all_models()
    
    missing_tables = []
    for model in models:
        if model.__tablename__ not in existing_tables:
            missing_tables.append(model)
    
    if not missing_tables:
        print("所有表已存在，无需创建。")
        return
    
    print(f"\n发现 {len(missing_tables)} 个缺失表，开始创建...")
    
    with engine.begin() as conn:
        for model in missing_tables:
            print(f"  -> 创建 {model.__tablename__}")
            try:
                model.__table__.create(conn)
                print(f"     ✅ 成功")
            except Exception as e:
                print(f"     ❌ 失败: {e}")


def run_alembic_migrations():
    """运行 Alembic 迁移（如果配置存在）。"""
    alembic_ini = project_root / "alembic.ini"
    if not alembic_ini.exists():
        print("未找到 alembic.ini，跳过 Alembic 迁移。")
        return
    
    try:
        from alembic.config import Config
        from alembic import command
        
        alembic_cfg = Config(str(alembic_ini))
        print("\n运行 Alembic 迁移...")
        command.upgrade(alembic_cfg, "head")
        print("✅ Alembic 迁移完成")
    except ImportError:
        print("Alembic 未安装，跳过。")
    except Exception as e:
        print(f"Alembic 迁移失败: {e}")
        print("回退到手动同步模式...")


def main():
    """主入口。"""
    print("=" * 50)
    print("数据库同步工具")
    print("=" * 50)
    
    # 1. 尝试运行 Alembic 迁移
    run_alembic_migrations()
    
    # 2. 创建缺失的表
    print("\n[1/3] 检查缺失表...")
    create_missing_tables()
    
    # 3. 同步缺失的列
    print("\n[2/3] 检查缺失列...")
    sync_missing_columns()
    
    # 4. 同步缺失的索引
    print("\n[3/3] 检查缺失索引...")
    sync_missing_indexes()
    
    print("\n" + "=" * 50)
    print("同步完成")
    print("=" * 50)


if __name__ == "__main__":
    main()
