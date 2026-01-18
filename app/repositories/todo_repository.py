"""待办事项 Repository（中文注释）。

提供待办事项的 CRUD 操作和审计日志记录。
"""
from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy import select, update, delete, and_
from sqlalchemy.orm import Session

from app.models.todo import Todo, TodoHistory


class TodoRepository:
    """待办事项数据访问层。"""
    
    def create(
        self, 
        db: Session, 
        user_id: int, 
        title: str, 
        description: Optional[str] = None,
        priority: int = 2,
        start_time: Optional[datetime] = None,
        due_date: Optional[datetime] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        reminder_enabled: bool = False,
        reminder_type: Optional[str] = None,
        reminder_advance_minutes: Optional[int] = None,
        extra_data: Optional[Dict] = None,
    ) -> Todo:
        """创建待办事项。
        
        Args:
            db: 数据库会话
            user_id: 用户 ID
            title: 待办标题
            description: 详细描述
            priority: 优先级 (1=高, 2=中, 3=低)
            start_time: 开始时间
            due_date: 计划结束时间
            category: 分类
            tags: 标签列表
            reminder_enabled: 是否启用提醒
            reminder_type: 提醒方式
            reminder_advance_minutes: 提前提醒分钟数
            extra_data: 元数据
            
        Returns:
            创建的待办事项
        """
        todo = Todo(
            user_id=user_id,
            title=title,
            description=description,
            priority=priority,
            start_time=start_time,
            due_date=due_date,
            category=category,
            tags=tags,
            status="todo",
            reminder_enabled=reminder_enabled,
            reminder_type=reminder_type,
            reminder_advance_minutes=reminder_advance_minutes,
            extra_data=extra_data,
        )
        db.add(todo)
        db.commit()
        db.refresh(todo)
        
        # 记录操作历史
        self._log_history(
            db=db, 
            todo_id=todo.id, 
            user_id=user_id, 
            action="create",
            new_values=self._todo_to_dict(todo)
        )
        
        return todo
    
    def get_by_id(self, db: Session, todo_id: int, user_id: int) -> Optional[Todo]:
        """根据 ID 获取待办事项（需验证用户归属）。"""
        stmt = select(Todo).where(Todo.id == todo_id, Todo.user_id == user_id)
        return db.execute(stmt).scalar_one_or_none()
    
    def list_by_user(
        self, 
        db: Session, 
        user_id: int, 
        status: Optional[str] = None,
        category: Optional[str] = None,
        priority: Optional[int] = None,
        keyword: Optional[str] = None,  # ⬅️ 新增关键词参数
        include_deleted: bool = False,
        limit: int = 50
    ) -> List[Todo]:
        """列出用户的待办事项。
        
        Args:
            db: 数据库会话
            user_id: 用户 ID
            status: 状态过滤 (todo/in_progress/done/cancelled)
            category: 分类过滤
            priority: 优先级过滤
            keyword: 标题关键词模糊搜索 ⬅️ 新增
            include_deleted: 是否包含已删除的
            limit: 返回数量限制
            
        Returns:
            待办事项列表
        """
        stmt = select(Todo).where(Todo.user_id == user_id)
        
        # 默认不显示已删除的
        if not include_deleted:
            stmt = stmt.where(Todo.is_deleted == False)
        
        # 状态过滤
        if status:
            if status == "pending":
                stmt = stmt.where(Todo.status.in_(["todo", "in_progress"]))
            elif status == "completed":
                stmt = stmt.where(Todo.status == "done")
            else:
                stmt = stmt.where(Todo.status == status)
        
        # 分类过滤
        if category:
            stmt = stmt.where(Todo.category == category)
        
        # 优先级过滤
        if priority:
            stmt = stmt.where(Todo.priority == priority)
        
        # ⬅️ 关键词过滤 (模糊匹配)
        if keyword:
            stmt = stmt.where(Todo.title.contains(keyword))
        
        stmt = stmt.order_by(Todo.priority.asc(), Todo.due_date.asc().nullslast(), Todo.create_time.desc()).limit(limit)
        return list(db.execute(stmt).scalars().all())
    
    def update_fields(
        self, 
        db: Session, 
        todo_id: int, 
        user_id: int, 
        **updates
    ) -> Optional[Todo]:
        """更新待办字段。
        
        Args:
            db: 数据库会话
            todo_id: 待办 ID
            user_id: 用户 ID
            **updates: 要更新的字段
            
        Returns:
            更新后的待办事项
        """
        # 获取旧值
        todo = self.get_by_id(db, todo_id, user_id)
        if not todo:
            return None
        
        old_values = self._todo_to_dict(todo)
        
        # 更新字段
        updates['update_time'] = datetime.now()
        stmt = (
            update(Todo)
            .where(Todo.id == todo_id, Todo.user_id == user_id)
            .values(**updates)
        )
        db.execute(stmt)
        db.commit()
        
        # 刷新获取新值
        db.refresh(todo)
        new_values = self._todo_to_dict(todo)
        
        # 记录历史
        changed_fields = list(updates.keys())
        self._log_history(
            db=db,
            todo_id=todo_id,
            user_id=user_id,
            action="update",
            changed_fields=changed_fields,
            old_values={k: old_values.get(k) for k in changed_fields},
            new_values={k: new_values.get(k) for k in changed_fields}
        )
        
        return todo
    
    def update_progress(
        self, 
        db: Session, 
        todo_id: int, 
        user_id: int, 
        progress: int,
        progress_notes: Optional[str] = None
    ) -> bool:
        """更新待办进度。"""
        updates = {
            "progress": progress,
            "progress_notes": progress_notes,
        }
        
        # 自动更新状态
        if progress >= 100:
            updates["status"] = "done"
            updates["actual_completion_time"] = datetime.now()
        elif progress > 0:
            updates["status"] = "in_progress"
        
        result = self.update_fields(db, todo_id, user_id, **updates)
        return result is not None
    
    def complete(self, db: Session, todo_id: int, user_id: int) -> bool:
        """标记待办事项为已完成。"""
        updates = {
            "status": "done",
            "progress": 100,
            "actual_completion_time": datetime.now(),
        }
        result = self.update_fields(db, todo_id, user_id, **updates)
        
        if result:
            self._log_history(
                db=db,
                todo_id=todo_id,
                user_id=user_id,
                action="complete"
            )
        
        return result is not None
    
    def cancel(self, db: Session, todo_id: int, user_id: int) -> bool:
        """取消待办事项。"""
        updates = {"status": "cancelled"}
        result = self.update_fields(db, todo_id, user_id, **updates)
        
        if result:
            self._log_history(
                db=db,
                todo_id=todo_id,
                user_id=user_id,
                action="cancel"
            )
        
        return result is not None

    
    def delete(self, db: Session, todo_id: int, user_id: int, soft: bool = True) -> bool:
        """删除待办事项（默认逻辑删除）。
        
        Args:
            db: 数据库会话
            todo_id: 待办事项 ID
            user_id: 用户 ID
            soft: 是否软删除（逻辑删除），默认 True
            
        Returns:
            是否成功
        """
        # 先获取待办信息用于日志
        todo = self.get_by_id(db, todo_id, user_id)
        if not todo:
            return False
        
        old_values = self._todo_to_dict(todo)
        
        if soft:
            # 逻辑删除：设置 is_deleted = true
            stmt = (
                update(Todo)
                .where(Todo.id == todo_id, Todo.user_id == user_id)
                .values(is_deleted=True, update_time=datetime.now())
            )
            result = db.execute(stmt)
        else:
            # 物理删除
            stmt = delete(Todo).where(Todo.id == todo_id, Todo.user_id == user_id)
            result = db.execute(stmt)
        
        db.commit()
        
        if result.rowcount > 0:
            self._log_history(
                db=db,
                todo_id=todo_id,
                user_id=user_id,
                action="soft_delete" if soft else "hard_delete",
                old_values=old_values
            )
        
        return result.rowcount > 0
    
    def batch_complete(self, db: Session, todo_ids: List[int], user_id: int) -> int:
        """批量完成待办事项（优化版）。
        
        Args:
            db: 数据库会话
            todo_ids: 待办ID列表
            user_id: 用户ID
            
        Returns:
            实际完成的数量
        """
        from datetime import datetime
        
        # 1. 批量查询（一次查询）
        todos = db.query(Todo).filter(
            and_(
                Todo.id.in_(todo_ids),
                Todo.user_id == user_id,
                Todo.is_deleted == False,
                Todo.status != "done"  # 过滤已完成
            )
        ).all()
        
        if not todos:
            return 0
        
        # 2. 批量更新
        now = datetime.now()
        for todo in todos:
            todo.status = "done"
            todo.progress = 100
            todo.actual_completion_time = now
            todo.update_time = now
        
        # 3. 批量插入历史记录（优化）
        from app.models.todo import TodoHistory
        histories = [
            TodoHistory(
                todo_id=todo.id,
                user_id=user_id,
                action="complete",
                changed_fields=json.dumps({
                    "status": {"old": todo.status, "new": "done"},
                    "progress": {"old": todo.progress, "new": 100}
                }),
                create_time=now
            )
            for todo in todos
        ]
        db.bulk_save_objects(histories)  # 批量插入
        
        db.commit()
        logger.info(f"批量完成 {len(todos)} 个待办")
        
        return len(todos)
    
    def get_history(
        self, 
        db: Session, 
        todo_id: Optional[int] = None,
        user_id: Optional[int] = None,
        limit: int = 50
    ) -> List[TodoHistory]:
        """获取操作历史。"""
        stmt = select(TodoHistory)
        
        if todo_id:
            stmt = stmt.where(TodoHistory.todo_id == todo_id)
        if user_id:
            stmt = stmt.where(TodoHistory.user_id == user_id)
        
        stmt = stmt.order_by(TodoHistory.operation_time.desc()).limit(limit)
        return list(db.execute(stmt).scalars().all())
    
    def _todo_to_dict(self, todo: Todo) -> Dict[str, Any]:
        """将待办对象转为字典（用于历史记录）。"""
        return {
            "id": todo.id,
            "user_id": todo.user_id,
            "title": todo.title,
            "description": todo.description,
            "status": todo.status,
            "priority": todo.priority,
            "progress": todo.progress,
            "due_date": todo.due_date.isoformat() if todo.due_date else None,
            "category": todo.category,
            "tags": todo.tags,
        }
    
    def _log_history(
        self,
        db: Session,
        todo_id: int,
        user_id: int,
        action: str,
        changed_fields: Optional[List[str]] = None,
        old_values: Optional[Dict] = None,
        new_values: Optional[Dict] = None,
        confirmed_by_user: bool = False
    ):
        """记录操作历史。"""
        history = TodoHistory(
            todo_id=todo_id,
            user_id=user_id,
            action=action,
            changed_fields=changed_fields,
            old_values=old_values,
            new_values=new_values,
            confirmed_by_user=confirmed_by_user
        )
        db.add(history)
        db.commit()


# 全局 Repository 实例
todo_repo = TodoRepository()
