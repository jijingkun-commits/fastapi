"""待办 API 测试（中文注释）。

测试待办的 CRUD 操作和业务逻辑。
"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import get_db
from app.api.deps import get_current_user


client = TestClient(app)


def _mock_user():
    """创建模拟用户。"""
    user = MagicMock()
    user.id = 1
    user.username = "testuser"
    return user


def _mock_todo(todo_id: int = 1, title: str = "测试待办"):
    """创建模拟待办对象。"""
    todo = MagicMock()
    todo.id = todo_id
    todo.user_id = 1
    todo.title = title
    todo.description = "测试描述"
    todo.priority = 2
    todo.status = "pending"
    todo.due_date = datetime(2026, 2, 1, 12, 0, 0)
    todo.start_time = None
    todo.category = "工作"
    todo.progress = 0
    todo.progress_notes = None
    todo.is_completed = False
    todo.is_deleted = False
    todo.created_at = datetime.now()
    todo.updated_at = datetime.now()
    return todo


class TestTodoListAPI:
    """待办列表接口测试。"""
    
    def test_list_todos_unauthorized(self):
        """测试未认证时返回 401。"""
        response = client.get("/api/v1/todos")
        assert response.status_code == 401
    
    def test_list_todos_empty(self):
        """测试空列表返回。"""
        app.dependency_overrides[get_current_user] = _mock_user
        
        with patch("app.repositories.todo_repository.todo_repo.find_by_user") as mock_find:
            mock_find.return_value = []
            response = client.get("/api/v1/todos")
            assert response.status_code == 200
            assert response.json() == []
        
        app.dependency_overrides.clear()
    
    def test_list_todos_with_data(self):
        """测试有数据时正常返回。"""
        app.dependency_overrides[get_current_user] = _mock_user
        
        mock_todos = [_mock_todo(1, "任务1"), _mock_todo(2, "任务2")]
        
        with patch("app.repositories.todo_repository.todo_repo.find_by_user") as mock_find:
            mock_find.return_value = mock_todos
            response = client.get("/api/v1/todos")
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
        
        app.dependency_overrides.clear()


class TestTodoUpdateAPI:
    """待办更新接口测试。"""
    
    def test_update_todo_not_found(self):
        """测试更新不存在的待办返回 404。"""
        app.dependency_overrides[get_current_user] = _mock_user
        
        with patch("app.repositories.todo_repository.todo_repo.get_by_id") as mock_get:
            mock_get.return_value = None
            response = client.patch(
                "/api/v1/todos/999",
                json={"title": "新标题"}
            )
            assert response.status_code == 404
        
        app.dependency_overrides.clear()
    
    def test_update_todo_invalid_priority(self):
        """测试无效优先级返回 422。"""
        app.dependency_overrides[get_current_user] = _mock_user
        
        response = client.patch(
            "/api/v1/todos/1",
            json={"priority": 5}  # 无效值
        )
        assert response.status_code == 422
        
        app.dependency_overrides.clear()
    
    def test_update_todo_success(self):
        """测试成功更新待办。"""
        app.dependency_overrides[get_current_user] = _mock_user
        
        mock_todo = _mock_todo()
        updated_todo = _mock_todo()
        updated_todo.title = "更新后的标题"
        
        with patch("app.repositories.todo_repository.todo_repo.get_by_id") as mock_get, \
             patch("app.repositories.todo_repository.todo_repo.update") as mock_update:
            mock_get.return_value = mock_todo
            mock_update.return_value = updated_todo
            
            response = client.patch(
                "/api/v1/todos/1",
                json={"title": "更新后的标题"}
            )
            assert response.status_code == 200
        
        app.dependency_overrides.clear()


class TestTodoCompleteAPI:
    """待办完成接口测试。"""
    
    def test_complete_todo_success(self):
        """测试成功完成待办。"""
        app.dependency_overrides[get_current_user] = _mock_user
        
        mock_todo = _mock_todo()
        completed_todo = _mock_todo()
        completed_todo.is_completed = True
        completed_todo.status = "completed"
        
        with patch("app.repositories.todo_repository.todo_repo.complete") as mock_complete:
            mock_complete.return_value = completed_todo
            
            response = client.post("/api/v1/todos/1/complete")
            assert response.status_code == 200
        
        app.dependency_overrides.clear()


class TestTodoDeleteAPI:
    """待办删除接口测试。"""
    
    def test_delete_todo_not_found(self):
        """测试删除不存在的待办返回 404。"""
        app.dependency_overrides[get_current_user] = _mock_user
        
        with patch("app.repositories.todo_repository.todo_repo.soft_delete") as mock_delete:
            mock_delete.return_value = False
            
            response = client.delete("/api/v1/todos/999")
            assert response.status_code == 404
        
        app.dependency_overrides.clear()
    
    def test_delete_todo_success(self):
        """测试成功删除待办。"""
        app.dependency_overrides[get_current_user] = _mock_user
        
        with patch("app.repositories.todo_repository.todo_repo.soft_delete") as mock_delete:
            mock_delete.return_value = True
            
            response = client.delete("/api/v1/todos/1")
            assert response.status_code == 200
        
        app.dependency_overrides.clear()
