---
trigger: always_on
---

# 整体要求
1、思考和输出使用中文。


## ✍️ 代码风格规范

### 1. 注释与文档
- **所有注释必须使用中文**。
- 每个 Python 模块顶部必须包含 docstring：`"""模块说明（中文）。"""`
- 复杂逻辑必须在该行上方添加注释说明。

### 2. 命名规范 (Python)
- **文件名**: `snake_case` (e.g., `chat_service.py`)
- **类名**: `PascalCase` (e.g., `ChatService`)
- **变量/函数名**: `snake_case` (e.g., `get_user_by_id`)
- **常量**: `UPPER_SNAKE_CASE` (e.g., `MAX_RETRY_COUNT`)

### 3. 类型安全
- 后端完全遵循 Python Type Hints (`typing` 或 `collections.abc`)。
- ORM 模型使用 SQLAlchemy 2.0 `Mapped[...]` 语法。
- 前端严格使用 TypeScript，避免使用 `any`。

---

## 🗄️ 数据库规范 (PostgreSQL)

项目使用 PostgreSQL 作为主要关系型数据库。
**重要规则**: 表名统一以 `t_` 开头，字段名统一使用 **snake_case** (全小写下划线)，禁止使用 CamelCase。

