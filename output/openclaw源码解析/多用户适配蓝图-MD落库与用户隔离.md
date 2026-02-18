# 多用户适配蓝图：MD 落库与用户隔离

> 创建日期：2026-02-18
> 适用项目：`/Users/jijingkun/bojxAI/fastapi`
> 核心问题：OpenClaw 用 MD 文件实现的 skill/memory/identity 机制，如何在多用户 DB 架构中落地？

---

## 1. 问题定义

OpenClaw 是单用户桌面 Agent，所有状态用本地 MD 文件存储：

| OpenClaw 文件 | 作用 | 你方现状 |
|---|---|---|
| `SKILL.md` | 技能定义与触发规则 | `t_agent_skills` 全局共享，无 user_id |
| `MEMORY.md` | 长期记忆（evergreen） | `t_user_memory` 已有 user_id 隔离 |
| `memory/YYYY-MM-DD*.md` | 会话沉淀日记 | 无对应实现 |
| `AGENTS.md` / identity | Agent 身份与行为规则 | Prompt 硬编码，无用户级定制 |
| `config.yaml` | 模型/队列/策略配置 | `t_system_config` 全局，无用户级覆盖 |

你的系统是多用户 SaaS，需要：

1. 所有 MD 内容落到 DB 表，以 `user_id` 隔离。
2. 创建用户时自动生成初始版本数据（skill 模版 + 空记忆 + 默认配置）。
3. 用户可独立启用/禁用/定制自己的 skill 集合，不影响其他用户。

---

## 2. 数据模型改造方案

### 2.1 Skill 层：引入 `t_user_skill_config`（用户级技能配置）

不改 `t_agent_skills`（保持为全局技能库），新增用户级配置表：

```sql
CREATE TABLE t_user_skill_config (
    id            BIGSERIAL PRIMARY KEY,
    user_id       INTEGER NOT NULL REFERENCES t_user(id),
    skill_id      VARCHAR(100) NOT NULL,  -- 关联 t_agent_skills.skill_id
    is_enabled    BOOLEAN NOT NULL DEFAULT true,
    auto_enabled  BOOLEAN NOT NULL DEFAULT true,
    priority      INTEGER NOT NULL DEFAULT 100,
    custom_trigger_phrases JSONB DEFAULT '[]'::jsonb,  -- 用户自定义触发词（覆盖全局）
    custom_config  JSONB DEFAULT '{}'::jsonb,           -- 用户级参数覆盖
    created_at    TIMESTAMP DEFAULT now(),
    updated_at    TIMESTAMP DEFAULT now(),
    UNIQUE(user_id, skill_id)
);
CREATE INDEX idx_user_skill_config_user ON t_user_skill_config(user_id);
```

查询逻辑：

```python
# 获取用户可用技能 = 全局技能 LEFT JOIN 用户配置
# 若用户配置存在 → 用用户的 is_enabled/priority/trigger_phrases
# 若用户配置不存在 → 用全局默认值
```

### 2.2 Memory 层：扩展 `t_user_memory` + 新增 `t_user_memory_file`

`t_user_memory` 已有 user_id 隔离，保持不变（偏好 KV）。

新增文件记忆表（对应 OpenClaw 的 `MEMORY.md` + 日记文件）：

```sql
CREATE TABLE t_user_memory_file (
    id            BIGSERIAL PRIMARY KEY,
    user_id       INTEGER NOT NULL REFERENCES t_user(id),
    file_type     VARCHAR(32) NOT NULL DEFAULT 'daily',  -- 'evergreen' | 'daily' | 'snapshot'
    file_key      VARCHAR(200) NOT NULL,  -- e.g. 'MEMORY' / '2026-02-18_session_abc'
    content       TEXT NOT NULL,
    embedding     vector(2048),           -- 可选，用于语义检索
    token_count   INTEGER,
    is_pinned     BOOLEAN DEFAULT false,  -- evergreen 文件不做时间衰减
    source_thread_id VARCHAR(100),
    created_at    TIMESTAMP DEFAULT now(),
    updated_at    TIMESTAMP DEFAULT now(),
    UNIQUE(user_id, file_key)
);
CREATE INDEX idx_user_memory_file_user ON t_user_memory_file(user_id);
CREATE INDEX idx_user_memory_file_type ON t_user_memory_file(user_id, file_type);
```

### 2.3 Identity 层：新增 `t_user_agent_profile`

对应 OpenClaw 的 `AGENTS.md` / identity 定制：

```sql
CREATE TABLE t_user_agent_profile (
    id            BIGSERIAL PRIMARY KEY,
    user_id       INTEGER NOT NULL REFERENCES t_user(id),
    profile_key   VARCHAR(100) NOT NULL,  -- e.g. 'system_prompt_override' / 'preferred_style'
    profile_value TEXT NOT NULL,
    is_active     BOOLEAN DEFAULT true,
    created_at    TIMESTAMP DEFAULT now(),
    updated_at    TIMESTAMP DEFAULT now(),
    UNIQUE(user_id, profile_key)
);
CREATE INDEX idx_user_agent_profile_user ON t_user_agent_profile(user_id);
```

### 2.4 Config 层：新增 `t_user_config_override`

对应 OpenClaw 的用户级 config 覆盖：

```sql
CREATE TABLE t_user_config_override (
    id            BIGSERIAL PRIMARY KEY,
    user_id       INTEGER NOT NULL REFERENCES t_user(id),
    config_key    VARCHAR(200) NOT NULL,  -- e.g. 'queue.mode' / 'model.primary'
    config_value  TEXT NOT NULL,
    created_at    TIMESTAMP DEFAULT now(),
    updated_at    TIMESTAMP DEFAULT now(),
    UNIQUE(user_id, config_key)
);
CREATE INDEX idx_user_config_override_user ON t_user_config_override(user_id);
```

---

## 3. 用户初始化方案

### 3.1 初始化时机

在 `UserService.create_user()` 成功后，调用 `UserInitializationService.initialize(user_id)`。

### 3.2 初始化内容

#### 3.2.1 Skill 模版（9 个）

从现有 ~180 个全局技能中选出 9 个作为新用户默认启用集：

| skill_id | 名称 | 选择理由 |
|---|---|---|
| `sql-expert` | SQL 专家 | 银行场景核心：数据查询 |
| `data-insight` | 数据洞察专家 | 银行场景核心：指标分析 |
| `todo-intent` | 待办意图识别 | 待办助手核心能力 |
| `knowledge-search` | 知识库检索专家 | RAG 检索核心能力 |
| `python-expert` | Python 专家 | 通用编程辅助 |
| `fastapi-expert` | FastAPI 专家 | 本项目技术栈匹配 |
| `database-design` | 数据库设计 | 银行数据建模场景 |
| `brainstorming` | 头脑风暴 | 通用创意与规划 |
| `copywriter` | 文案润色专家 | 报告/邮件润色 |

初始化逻辑：

```python
DEFAULT_SKILL_TEMPLATE = [
    "sql-expert", "data-insight", "todo-intent",
    "knowledge-search", "python-expert", "fastapi-expert",
    "database-design", "brainstorming", "copywriter",
]

def _init_user_skills(self, user_id: int, db: Session):
    for skill_id in DEFAULT_SKILL_TEMPLATE:
        config = UserSkillConfig(
            user_id=user_id,
            skill_id=skill_id,
            is_enabled=True,
            auto_enabled=True,
            priority=100,
        )
        db.add(config)
```

#### 3.2.2 Memory 初始化

创建一条 evergreen 记忆文件（等价 OpenClaw 的 `MEMORY.md`）：

```python
def _init_user_memory(self, user_id: int, db: Session):
    memory_file = UserMemoryFile(
        user_id=user_id,
        file_type="evergreen",
        file_key="MEMORY",
        content="# 用户长期记忆\n\n（系统将在对话中自动沉淀重要信息到此处）\n",
        is_pinned=True,
    )
    db.add(memory_file)
```

#### 3.2.3 Agent Profile 初始化

```python
def _init_user_profile(self, user_id: int, db: Session):
    defaults = [
        ("preferred_language", "zh-CN"),
        ("response_style", "professional"),
    ]
    for key, value in defaults:
        profile = UserAgentProfile(
            user_id=user_id,
            profile_key=key,
            profile_value=value,
        )
        db.add(profile)
```

### 3.3 完整初始化服务

```python
class UserInitializationService:
    """用户创建后的初始化服务：自动生成 skill 配置、记忆文件、Agent 档案。"""

    @classmethod
    def initialize(cls, user_id: int, db: Session):
        cls._init_user_skills(user_id, db)
        cls._init_user_memory(user_id, db)
        cls._init_user_profile(user_id, db)
        db.commit()
```

---

## 4. 查询层适配

### 4.1 Skill 检索适配

当前 `SkillService.search_skills()` 直接查 `t_agent_skills`，需改为：

```python
def search_skills_for_user(cls, user_id: int, query: str, ...):
    # 1. 从 t_agent_skills LEFT JOIN t_user_skill_config 获取用户视角的技能列表
    # 2. 过滤：用户配置 is_enabled=True 或 无用户配置但全局 is_enabled=True
    # 3. 按用户 priority 排序（用户配置优先，否则用全局 priority）
    # 4. 向量检索仍用 t_agent_skills.embedding
    # 5. trigger_phrases 合并：用户自定义 + 全局
```

### 4.2 Memory 检索适配

```python
def recall_memory_for_user(cls, user_id: int, query: str, ...):
    # 1. 从 t_user_memory_file WHERE user_id = ? 检索
    # 2. 优先 evergreen（is_pinned=True），再 daily
    # 3. 支持 vector search（若 embedding 存在）或 keyword fallback
    # 4. 与现有 t_user_memory（偏好 KV）合并注入
```

### 4.3 Config 解析适配

```python
def resolve_config(cls, user_id: int, key: str, default: Any):
    # 1. 先查 t_user_config_override WHERE user_id AND config_key
    # 2. 未命中则查 t_system_config
    # 3. 未命中则用代码默认值
```

---

## 5. 与迁移蓝图的对齐

| 蓝图阶段 | 多用户适配点 |
|---|---|
| P0 协议与证据 | 无直接影响（协议是 per-session，已有 thread_id 隔离） |
| P1 队列 | queue_state 按 thread_id 隔离（已满足） |
| P2 子任务 | subtask_registry 按 thread_id 隔离（已满足） |
| P2.5 记忆闭环 | **核心改造点**：`t_user_memory_file` 替代 MD 文件方案 |
| P3 运行时控制 | active_run 按 user_id + thread_id 隔离 |
| P4 策略分层 | **核心改造点**：`t_user_skill_config` + `t_user_config_override` 提供用户级策略 |
| P4.5 模型容错 | model override 可通过 `t_user_config_override` 实现用户级模型选择 |
| P5 恢复 | 无额外适配（已按 user/thread 隔离） |

---

## 6. 文件级改造清单

### 6.1 新增文件

| 文件 | 作用 |
|---|---|
| `app/models/user_skill_config.py` | `t_user_skill_config` ORM |
| `app/models/user_memory_file.py` | `t_user_memory_file` ORM |
| `app/models/user_agent_profile.py` | `t_user_agent_profile` ORM |
| `app/models/user_config_override.py` | `t_user_config_override` ORM |
| `app/services/user_initialization_service.py` | 用户初始化服务 |
| `alembic/versions/xxx_add_user_isolation_tables.py` | 数据库迁移 |

### 6.2 必改文件

| 文件 | 改造点 |
|---|---|
| `app/services/skill_service.py` | `search_skills` → `search_skills_for_user`，接入用户配置层 |
| `app/services/user_preference_memory_service.py` | 与 `t_user_memory_file` 协同（双源注入） |
| `app/services/chat_service.py` | 记忆注入链路增加 file memory recall |
| `app/api/v1/endpoints/user_api.py` | 注册/创建用户后调用初始化服务 |
| `app/api/v1/endpoints/skill_admin_api.py` | 增加用户级 skill 配置 CRUD 接口 |
| `app/models/__init__.py` | 注册新模型 |

---

## 7. 验收标准

1. 新建用户后，`t_user_skill_config` 自动生成 9 条记录。
2. 新建用户后，`t_user_memory_file` 自动生成 1 条 evergreen 记忆。
3. 用户 A 禁用 `sql-expert`，用户 B 不受影响。
4. Skill 检索结果尊重用户级 `is_enabled` 和 `priority`。
5. 用户级 config override 优先于全局 `t_system_config`。
6. 现有无用户配置的用户，行为与改造前一致（向后兼容）。

---

## 8. 回滚策略

- 新表可独立删除，不影响现有 `t_agent_skills` / `t_user_memory`。
- Skill 检索可通过 feature flag `USER_SKILL_ISOLATION_ENABLED` 切换新旧逻辑。
- 用户初始化失败不阻塞用户创建（catch + log + 后台补偿）。
