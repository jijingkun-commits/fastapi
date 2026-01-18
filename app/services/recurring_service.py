"""重复任务服务（中文注释）。

处理重复任务的自动生成逻辑。
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy.orm import Session

from app.models.todo import Todo
from app.repositories.todo_repository import todo_repo

logger = logging.getLogger(__name__)


class RecurringService:
    """重复任务服务。"""
    
    @staticmethod
    def generate_next_occurrence(
        db: Session,
        recurring_todo: Todo,
        base_date: Optional[datetime] = None
    ) -> Optional[Todo]:
        """根据重复规则生成下一次任务实例。
        
        Args:
            db: 数据库会话
            recurring_todo: 重复任务模板
            base_date: 基准日期（默认使用当前任务的截止日期）
            
        Returns:
            新创建的任务实例，如果无法生成则返回 None
        """
        if not recurring_todo.is_recurring:
            logger.warning(f"任务 {recurring_todo.id} 不是重复任务")
            return None
        
        # 使用基准日期或当前任务的截止日期
        base = base_date or recurring_todo.due_date or datetime.now()
        
        # 计算下一次截止日期
        next_due = RecurringService._calculate_next_due_date(
            base,
            recurring_todo.recurrence_pattern,
            recurring_todo.recurrence_interval,
            recurring_todo.recurrence_days
        )
        
        if not next_due:
            return None
        
        # 检查是否超过结束日期
        if recurring_todo.recurrence_end_date and next_due > recurring_todo.recurrence_end_date:
            logger.info(f"重复任务 {recurring_todo.id} 已到期")
            return None
        
        # 创建新任务实例
        new_todo = Todo(
            user_id=recurring_todo.user_id,
            title=recurring_todo.title,
            description=recurring_todo.description,
            priority=recurring_todo.priority,
            category=recurring_todo.category,
            tags=recurring_todo.tags,
            due_date=next_due,
            start_time=RecurringService._calculate_start_time(next_due, recurring_todo.start_time, base),
            reminder_enabled=recurring_todo.reminder_enabled,
            reminder_type=recurring_todo.reminder_type,
            reminder_advance_minutes=recurring_todo.reminder_advance_minutes,
            # 关联到原重复任务
            parent_recurring_id=recurring_todo.id,
            is_recurring=False,  # 实例本身不是重复任务
            status="todo",
            progress=0,
            create_time=datetime.now(),
            update_time=datetime.now()
        )
        
        db.add(new_todo)
        db.commit()
        db.refresh(new_todo)
        
        logger.info(f"已生成重复任务实例: {new_todo.id} (来自模板 {recurring_todo.id})")
        return new_todo
    
    @staticmethod
    def _calculate_next_due_date(
        base_date: datetime,
        pattern: str,
        interval: int,
        days: Optional[List[int]] = None
    ) -> Optional[datetime]:
        """计算下一次截止日期。
        
        Args:
            base_date: 基准日期
            pattern: 重复模式 (daily, weekly, monthly)
            interval: 间隔
            days: 星期几（仅 weekly 使用）
            
        Returns:
            下一次截止日期
        """
        if pattern == "daily":
            return base_date + timedelta(days=interval)
        
        elif pattern == "weekly":
            # 如果指定了星期几
            if days:
                # 找到下一个符合条件的星期几
                current_weekday = base_date.weekday()  # 0=周一, 6=周日
                
                # 转换为 1-7 格式（1=周一）
                days_sorted = sorted([d for d in days if d >= 1 and d <= 7])
                
                for target_day in days_sorted:
                    target_weekday = target_day - 1  # 转回 0-6
                    days_ahead = (target_weekday - current_weekday) % 7
                    
                    if days_ahead == 0:
                        days_ahead = 7  # 下一周的同一天
                    
                    next_date = base_date + timedelta(days=days_ahead)
                    return next_date
            else:
                # 没指定星期几，按周数间隔
                return base_date + timedelta(weeks=interval)
        
        elif pattern == "monthly":
            # 下个月的同一天
            next_month = base_date.month + interval
            next_year = base_date.year
            
            while next_month > 12:
                next_month -= 12
                next_year += 1
            
            # 处理月末日期（如1月31日 → 2月28日）
            try:
                return base_date.replace(year=next_year, month=next_month)
            except ValueError:
                # 如果日期不存在（如2月31日），使用该月最后一天
                import calendar
                last_day = calendar.monthrange(next_year, next_month)[1]
                return base_date.replace(year=next_year, month=next_month, day=last_day)
        
        return None
    
    @staticmethod
    def _calculate_start_time(
        next_due: datetime,
        original_start: Optional[datetime],
        base_date: datetime
    ) -> Optional[datetime]:
        """计算下一次的开始时间。"""
        if not original_start:
            return None
        
        # 计算原始任务中开始时间和截止时间的差值
        time_diff = base_date - original_start
        
        # 应用到下一次
        return next_due - time_diff
    
    @staticmethod
    def batch_generate_upcoming(
        db: Session,
        user_id: int,
        days_ahead: int = 7
    ) -> List[Todo]:
        """批量生成未来N天的重复任务实例。
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            days_ahead: 提前生成的天数
            
        Returns:
            新创建的任务列表
        """
        # 获取所有重复任务模板
        recurring_templates = todo_repo.list_by_user(
            db,
            user_id,
            limit=1000
        )
        
        recurring_templates = [
            t for t in recurring_templates 
            if t.is_recurring and not t.is_deleted
        ]
        
        generated = []
        cutoff_date = datetime.now() + timedelta(days=days_ahead)
        
        for template in recurring_templates:
            # 检查是否已有实例
            existing = db.query(Todo).filter(
                Todo.parent_recurring_id == template.id,
                Todo.due_date > datetime.now(),
                Todo.due_date <= cutoff_date
            ).first()
            
            if not existing:
                # 生成新实例
                new_todo = RecurringService.generate_next_occurrence(db, template)
                if new_todo:
                    generated.append(new_todo)
        
        logger.info(f"为用户 {user_id} 生成了 {len(generated)} 个重复任务实例")
        return generated


# 单例服务
recurring_service = RecurringService()
