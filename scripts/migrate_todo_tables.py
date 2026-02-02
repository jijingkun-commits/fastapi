"""执行待办表升级脚本（中文注释）。

运行数据库迁移脚本来升级 t_todo 表。
使用 engine.begin() 进行事务管理，失败时自动回滚。
"""
import sys
from pathlib import Path

# 添加项目根目录到 sys.path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from app.db.session import engine


def run_migration():
    """执行数据库迁移脚本。
    
    使用 engine.begin() 进行事务管理：
    - 成功时自动提交
    - 失败时自动回滚
    """
    sql_file = project_root / "install/scripts/init_postgres.sql/007_upgrade_todo_tables.sql"
    
    print(f"📝 读取 SQL 脚本: {sql_file}")
    with open(sql_file, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    print("🔄 开始执行数据库迁移...")
    
    # 使用 engine.begin() 进行事务管理
    try:
        with engine.begin() as conn:
            conn.execute(text(sql_content))
        print("✅ 数据库迁移成功完成！")
    except Exception as e:
        print(f"❌ 迁移失败（已自动回滚）: {e}")
        raise
    
    # 验证部分：在事务提交后执行（只读操作）
    _verify_migration()


def _verify_migration():
    """验证迁移结果。"""
    print("🔍 验证迁移结果...")
    
    with engine.connect() as conn:
        # 验证表结构
        result = conn.execute(text("""
            SELECT COUNT(*) as col_count 
            FROM information_schema.columns 
            WHERE table_name = 't_todo'
        """))
        col_count = result.scalar()
        print(f"   - t_todo 表字段数: {col_count}")
        
        # 验证新表
        for table_name in ['t_todo_history', 't_todo_reminder_queue']:
            result = conn.execute(text(f"""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_name = '{table_name}'
                )
            """))
            exists = result.scalar()
            print(f"   - {table_name} 表: {'✅ 已创建' if exists else '❌ 未创建'}")


if __name__ == "__main__":
    run_migration()
