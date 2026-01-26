# Repository 模式解读

本文档解读项目中 Repository 模式的实践。

**目录**: `app/repositories/`

## 设计原则

Repository 层负责数据访问，隔离业务逻辑和数据库操作。

```
Service → Repository → Model → Database
```

---

## 典型实现

### TodoRepository

```python
class TodoRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, user_id: int, data: dict) -> Todo:
        """创建待办。"""
        todo = Todo(user_id=user_id, **data)
        self.db.add(todo)
        self.db.commit()
        self.db.refresh(todo)
        return todo
    
    def find_by_id(self, todo_id: int) -> Optional[Todo]:
        """根据 ID 查询。"""
        return self.db.query(Todo).filter(Todo.id == todo_id).first()
    
    def find_by_user(
        self, 
        user_id: int, 
        status: Optional[str] = None
    ) -> List[Todo]:
        """查询用户待办列表。"""
        query = self.db.query(Todo).filter(Todo.user_id == user_id)
        if status:
            query = query.filter(Todo.status == status)
        return query.order_by(Todo.created_at.desc()).all()
    
    def update(self, todo_id: int, data: dict) -> Optional[Todo]:
        """更新待办。"""
        todo = self.find_by_id(todo_id)
        if not todo:
            return None
        for key, value in data.items():
            if value is not None:
                setattr(todo, key, value)
        self.db.commit()
        self.db.refresh(todo)
        return todo
    
    def delete(self, todo_id: int) -> bool:
        """删除待办。"""
        todo = self.find_by_id(todo_id)
        if not todo:
            return False
        self.db.delete(todo)
        self.db.commit()
        return True
```

---

## 使用方式

### 在 Service 中

```python
class TodoService:
    def __init__(self, db: Session):
        self.repo = TodoRepository(db)
    
    def create_todo(self, user_id: int, title: str) -> Todo:
        return self.repo.create(user_id, {"title": title})
```

### 在 Tool 中

```python
@tool
def add_todo(title: str, config: RunnableConfig) -> str:
    user_id = get_user_id_from_config(config)
    with get_db_context() as db:
        repo = TodoRepository(db)
        todo = repo.create(user_id, {"title": title})
        return f"创建成功: {todo.title}"
```

---

## 设计要点

1. **返回模型对象**: Repository 返回 ORM 对象，不返回字典
2. **事务边界**: Repository 内部处理 commit/rollback
3. **聚合根**: 每个 Repository 对应一个主表
4. **保持简单**: Repository 只做数据访问，不含业务逻辑
