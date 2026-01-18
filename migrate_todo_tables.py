"""执行待办表升级脚本（中文注释）。

运行数据库迁移脚本来升级 t_todo 表。
"""
import sys
from pathlib import Path

# 添加项目根目录到 sys.path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from app.db.session import engine

def run_migration():
    """执行数据库迁移脚本"""
    sql_file = project_root / "install/scripts/init_postgres.sql/007_upgrade_todo_tables.sql"
    
    print(f"📝 读取 SQL 脚本: {sql_file}")
    with open(sql_file, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    print("🔄 开始执行数据库迁移...")
    
    try:
        with engine.connect() as conn:
            # 执行整个脚本
            conn.execute(text(sql_content))
            conn.commit()
            print("✅ 数据库迁移成功完成！")
            
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
                
    except Exception as e:
        print(f"❌ 迁移失败: {e}")
        raise

if __name__ == "__main__":
    run_migration()
