"""用户管理模块数据库迁移脚本。

变更内容：
1. t_user 表新增 is_active 字段
2. 新建 t_token_blacklist 表

运行方式：python scripts/migrate_user_management.py
"""
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text, inspect
from app.db.session import engine
from app.db.base import Base
from app.models.token_blacklist import TokenBlacklist


def check_column_exists(table_name: str, column_name: str) -> bool:
    """检查表中是否存在指定列。"""
    inspector = inspect(engine)
    columns = [col["name"] for col in inspector.get_columns(table_name)]
    return column_name in columns


def check_table_exists(table_name: str) -> bool:
    """检查表是否存在。"""
    inspector = inspect(engine)
    return table_name in inspector.get_table_names()


def migrate():
    """执行迁移。"""
    print("=" * 50)
    print("用户管理模块数据库迁移")
    print("=" * 50)
    
    with engine.begin() as conn:
        # 1. t_user 新增 is_active 字段
        print("\n[1/2] 检查 t_user.is_active 字段...")
        if check_table_exists("t_user"):
            if not check_column_exists("t_user", "is_active"):
                print("  -> 添加 is_active 字段...")
                conn.execute(text("""
                    ALTER TABLE t_user 
                    ADD COLUMN is_active BOOLEAN DEFAULT TRUE
                """))
                # 设置已存在用户为启用状态
                conn.execute(text("""
                    UPDATE t_user SET is_active = TRUE WHERE is_active IS NULL
                """))
                print("  ✅ is_active 字段已添加")
            else:
                print("  ⏭️  is_active 字段已存在，跳过")
        else:
            print("  ⚠️  t_user 表不存在，请先运行 init_tables_ci.py")
        
        # 2. 创建 t_token_blacklist 表
        print("\n[2/2] 检查 t_token_blacklist 表...")
        if not check_table_exists("t_token_blacklist"):
            print("  -> 创建 t_token_blacklist 表...")
            TokenBlacklist.__table__.create(conn)
            print("  ✅ t_token_blacklist 表已创建")
        else:
            print("  ⏭️  t_token_blacklist 表已存在，跳过")
    
    print("\n" + "=" * 50)
    print("迁移完成")
    print("=" * 50)


if __name__ == "__main__":
    migrate()
