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

---

## 特殊实现：chat_repo

`chat_repo.py` 实现了对话消息的存储，包含特殊的去重和同步机制：

### 基于 Hash 的去重

使用内容的 MD5 短 hash 进行去重，避免微小差异导致重复保存：

```python
def _content_hash(content: str) -> str:
    """计算内容的短 hash，用于日志对比和去重。"""
    if not content:
        return "empty"
    return hashlib.md5(content.strip().encode()).hexdigest()[:8]

def save_conversation_from_messages(...):
    # 检查最近的消息是否有相同 hash
    for msg in recent_messages:
        if _content_hash(msg.content or "") == content_hash:
            # 如果内容相同但 extra_data 不同，更新 extra_data
            if extra_data and msg.extra_data != extra_data:
                msg.extra_data = extra_data
                db.commit()
            return  # 跳过重复保存
```

### Thinking 内容处理

确保思考内容在保存时正确包装：

```python
# 从 additional_kwargs 提取 thinking
thinking = additional_kwargs.get("reasoning_content") or additional_kwargs.get("thinking_content")

# 如果内容中没有 <think> 标签但有 thinking，将其包装后添加
if thinking and "<think>" not in ai_content:
    ai_content = f"<think>\n{thinking}\n</think>\n\n{ai_content}"
```

### 同步追踪日志

使用 `[SYNC-TRACE]` 前缀的日志，记录内容长度和 hash，方便排查同步问题：

```python
logger.info(
    "[SYNC-TRACE] 数据库保存完成: thread_id=%s, ai_len=%d, ai_hash=%s, extra_data_keys=%s",
    thread_id, len(ai_content), _content_hash(ai_content), list(extra_data.keys())
)
```
