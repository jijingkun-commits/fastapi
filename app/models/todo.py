"""待办事项模型（中文注释）。

定义待办事项的 ORM 模型，用于持久化用户的任务管理数据。
"""
from datetime import datetime
from typing import Optional, List

from sqlalchemy import Integer, String, Text, Boolean, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Todo(Base):
    """待办事项表。
    
    Attributes:
        id: 主键
        user_id: 用户 ID
        title: 待办标题
        description: 详细描述
        
        # 时间管理
        start_time: 开始时间
        due_date: 计划结束时间
        actual_completion_time: 实际完成时间
        
        # 状态管理
        status: 状态 (todo/in_progress/done/cancelled)
        progress: 进度百分比 (0-100)
        progress_notes: 具体进展说明
        
        # 优先级与分类
        priority: 优先级 (1=高, 2=中, 3=低)
        category: 分类标签
        tags: 标签数组
        
        # 提醒配置
        reminder_enabled: 是否启用提醒
        reminder_type: 提醒方式 (email/notification/both)
        reminder_advance_minutes: 提前多少分钟提醒
        reminder_times: 多次提醒时间点
        last_reminded_at: 最后提醒时间
        
        # 元数据
        create_time: 创建时间
        update_time: 更新时间
        extra_data: 扩展元数据
    """
    __tablename__ = "t_todo"
    
    # 主键
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True, comment="用户ID")
    
    # 基本信息
    title: Mapped[str] = mapped_column(String(255), nullable=False, comment="待办标题")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="详细描述")
    
    # 时间管理
    start_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, comment="开始时间")
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, comment="计划结束时间")
    actual_completion_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, comment="实际完成时间")
    
    # 状态管理（统一用 status 判断，移除冗余的 is_completed）
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="todo", comment="状态: todo/in_progress/done/cancelled")
    progress: Mapped[int] = mapped_column(Integer, default=0, comment="进度百分比")
    progress_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="具体进展说明")
    
    # 优先级与分类
    priority: Mapped[int] = mapped_column(Integer, default=2, comment="优先级 1=高 2=中 3=低")
    category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="分类标签")
    tags: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True, comment="标签数组")
    
    # 提醒配置
    reminder_enabled: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否启用提醒")
    reminder_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, comment="提醒方式")
    reminder_advance_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="提前分钟数")
    reminder_times: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True, comment="提醒时间点")
    last_reminded_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, comment="最后提醒时间")
    
    # 元数据
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, comment="逻辑删除标记")
    
    # Phase 4: 重复任务字段
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否为重复任务")
    recurrence_pattern: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="重复模式")
    recurrence_interval: Mapped[int] = mapped_column(Integer, default=1, comment="重复间隔")
    recurrence_days: Mapped[Optional[List]] = mapped_column(JSON, nullable=True, comment="重复的星期几")
    recurrence_end_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, comment="重复结束日期")
    parent_recurring_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="关联的重复任务模板ID")
    
    # Phase 4: 子任务字段
    parent_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="父任务ID")
    task_order: Mapped[int] = mapped_column(Integer, default=0, comment="任务排序")
    depth_level: Mapped[int] = mapped_column(Integer, default=0, comment="层级深度")
    
    create_time: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, comment="创建时间"
    )
    update_time: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间"
    )
    extra_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, comment="扩展元数据")
    
    def __repr__(self) -> str:
        status_icon = {
            "todo": "○",
            "in_progress": "◐",
            "done": "●",
            "cancelled": "✗"
        }.get(self.status, "○")
        priority_icon = {1: "🔴", 2: "🟡", 3: "🟢"}.get(self.priority, "")
        return f"<Todo {status_icon}{priority_icon} [{self.id}] {self.title}>"


class TodoHistory(Base):
    """待办操作历史记录表。
    
    用于审计和回滚，记录所有待办相关操作。
    """
    __tablename__ = "t_todo_history"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    todo_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True, comment="待办ID")
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True, comment="用户ID")
    action: Mapped[str] = mapped_column(String(20), nullable=False, comment="操作类型")
    changed_fields: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, comment="变更字段")
    old_values: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, comment="变更前值")
    new_values: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, comment="变更后值")
    confirmed_by_user: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否用户确认")
    operation_time: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, comment="操作时间"
    )
    extra_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, comment="元数据")
    
    def __repr__(self) -> str:
        confirmed = "✓" if self.confirmed_by_user else "?"
        return f"<TodoHistory {confirmed} [{self.id}] {self.action} @{self.operation_time}>"


class TodoReminderQueue(Base):
    """待办提醒任务队列。
    
    用于异步调度待办提醒任务。
    """
    __tablename__ = "t_todo_reminder_queue"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    todo_id: Mapped[int] = mapped_column(Integer, nullable=False, comment="待办ID")
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, comment="用户ID")
    reminder_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="计划提醒时间")
    reminder_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, comment="提醒方式")
    status: Mapped[str] = mapped_column(String(20), default="pending", comment="提醒状态")
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, comment="发送时间")
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="错误信息")
    retry_count: Mapped[int] = mapped_column(Integer, default=0, comment="重试次数")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, comment="创建时间"
    )
    
    def __repr__(self) -> str:
        status_icon = {"pending": "⏳", "sent": "✓", "failed": "✗"}.get(self.status, "?")
        return f"<Reminder {status_icon} [{self.id}] @{self.reminder_time}>"
