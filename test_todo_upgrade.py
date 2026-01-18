"""测试待办 Agent 升级（中文注释）。

验证数据库表结构、ORM 模型和工具加载。
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_database_tables():
    """测试数据库表结构"""
    print("=" * 60)
    print("1️⃣  测试数据库表结构")
    print("=" * 60)
    
    from sqlalchemy import text, inspect
    from app.db.session import engine
    
    with engine.connect() as conn:
        inspector = inspect(engine)
        
        # 测试主表字段
        print("\n✅ t_todo 表字段:")
        columns = inspector.get_columns('t_todo')
        expected_new_fields = [
            'start_time', 'actual_completion_time', 'status', 'progress',
            'progress_notes', 'category', 'tags', 'reminder_enabled',
            'reminder_type', 'reminder_advance_minutes', 'reminder_times',
            'last_reminded_at', 'metadata'
        ]
        
        col_names = [col['name'] for col in columns]
        for field in expected_new_fields:
            if field in col_names:
                print(f"   ✓ {field}")
            else:
                print(f"   ✗ {field} (缺失)")
        
        print(f"\n   总字段数: {len(columns)}")
        
        # 测试新表
        print("\n✅ 新增表:")
        for table_name in ['t_todo_history', 't_todo_reminder_queue']:
            if table_name in inspector.get_table_names():
                col_count = len(inspector.get_columns(table_name))
                print(f"   ✓ {table_name} ({col_count} 个字段)")
            else:
                print(f"   ✗ {table_name} (不存在)")


def test_orm_models():
    """测试 ORM 模型"""
    print("\n" + "=" * 60)
    print("2️⃣  测试 ORM 模型")
    print("=" * 60)
    
    try:
        from app.models.todo import Todo, TodoHistory, TodoReminderQueue
        
        print("\n✅ Todo 模型:")
        todo_attrs = [
            'start_time', 'actual_completion_time', 'status', 'progress',
            'progress_notes', 'category', 'tags', 'reminder_enabled',
            'reminder_type', 'reminder_advance_minutes'
        ]
        for attr in todo_attrs:
            if hasattr(Todo, attr):
                print(f"   ✓ {attr}")
            else:
                print(f"   ✗ {attr} (缺失)")
        
        print("\n✅ TodoHistory 模型:")
        print("   ✓ 已定义")
        
        print("\n✅ TodoReminderQueue 模型:")
        print("   ✓ 已定义")
        
    except Exception as e:
        print(f"\n❌ ORM 模型加载失败: {e}")


def test_repository():
    """测试 Repository"""
    print("\n" + "=" * 60)
    print("3️⃣  测试 Repository")
    print("=" * 60)
    
    try:
        from app.repositories.todo_repository import todo_repo
        
        methods = [
            'create', 'get_by_id', 'list_by_user', 'update_fields',
            'update_progress', 'complete', 'cancel', 'delete', 'get_history'
        ]
        
        print("\n✅ TodoRepository 方法:")
        for method in methods:
            if hasattr(todo_repo, method):
                print(f"   ✓ {method}()")
            else:
                print(f"   ✗ {method}() (缺失)")
        
    except Exception as e:
        print(f"\n❌ Repository 加载失败: {e}")


def test_tools():
    """测试工具加载"""
    print("\n" + "=" * 60)
    print("4️⃣  测试 Agent 工具")
    print("=" * 60)
    
    try:
        from app.ai.tools.todo_tools import (
            add_todo, list_todos, update_progress,
            update_todo, complete_todo, delete_todo
        )
        
        tools = {
            'add_todo': add_todo,
            'list_todos': list_todos,
            'update_progress': update_progress,
            'update_todo': update_todo,
            'complete_todo': complete_todo,
            'delete_todo': delete_todo,
        }
        
        print(f"\n✅ 工具数量: {len(tools)} 个")
        for name, tool in tools.items():
            print(f"   ✓ {name}")
        
    except Exception as e:
        print(f"\n❌ 工具加载失败: {e}")
        import traceback
        traceback.print_exc()


def test_agent():
    """测试 Agent 创建"""
    print("\n" + "=" * 60)
    print("5️⃣  测试 Agent 创建")
    print("=" * 60)
    
    try:
        from app.ai.agents.todo_agent import create_todo_agent
        
        # 不实际创建 LLM，只测试导入
        print("\n✅ create_todo_agent 函数:")
        print("   ✓ 已导入")
        
    except Exception as e:
        print(f"\n❌ Agent 加载失败: {e}")


def main():
    """主测试入口"""
    print("\n🧪 待办 Agent 升级验证测试\n")
    
    try:
        test_database_tables()
        test_orm_models()
        test_repository()
        test_tools()
        test_agent()
        
        print("\n" + "=" * 60)
        print("✅ 所有测试完成！")
        print("=" * 60 + "\n")
        
    except Exception as e:
        print(f"\n❌ 测试过程出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
