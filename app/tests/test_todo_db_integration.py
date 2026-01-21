"""待办 API 集成测试：数据库验证。

通过直接数据库操作验证 Todo CRUD 功能。
"""
import pytest
from datetime import datetime
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.todo import Todo
from app.models.user import User
from app.repositories.todo_repository import todo_repo


# ==================== Fixtures ====================

@pytest.fixture
def db_session():
    """获取数据库会话。"""
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def test_user(db_session: Session):
    """获取已存在的测试用户（jjk）。"""
    user = db_session.query(User).filter(User.username == "jjk").first()
    if not user:
        pytest.skip("测试用户 'jjk' 不存在，请先创建")
    return user


@pytest.fixture
def cleanup_todos(db_session: Session, test_user: User):
    """测试前后清理测试用户的待办。"""
    # 测试前清理
    db_session.query(Todo).filter(Todo.user_id == test_user.id).delete()
    db_session.commit()
    
    yield
    
    # 测试后清理
    db_session.query(Todo).filter(Todo.user_id == test_user.id).delete()
    db_session.commit()


# ==================== Test Cases ====================

def test_create_todo_saves_to_db(
    db_session: Session,
    test_user: User,
    cleanup_todos
):
    """测试：创建待办后，数据库中能查到。"""
    # 直接往数据库插入
    new_todo = Todo(
        user_id=test_user.id,
        title="集成测试待办",
        description="这是通过集成测试创建的待办",
        priority=3,
        status="todo"
    )
    db_session.add(new_todo)
    db_session.commit()
    db_session.refresh(new_todo)
    
    # 使用 repository 查询验证
    todos = todo_repo.list_by_user(db_session, test_user.id)
    
    found = any(t.title == "集成测试待办" for t in todos)
    assert found, "创建的待办应该能通过 repository 查询到"
    
    # 验证字段
    todo = next(t for t in todos if t.title == "集成测试待办")
    assert todo.description == "这是通过集成测试创建的待办"
    assert todo.priority == 3
    assert todo.status == "todo"


def test_update_todo_via_repo_updates_db(
    db_session: Session,
    test_user: User,
    cleanup_todos
):
    """测试：通过 repository 更新待办后，数据库中的值已变。"""
    # 先创建一个待办
    todo = Todo(
        user_id=test_user.id,
        title="原标题",
        priority=1,
        status="todo"
    )
    db_session.add(todo)
    db_session.commit()
    db_session.refresh(todo)
    todo_id = todo.id
    
    # 使用 repository 更新
    updated = todo_repo.update_fields(
        db_session, todo_id, test_user.id,
        title="新标题", priority=2
    )
    
    assert updated is not None
    
    # 直接查询数据库验证
    db_session.expire_all()
    updated_todo = db_session.query(Todo).filter(Todo.id == todo_id).first()
    
    assert updated_todo is not None
    assert updated_todo.title == "新标题", "数据库中的标题应该已更新"
    assert updated_todo.priority == 2, "数据库中的优先级应该已更新"


def test_delete_todo_via_repo_soft_deletes(
    db_session: Session,
    test_user: User,
    cleanup_todos
):
    """测试：通过 repository 删除后，数据库中 is_deleted=True。"""
    # 先创建一个待办
    todo = Todo(
        user_id=test_user.id,
        title="待删除待办",
        status="todo"
    )
    db_session.add(todo)
    db_session.commit()
    db_session.refresh(todo)
    todo_id = todo.id
    
    # 使用 repository 软删除
    success = todo_repo.delete(db_session, todo_id, test_user.id, soft=True)
    assert success == True
    
    # 直接查询数据库验证软删除
    db_session.expire_all()
    deleted_todo = db_session.query(Todo).filter(Todo.id == todo_id).first()
    
    assert deleted_todo is not None, "软删除不应该物理删除记录"
    assert deleted_todo.is_deleted == True, "is_deleted 应该为 True"


def test_complete_todo_via_repo_changes_status(
    db_session: Session,
    test_user: User,
    cleanup_todos
):
    """测试：完成后，数据库 status='done'。"""
    # 先创建一个待办
    todo = Todo(
        user_id=test_user.id,
        title="待完成待办",
        status="todo"
    )
    db_session.add(todo)
    db_session.commit()
    db_session.refresh(todo)
    todo_id = todo.id
    
    # 使用 repository 完成
    success = todo_repo.complete(db_session, todo_id, test_user.id)
    assert success == True
    
    # 直接查询数据库验证状态
    db_session.expire_all()
    completed_todo = db_session.query(Todo).filter(Todo.id == todo_id).first()
    
    assert completed_todo is not None
    assert completed_todo.status == "done", "状态应该变为 done"
    assert completed_todo.progress == 100, "进度应该变为 100"


def test_list_by_status_filters_correctly(
    db_session: Session,
    test_user: User,
    cleanup_todos
):
    """测试：按状态筛选待办列表。"""
    # 创建不同状态的待办
    todos_data = [
        ("任务1", "todo"),
        ("任务2", "in_progress"),
        ("任务3", "done"),
        ("任务4", "todo"),
    ]
    
    for title, status in todos_data:
        todo = Todo(
            user_id=test_user.id,
            title=title,
            status=status
        )
        db_session.add(todo)
    db_session.commit()
    
    # 筛选 todo 状态
    todo_list = todo_repo.list_by_user(db_session, test_user.id, status="todo")
    assert len(todo_list) == 2, "应该有 2 个 todo 状态的任务"
    
    # 筛选 done 状态
    done_list = todo_repo.list_by_user(db_session, test_user.id, status="done")
    assert len(done_list) == 1, "应该有 1 个 done 状态的任务"
