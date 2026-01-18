
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
