"""待办看板 API 端点（中文注释）。

提供看板视图所需的数据和操作。
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, field_validator

from app.db.session import get_db
from app.repositories.todo_repository import todo_repo
from app.api.deps import get_current_user
from app.models.user import User
from app.services.recurring_service import recurring_service
from app.core.exceptions import (
    TodoNotFoundException,
    RecurringTaskException
)
from app.models.todo import Todo

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== Schemas ====================

class TodoUpdateRequest(BaseModel):
    """待办更新请求模型（支持部分更新）。"""
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[int] = None
    due_date: Optional[str] = None
    start_time: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = None
    progress: Optional[int] = None
    progress_notes: Optional[str] = None
    
    @field_validator('priority')
    @classmethod
    def validate_priority(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v not in [1, 2, 3]:
            raise ValueError("优先级必须为 1(高), 2(中), 3(低)")
        return v
        
    @field_validator('status')
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ["pending", "completed", "cancelled"]:
            raise ValueError("状态必须为 pending, completed 或 cancelled")
        return v
        
    @field_validator('progress')
    @classmethod
    def validate_progress(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and not (0 <= v <= 100):
            raise ValueError("进度必须在 0 到 100 之间")
        return v

    @field_validator('due_date', 'start_time')
    @classmethod
    def parse_datetime(cls, v: Optional[str]) -> Optional[datetime]:
        """验证并转换时间格式字符串为 datetime 对象。
        
        支持 ISO 8601 格式，如 '2023-10-01T10:00:00'
        """
        if v is None:
            return None
        # 如果是空字符串，视为清除时间？或者非法？这里视为 None
        if v == "":
            return None
            
        try:
            return datetime.fromisoformat(v.replace('Z', '+00:00'))
        except ValueError:
            raise ValueError("时间格式错误，请使用 ISO 8601 格式")


class RecurringConfigRequest(BaseModel):
    """重复任务配置请求。"""
    pattern: str  # daily, weekly, monthly
    interval: int = 1
    days: Optional[List[int]] = None  # 星期几 [1-7]
    end_date: Optional[datetime] = None


# ==================== API Endpoints ====================

@router.get("", response_model=List[Dict[str, Any]])
def list_todos(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取用户的待办列表。
    
    Args:
        status: 状态过滤 (可选: todo/in_progress/done/cancelled)
        
    Returns:
        待办列表
    """
    todos = todo_repo.list_by_user(db, current_user.id, status=status)
    return [_todo_to_dict(todo) for todo in todos]


@router.get("/{todo_id}", response_model=Dict[str, Any])
def get_todo(
    todo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取单个待办详情。
    
    Args:
        todo_id: 待办ID
        
    Returns:
        待办详情
    """
    todo = todo_repo.get_by_id(db, todo_id, current_user.id)
    if not todo:
        raise HTTPException(status_code=404, detail="待办不存在")
    return _todo_to_dict(todo)


@router.patch("/{todo_id}", response_model=Dict[str, Any])
def update_todo(
    todo_id: int,
    data: TodoUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新待办事项（支持部分更新）。
    
    Args:
        todo_id: 待办ID
        data: 更新数据（只传需要修改的字段）
        
    Returns:
        更新后的待办详情
    """
    # 过滤掉请求中未传的字段 (exclude_unset=True)
    updates = data.model_dump(exclude_unset=True)
    
    if not updates:
        raise HTTPException(status_code=400, detail="没有要更新的字段")
    
    todo = todo_repo.update_fields(db, todo_id, current_user.id, **updates)
    if not todo:
        raise HTTPException(status_code=404, detail="待办不存在")
    
    return _todo_to_dict(todo)


@router.delete("/{todo_id}")
def delete_todo(
    todo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除待办事项（软删除）。
    
    Args:
        todo_id: 待办ID
        
    Returns:
        操作结果
    """
    success = todo_repo.delete(db, todo_id, current_user.id, soft=True)
    if not success:
        raise HTTPException(status_code=404, detail="待办不存在")
    return {"success": True, "message": "删除成功"}


@router.post("/{todo_id}/complete")
def complete_todo(
    todo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """完成待办事项。
    
    Args:
        todo_id: 待办ID
        
    Returns:
        操作结果
    """
    success = todo_repo.complete(db, todo_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="待办不存在")
    return {"success": True, "message": "已完成"}



# ==================== Helper Functions ====================

def _todo_to_dict(todo) -> Dict[str, Any]:
    """将 Todo 对象转为字典。"""
    return {
        "id": todo.id,
        "title": todo.title,
        "description": todo.description,
        "status": todo.status,
        "priority": todo.priority,
        "progress": todo.progress,
        "progress_notes": todo.progress_notes,
        "category": todo.category,
        "tags": todo.tags,
        "start_time": todo.start_time.isoformat() if todo.start_time else None,
        "due_date": todo.due_date.isoformat() if todo.due_date else None,
        "create_time": todo.create_time.isoformat() if todo.create_time else None,
        # 重复任务信息
        "is_recurring": todo.is_recurring if hasattr(todo, 'is_recurring') else False,
        # 子任务信息
        "parent_id": todo.parent_id if hasattr(todo, 'parent_id') else None,
        "depth_level": todo.depth_level if hasattr(todo, 'depth_level') else 0,
    }


# 在文件末尾添加重复任务相关端点

@router.post("/{todo_id}/recurring", response_model=Dict[str, Any])
def set_recurring(
    todo_id: int,
    config: RecurringConfigRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """设置待办为重复任务。
    
    Args:
        todo_id: 待办ID
        config: 重复配置
        
    Returns:
        更新后的待办
    """
    user_id = current_user.id
    
    # 验证pattern
    valid_patterns = ["daily", "weekly", "monthly"]
    if config.pattern not in valid_patterns:
        raise HTTPException(status_code=400, detail="无效的重复模式")
    
    # 验证days（weekly模式必须提供）
    if config.pattern == "weekly" and not config.days:
        raise HTTPException(status_code=400, detail="周重复必须指定星期几")
    
    # 更新任务
    updates = {
        "is_recurring": True,
        "recurrence_pattern": config.pattern,
        "recurrence_interval": config.interval,
        "recurrence_days": config.days,
        "recurrence_end_date": config.end_date
    }
    
    todo = todo_repo.update_fields(db, todo_id, user_id, **updates)
    
    if not todo:
        raise HTTPException(status_code=404, detail="待办不存在")
    
    # 生成下一次实例
    next_instance = recurring_service.generate_next_occurrence(db, todo)
    
    return {
        "success": True,
        "todo": _todo_to_dict(todo),
        "next_instance": _todo_to_dict(next_instance) if next_instance else None
    }


@router.delete("/{todo_id}/recurring")
def remove_recurring(
    todo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """取消待办的重复设置。"""
    user_id = current_user.id
    
    updates = {
        "is_recurring": False,
        "recurrence_pattern": None,
        "recurrence_interval": 1,
        "recurrence_days": None,
        "recurrence_end_date": None
    }
    
    todo = todo_repo.update_fields(db, todo_id, user_id, **updates)
    
    if not todo:
        raise HTTPException(status_code=404, detail="待办不存在")
    
    return {"success": True, "message": "已取消重复设置"}


@router.post("/{todo_id}/skip-occurrence")
def skip_occurrence(
    todo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """跳过一次重复任务实例（将当前实例标记为取消，并生成下一次）。"""
    user_id = current_user.id
    
    # 获取任务
    todo = todo_repo.get_by_id(db, todo_id, user_id)
    if not todo:
        raise HTTPException(status_code=404, detail="待办不存在")
    
    # 必须是重复任务的实例
    if not todo.parent_recurring_id:
        raise HTTPException(status_code=400, detail="不是重复任务实例")
    
    # 获取模板
    template = db.query(Todo).filter(
        Todo.id == todo.parent_recurring_id
    ).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="重复任务模板不存在")
    
    # 标记当前实例为已取消
    todo_repo.update_fields(db, todo_id, user_id, status="cancelled")
    
    # 生成下一次实例
    next_instance = recurring_service.generate_next_occurrence(
        db, 
        template,
        base_date=todo.due_date + timedelta(days=1)  # 从下一天开始计算
    )
    
    return {
        "success": True,
        "message": "已跳过此次任务",
        "next_instance": _todo_to_dict(next_instance) if next_instance else None
    }


@router.post("/recurring/generate-upcoming")
def generate_upcoming(
    days: int = 7,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """批量生成未来N天的重复任务实例。"""
    user_id = current_user.id
    
    generated = recurring_service.batch_generate_upcoming(db, user_id, days)
    
    return {
        "success": True,
        "count": len(generated),
        "instances": [_todo_to_dict(t) for t in generated]
    }
