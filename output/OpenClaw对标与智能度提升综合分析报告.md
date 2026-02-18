# OpenClaw 对标与智能度提升综合分析报告

> 生成时间：2026-02-18
> 对标项目：`/Users/jijingkun/bojxAI/bot/openclaw`（源码级分析，非推测）
> 当前项目：`/Users/jijingkun/bojxAI/fastapi`
> 本报告整合了对标评分、四大核心问题深挖、已落地记忆 MVP 及五项评估

---

## 一、对标总览

### 评分矩阵（5 分制）

| 能力维度 | OpenClaw | 本项目 | 差距 | 改进难度 | 备注 |
|---------|---------|--------|------|---------|------|
| 记忆层 | 4.5 | 2.5 | ★★ | 中 | MVP 已落地，差距缩小 |
| 技能/插件治理 | 4.5 | 0.5 | ★★★★ | 高 | |
| 工具编排与策略 | 4.5 | 1.0 | ★★★ | 中（已有 V0.1 方案） | |
| 意图路由 | 3.5 | 3.0 | ★ | 低 | 本项目 Schema 路由优于 OpenClaw |
| 安全护栏 | 3.5 | 2.5 | ★ | 低 | 输入/输出层面本项目更强 |
| 子 Agent 编排 | 4.0 | 2.0 | ★★ | 中 | |
| 可观测性 | 3.5 | 2.0 | ★★ | 中 | |

### 一句话结论

OpenClaw 的核心优势不在于单个工具有多强，而在于**三层治理架构**（记忆治理 + 技能治理 + 工具治理）形成了一个自适应的"操作系统"。本项目在意图路由和安全护栏上有不错的基础，记忆层 MVP 已落地（偏好提取 + 冲突去重 + 摘要压缩），但在技能、工具两个核心治理层存在系统性缺失。

### 补充校准（2026-02-18）

结合本轮针对 OpenClaw 的执行机制复盘，结论进一步收敛为：

- OpenClaw 的“看起来会自己做事”主要来自**多层规则 + 固定执行协议 + 权限/观测边界**，而不是先堆大量 skill 描述。
- 在本项目中，skill 应定位为“能力目录”，执行闭环应由 `execution_mode + checklist + done_criteria + evidence` 驱动。
- 优先级建议调整为：先补齐“调研执行协议与收敛门禁”，再扩 skill 数量。
- 详细方案已沉淀在 `output/执行协议设计与诊断工具方案.md`（摘要融合版）。

---

## 二、记忆层：已落地 MVP + OpenClaw 借鉴 + 五项评估

### 2.1 已完成实现（已提交）

跨会话用户偏好记忆 MVP 已落地并提交两个 commit：

| 提交 | 内容 |
|------|------|
| `d45ad49` feat(chat): add cross-session user preference memory MVP | 基础偏好提取 + DB 持久化 + 上下文注入 |
| `6799014` feat(memory): dedupe conflicts and compress preference context | 冲突去重 + 摘要压缩增强 |

关键文件：

| 类型 | 文件 |
|------|------|
| 表与迁移 | `alembic/versions/20260216_0009_create_user_memory_table.py` |
| 模型 | `app/models/user_memory.py`（已注册到 `__init__.py`、`alembic/env.py`） |
| 仓储 | `app/repositories/user_memory_repo.py` |
| 服务 | `app/services/user_preference_memory_service.py` |
| 接入聊天 | `app/services/chat_service.py` |
| 配置 | `app/core/config.py`、`.env.example` |
| 单测 | `tests/unit/test_user_preference_memory_service.py` |
| SQL 初始化 | `install/sql/init_postgres.sql` |

### 2.2 当前记忆机制

```
┌─────────────────────────────────────────────────────────┐
│              当前记忆架构（已落地）                        │
│                                                         │
│  存储层: t_user_memory (chat_db)                         │
│    - 按 user_id 隔离                                     │
│    - memory_key / memory_value 键值对                    │
│                                                         │
│  写入层: 聊天流程中识别"偏好表达"并提取后写库              │
│    - 规则/触发表达驱动                                    │
│    - 明确表达（"记住.../以后默认..."）命中率更高           │
│                                                         │
│  读取层: 每轮生成时读取用户偏好并注入系统上下文            │
│    - 排序: update_time DESC, id DESC                     │
│    - 限制: USER_PREFERENCE_MEMORY_MAX_ITEMS (可调至 20)  │
│                                                         │
│  质量策略（已实现）:                                      │
│    - 冲突去重: 同 key 仅保留最新值                        │
│    - 文本压缩: 上下文过长时做摘要压缩                     │
│    - 避免全量注入（上下文污染 + 冲突信息 + token 成本）    │
└─────────────────────────────────────────────────────────┘
```

关于"全量注入"的结论：全量注入会带来三类问题——上下文污染、冲突信息并存、token 成本上升。因此采用"有上限 + 最近优先 + 去重 + 压缩"的组合策略。阈值可调到 20，但已配套去重/压缩，不是简单放大。

### 2.3 OpenClaw 记忆架构（仅作思想借鉴）

OpenClaw 的主记忆形态是**工作区文件**（`MEMORY.md` + `memory/YYYY-MM-DD.md`），不是数据库优先。本项目用 DB 落地更适合业务系统与可治理性。

```
┌─────────────────────────────────────────────────────────┐
│              OpenClaw 记忆架构（参考）                     │
│                                                         │
│  MEMORY.md (持久事实层)                                   │
│    - 跨会话持久化的用户事实/偏好                           │
│    - 手动 + 自动提取                                      │
│                                                         │
│  memory/YYYY-MM-DD.md (会话上下文层)                      │
│    - 每日会话摘要，自动归档                                │
│                                                         │
│  Compaction (压缩机制)                                    │
│    - 上下文窗口即将溢出时触发                              │
│    - 压缩前先 flush 记忆 → 防"晚期健忘症"                 │
│    - 保留最近 N 条 + 摘要                                 │
│                                                         │
│  Hybrid Search (混合检索)                                 │
│    - Vector (语义相似) + BM25 (关键词精确)                 │
│    - MMR 去重 + 时间衰减                                  │
│    - 多后端自动降级 (OpenAI→Gemini→本地)                   │
│    - 结果带 path + line 引用                              │
└─────────────────────────────────────────────────────────┘
```

可借鉴的两条机制：
1. **会话切换时自动沉淀**（`/new` hook 写摘要）
2. **预压缩前静默 memory flush**（防止上下文被压缩丢失）

本地实测状态：memory-core 插件启用，memory-lancedb 未启用，embedding key 未配置完整，语义检索能力实际不可用。

### 2.4 差距分析（更新后）

| 能力 | OpenClaw | 本项目（MVP 后） | 影响 |
|------|---------|-----------------|------|
| 持久事实记忆 | MEMORY.md 自动提取 | 规则提取 + DB 持久化 ✅ | 基础能力已有，提取范围待扩展 |
| 冲突去重 | 无明确机制 | 同 key 去重 ✅ | 本项目更优 |
| 上下文压缩 | Pre-compaction flush + 摘要 | 摘要压缩 ✅，无 pre-compaction flush | 长对话仍有"晚期健忘症"风险 |
| 会话摘要 | 每日自动归档 | 无 ❌ | 跨会话上下文延续弱 |
| 记忆检索 | Vector + BM25 + MMR + 时间衰减 | 无检索（仅 DB 查询最近偏好）❌ | 无法从历史对话中召回相关信息 |
| 引用溯源 | path + line number | 无 ❌ | 无法追溯记忆来源 |
| 用户可见性 | 无管理界面 | 无管理界面 ❌ | 用户无法查看/纠正偏好 |

### 2.5 五项重点评估

#### 评估 1: 偏好抽取规则是否足够稳健？是否需要"确认式写入"？

**现状**：规则/触发表达驱动，不要求严格固定格式。明确表达（"记住.../以后默认..."）命中率高，隐式偏好（如用户反复使用某种查询模式）无法捕获。

**评估结论**：当前规则对"显式偏好"够用，但对"隐式偏好"无能为力。

**建议方案**：引入置信度分级 + 确认式写入

```
偏好表达识别
    ↓
置信度评估:
  - 高置信 (≥0.8): "记住我喜欢..." / "以后默认..." → 直接写入
  - 中置信 (0.5-0.8): "我通常看零售的" → 写入但标记 tentative
  - 低置信 (<0.5): 隐式模式推断 → 追问确认后写入
    ↓
确认式写入 (低置信时):
  AI: "我注意到你最近几次都在查零售存款数据，要不要我记住'默认查零售'？"
  用户: "好的" → 写入
  用户: "不用" → 丢弃
```

实现难度：中。需要在偏好提取服务中增加 `confidence` 字段，并在 postprocess 中增加追问逻辑。

#### 评估 2: 偏好数据模型是否需要版本化？

**现状**：`t_user_memory` 表仅有 `memory_key`、`memory_value`、`update_time`，无版本/生效时间/来源信息。

**评估结论**：需要。银行业务场景中偏好会随时间变化（如"上季度关注对公，本季度关注零售"），且合规要求可追溯。

**建议数据模型扩展**：

```sql
ALTER TABLE t_user_memory ADD COLUMN version INT DEFAULT 1;
ALTER TABLE t_user_memory ADD COLUMN confidence FLOAT DEFAULT 1.0;
ALTER TABLE t_user_memory ADD COLUMN source_thread_id VARCHAR(64);
ALTER TABLE t_user_memory ADD COLUMN source_message_id VARCHAR(64);
ALTER TABLE t_user_memory ADD COLUMN effective_from TIMESTAMP;
ALTER TABLE t_user_memory ADD COLUMN effective_until TIMESTAMP;  -- NULL = 永久有效
ALTER TABLE t_user_memory ADD COLUMN status VARCHAR(20) DEFAULT 'active';
  -- active / tentative / expired / deleted_by_user
```

关键设计：
- `version`：同 key 多版本共存，注入时取最新 active 版本
- `confidence`：低置信度的偏好标记为 `tentative`，可被后续高置信度覆盖
- `source_thread_id` + `source_message_id`：溯源到具体对话，满足合规审计
- `effective_until`：支持时效性偏好（如"本月关注..."）

#### 评估 3: 注入策略是否应分层（硬偏好/软偏好）？

**评估结论**：应该分层。不同类型的偏好对 Agent 行为的约束力不同。

**建议分层方案**：

| 层级 | 定义 | 注入方式 | 限额 | 示例 |
|------|------|---------|------|------|
| 硬偏好 | 用户明确设定的强约束 | 注入 system prompt，每轮必带 | 5 条 | "回复用中文"、"默认查零售数据" |
| 软偏好 | 推断或低置信度的倾向 | 注入 user context，可被当轮覆盖 | 10 条 | "通常关注存款余额"、"偏好表格展示" |
| 历史上下文 | 跨会话的事实记忆 | 仅在相关时检索注入 | 按相关性 top-K | "上次查了A分行贷款数据" |

```python
def build_memory_context(user_id: int, current_query: str) -> dict:
    """分层构建记忆上下文"""
    hard = memory_repo.get_by_user(user_id, status="active", confidence_gte=0.8, limit=5)
    soft = memory_repo.get_by_user(user_id, status="active", confidence_lt=0.8, limit=10)
    # 历史上下文（Phase 2，需要检索能力）
    # history = memory_search(user_id, current_query, top_k=3)
    
    return {
        "hard_preferences": format_preferences(hard),   # → system prompt
        "soft_preferences": format_preferences(soft),    # → user context
        # "relevant_history": format_history(history),   # → user context (Phase 2)
    }
```

#### 评估 4: 是否引入"预压缩前自动沉淀"？

**评估结论**：应该引入。这是 OpenClaw "越用越聪明"的核心机制之一。

**当前风险**：LangGraph 的 `trim_messages` 在上下文窗口接近上限时裁剪旧消息，但裁剪前不会保存其中的偏好/事实信息，导致"晚期健忘症"——对话越长，早期提到的偏好越容易丢失。

**建议方案**：在 preprocess 节点中增加 memory flush 检查

```python
# app/ai/workflow/chat_graph.py 的 preprocess 节点中

async def _preprocess(state: AgentState) -> AgentState:
    messages = state["messages"]
    
    # 检查是否即将触发压缩
    total_tokens = estimate_token_count(messages)
    if total_tokens > COMPACTION_THRESHOLD * 0.8:  # 接近阈值时提前 flush
        # 从即将被裁剪的旧消息中提取偏好
        old_messages = messages[:len(messages) // 2]  # 前半部分可能被裁剪
        await extract_and_save_preferences(
            user_id=state["user_id"],
            messages=old_messages,
            source="pre_compaction_flush"
        )
    
    # 继续正常 preprocess...
```

实现难度：低。核心逻辑是在 trim 之前多做一次偏好提取，复用已有的提取服务。

#### 评估 5: 用户可见的记忆管理接口

**评估结论**：必须提供。这是合规要求（用户数据可控），也是产品体验要求（用户能纠正错误偏好）。

**建议 API 设计**：

```
GET    /api/v1/memory/preferences          # 查看我的所有偏好
GET    /api/v1/memory/preferences/{key}     # 查看特定偏好的历史版本
PUT    /api/v1/memory/preferences/{key}     # 手动修改偏好值
DELETE /api/v1/memory/preferences/{key}     # 删除偏好（标记 deleted_by_user）
POST   /api/v1/memory/preferences/reset     # 重置所有偏好
```

**前端 UI 建议**：

```
┌─────────────────────────────────────────┐
│  我的偏好设置                            │
│                                         │
│  ┌─────────────────────────────────────┐│
│  │ 回复语言: 中文           [编辑][删除]││
│  │ 来源: 2026-02-16 对话    置信度: 高  ││
│  └─────────────────────────────────────┘│
│  ┌─────────────────────────────────────┐│
│  │ 默认数据范围: 零售        [编辑][删除]││
│  │ 来源: 2026-02-17 对话    置信度: 中  ││
│  └─────────────────────────────────────┘│
│  ┌─────────────────────────────────────┐│
│  │ 关注指标: 存款余额        [编辑][删除]││
│  │ 来源: 系统推断           置信度: 低  ││
│  │ ⚠️ 低置信度，点击确认或删除          ││
│  └─────────────────────────────────────┘│
│                                         │
│  [重置所有偏好]                          │
└─────────────────────────────────────────┘
```

### 2.6 记忆层改进路线

| 阶段 | 目标 | 工作量 | 前置条件 |
|------|------|--------|---------|
| M0 ✅ | 偏好提取 + DB 持久化 + 去重 + 压缩 | 已完成 | - |
| M1 | 数据模型版本化（评估 2）+ 分层注入（评估 3） | 1 周 | M0 |
| M2 | 置信度 + 确认式写入（评估 1） | 1 周 | M1 |
| M3 | 预压缩前自动沉淀（评估 4） | 0.5 周 | M0 |
| M4 | 用户记忆管理 API + 前端（评估 5） | 1-2 周 | M1 |
| M5 | 会话摘要（借鉴 OpenClaw 每日归档） | 1 周 | M0 |
| M6 | 混合检索（pgvector + BM25） | 2-3 周 | M5 |

---

## 三、工具编排与策略

### 3.1 Q1: 工具动态加载

#### OpenClaw 做法：半动态

| 类型 | 加载方式 | 关键文件 |
|------|---------|---------|
| 内置工具 | `createOpenClawTools()` 硬编码注册，通过 Tool Policy Pipeline 动态过滤 | `openclaw-tools.ts` |
| 插件工具 | `jiti` (Just-In-Time Importer) 真正动态加载 `.ts/.js` 文件 | `plugins/loader.ts`, `plugins/tools.ts` |

插件动态加载链路：

```
~/.openclaw/plugins/ 或 workspace/plugins/
    ↓ jiti 动态导入
loadOpenClawPlugins({ config, workspaceDir })
    ↓ Schema 验证 + 权限检查
resolvePluginTools({ context, existingToolNames, toolAllowlist })
    ↓ 动态过滤（existingToolNames 防覆盖内置工具）
最终工具集
```

#### 本项目实现方案

| 阶段 | 内容 | 工作量 |
|------|------|--------|
| Phase 1 | API 触发重载：在 `app/ai/tools/` 下建立 Tool Registry，管理 API 触发工具集重新加载，无需重启 | 1 周 |
| Phase 2 | 插件目录扫描：从约定目录（如 `plugins/`）动态加载自定义工具，每个插件导出标准 Tool Schema | 2 周 |

### 3.2 Q4: 工具的用户级隔离

#### OpenClaw 的 7 层策略管线

```
输入: 全量工具集
    ↓
L1: Profile Policy (minimal/coding/messaging/full)
    ↓ stripPluginOnlyAllowlist
L2: Provider Profile Policy (按 LLM 提供商)
    ↓ stripPluginOnlyAllowlist
L3: Global Policy (全局允许列表)
    ↓ stripPluginOnlyAllowlist
L4: Global Provider Policy (全局按提供商)
    ↓ stripPluginOnlyAllowlist
L5: Agent Policy (按具体 Agent ID)
    ↓ stripPluginOnlyAllowlist
L6: Agent Provider Policy (Agent + 提供商组合)
    ↓ stripPluginOnlyAllowlist
L7: Group Policy (工具组策略)
    ↓
输出: 过滤后的工具集
```

关键安全机制——`stripPluginOnlyAllowlist`：当 allowlist 中只包含插件工具名（不包含任何核心工具名）时，自动忽略该 allowlist，防止配置错误导致核心工具被意外禁用。

工具分组机制：

```typescript
const TOOL_GROUPS = {
  "group:memory": ["memory_search", "memory_get"],
  "group:web": ["web_search", "web_fetch"],
  "group:fs": ["read", "write", "edit", "apply_patch"],
  "group:runtime": ["exec", "process"],
  "group:sessions": ["sessions_list", "sessions_spawn", ...],
};

const TOOL_PROFILES = {
  minimal: { allow: ["session_status"] },
  coding: { allow: ["group:fs", "group:runtime", "group:sessions", "group:memory"] },
  messaging: { allow: ["group:messaging", "sessions_list", ...] },
  full: { allow: ["group:openclaw"] },  // 所有工具
};
```

#### 本项目现状与改进

现状：无用户级工具隔离，所有 Agent 看到相同工具集，`permission_service.py` 未与工具层打通。

改进方案：

| 阶段 | 内容 | 工作量 |
|------|------|--------|
| Phase 1 | 按 user_role 过滤：工具分组 + 角色 Profile（admin/analyst/user） | 1 周 |
| Phase 2 | 按 user_id 个性化：用户级 allow/deny 覆盖 | 1 周 |
| Phase 3 | Skill 可见性：`t_agent_skills` 增加 `visibility` 字段 | 1-2 周 |

Phase 1 核心代码：

```python
TOOL_GROUPS = {
    "group:data": ["data_query", "chart_generation", "sql_executor"],
    "group:todo": ["todo_create", "todo_update", "todo_list", "todo_delete"],
    "group:knowledge": ["knowledge_search", "ragflow_search"],
    "group:admin": ["system_config", "user_management", "model_management"],
}

ROLE_PROFILES = {
    "admin":   {"allow": ["group:data", "group:todo", "group:knowledge", "group:admin"]},
    "analyst": {"allow": ["group:data", "group:knowledge"]},
    "user":    {"allow": ["group:todo", "group:knowledge"]},
}
```

### 3.3 工具层现状对比

| 能力 | OpenClaw | 本项目 |
|------|---------|--------|
| 统一注册中心 | `createOpenClawTools()` + 插件 loader | 手动拼装 `_get_supervisor_tools()` |
| 策略管线 | 7 层 Pipeline | 无（V0.1 方案已设计 4 层） |
| 工具分组 | `group:xxx` 展开 | 无 |
| 用户级隔离 | Profile + Agent + Provider 三维度 | 无 |
| 动态加载 | jiti 插件加载 | 无（需重启） |
| 安全兜底 | `stripPluginOnlyAllowlist` | 无 |
| before/after 钩子 | 有 | 无 |

---

## 四、多意图拆分与并行 Agent 调度（Q2）

### OpenClaw 的 Subagent 架构

OpenClaw 不在 Supervisor 层做"多意图拆分"，而是通过 **Subagent 工具** 让 Agent 自主 spawn 子任务。

```
┌─────────────────────────────────────────────────────────┐
│                  Subagent 编排架构                        │
│                                                         │
│  subagents-tool.ts (操作接口)                            │
│    - list: 列出活跃/最近的子 Agent                       │
│    - kill: 终止子 Agent（支持级联终止所有后代）            │
│    - steer: 向运行中的子 Agent 发送新指令（中断+重启）     │
│                                                         │
│  sessions-spawn-tool.ts (生成接口)                       │
│    - 创建独立 Session，分配唯一 sessionKey               │
│    - 支持模型覆盖、超时设置、cleanup 策略                 │
│    - 通过 Gateway RPC 异步启动                           │
│                                                         │
│  subagent-registry.ts (生命周期管理)                     │
│    - SubagentRunRecord: 完整运行记录                     │
│    - 磁盘持久化 + 内存缓存                               │
│    - lifecycle 事件监听 (start/end/error)                │
│    - 完成后 announce flow (结果回传给请求者)              │
│    - 自动归档 (archiveAfterMinutes, 默认 60 分钟)        │
│                                                         │
│  subagent-depth.ts (深度控制)                            │
│    - maxSpawnDepth 限制嵌套层级（默认 1）                 │
│    - 叶子 Agent 看到兄弟，编排 Agent 看到子代             │
└─────────────────────────────────────────────────────────┘
```

Steer 机制（源码级）——允许父 Agent 在子 Agent 运行过程中修改任务方向：

```
steer 调用流程:
1. 速率限制检查 (同一对 caller→child 间隔 ≥ 2s)
2. 禁止自我 steer
3. markSubagentRunForSteerRestart() → 抑制旧 run 的 announce
4. abortEmbeddedPiRun() → 中断当前生成
5. clearSessionQueues() → 清空队列
6. callGateway("agent.wait") → 等待中断生效 (最多 5s)
7. callGateway("agent") → 以新 message 重启子 Agent
8. replaceSubagentRunAfterSteer() → 用新 runId 替换旧记录
```

### 本项目改进方案

| 阶段 | 内容 | 工作量 | 前置条件 |
|------|------|--------|---------|
| Level 1 | Supervisor 多意图拆分 + LangGraph `Send()` 并行分发 | 2 周 | 无 |
| Level 2 | 子 Agent Session 隔离 + 结果汇总 | 2-3 周 | Level 1 |
| Level 3 | Steer/Kill 操作 + 级联终止 | 3-4 周 | Level 2 |

Level 1 核心思路：

```python
# multi_agent_graph.py 的 Supervisor 节点中
def supervisor_node(state):
    intents = classify_multi_intent(state["messages"][-1])
    if len(intents) == 1:
        return Command(goto=intents[0].route_to)
    else:
        # 并行分发到多个 Agent
        return [Send(intent.route_to, {"task": intent.description}) for intent in intents]
```

### 本项目现状对比

| 能力 | OpenClaw | 本项目 |
|------|---------|--------|
| 子 Agent 生成 | spawn + 隔离运行 | 无 |
| 任务编排 | steer/kill/list | 无 |
| 深度追踪 | depth counter | 无 |
| 后台任务 | session spawn + cleanup | 无 |
| 结果回传 | announce back | 无 |

当前银行业务场景（问数 + 待办）影响有限。当需要支持"帮我同时查三个分行的数据并汇总"这类并行任务时，才会成为瓶颈。

---

## 五、追问/消息队列机制（Q3）

### OpenClaw 的 Followup Queue 系统

| 模式 | 行为 | 适用场景 |
|------|------|---------|
| `"collect"` | 收集多个消息后一起处理（默认） | 用户连续发多条补充信息 |
| `"steer"` | 立即处理，允许中断当前生成 | 用户想改变方向 |
| `"interrupt"` | 强制中断当前生成，处理新消息 | 紧急修正 |
| `"queue"` | 严格队列，等待当前完成 | 保证顺序执行 |
| `"steer-backlog"` | 混合模式 | 复杂编排场景 |

配套机制：
- 3 种去重策略：`message-id`（按消息 ID）、`prompt`（按内容）、`none`（不去重）
- 3 种丢弃策略：`old`（丢旧）、`new`（丢新）、`summarize`（摘要合并）
- Debounce 机制：可配置延迟（默认 1000ms），防止频繁触发
- 容量限制：默认 20 条消息，超出按策略处理

工作流：

```
新消息到达
    ↓
enqueueFollowupRun() → 加入队列 (去重检查)
    ↓
触发防抖计时器 (debounceMs)
    ↓ 防抖时间到
scheduleFollowupDrain() → 开始处理
    ↓
根据 mode 决定行为:
  - queue: 等待当前完成后处理
  - collect: 合并队列中所有消息后一起处理
  - steer: 中断当前生成，立即处理
    ↓
逐个/批量处理队列消息
    ↓
处理完后继续检查队列，直到为空
```

### 本项目现状

完全没有队列机制。Agent 正在生成回复时，新消息的行为取决于前端实现——通常是阻塞或丢弃。

### 改进方案

| 阶段 | 内容 | 工作量 |
|------|------|--------|
| Phase 1 | 基础队列 + `"queue"` 模式（FIFO + 去重） | 1-2 周 |
| Phase 2 | `"collect"` 模式 + 防抖（合并多条消息） | 1 周 |
| Phase 3 | `"interrupt"` 模式（需 LangGraph 中断配合） | 2 周 |

Phase 1 核心代码：

```python
# app/ai/queue/followup_queue.py
@dataclass
class FollowupItem:
    prompt: str
    message_id: Optional[str] = None
    enqueued_at: float = field(default_factory=time.time)

@dataclass
class FollowupQueue:
    items: deque = field(default_factory=deque)
    draining: bool = False
    max_size: int = 10
    
    def enqueue(self, item: FollowupItem) -> bool:
        if len(self.items) >= self.max_size:
            return False
        if item.message_id:
            for existing in self.items:
                if existing.message_id == item.message_id:
                    return False
        self.items.append(item)
        return True

# 每个 thread_id 维护一个队列
_queues: dict[str, FollowupQueue] = {}
```

前端需配合：
1. "消息已排队"的 UI 反馈（显示队列位置）
2. 队列中消息的取消操作
3. Agent 正在处理时的输入框状态提示

---

## 六、技能/插件治理

### OpenClaw 技能架构

```
┌─────────────────────────────────────────────────────────┐
│            OpenClaw 技能治理架构                          │
│                                                         │
│  多源技能优先级                                           │
│    workspace (最高) > managed > bundled                   │
│    + plugin skills                                       │
│                                                         │
│  热刷新 (Hot Refresh)                                    │
│    - chokidar 文件监听 + debounce                        │
│    - 全局版本号 + workspace 版本号                        │
│    - 变更监听器模式                                       │
│    - 忽略 .git/node_modules/dist 等                      │
│                                                         │
│  SKILL.md Frontmatter                                    │
│    - 元数据：requires, install, emoji                     │
│    - 调用策略：userInvocable, disableModel                │
│    - 安装规格：brew/node/go/uv/download                   │
│    - OS 特定处理                                          │
│                                                         │
│  ClawHub 生态                                            │
│    - 中央注册表                                           │
│    - 技能发现/安装/版本管理/发布                           │
└─────────────────────────────────────────────────────────┘
```

### 本项目现状

- `t_agent_skills` 表存储技能定义，无热刷新、无版本管理、无优先级机制
- 工具在 graph 构建时硬编码绑定，新增工具需改 `multi_agent_graph.py`

### 差距与改进

| 能力 | OpenClaw | 本项目 | 改进阶段 |
|------|---------|--------|---------|
| 技能发现 | ClawHub 中央注册 + 本地扫描 | DB 静态记录 | S1 |
| 热刷新 | 文件监听 + 版本追踪 | 无（需重启） | S2 |
| 优先级治理 | workspace > managed > bundled | 无 | S1 |
| 调用策略 | userInvocable / disableModelInvocation | 无 | S3 |
| 安装管理 | 多包管理器 + OS 适配 | 无 | 远期 |

| 阶段 | 目标 | 工作量 |
|------|------|--------|
| S1 | 技能注册表：基于 `t_agent_skills` 实现 SkillRegistry，支持按 category/priority 查询 | 1 周 |
| S2 | 技能热加载：技能变更后无需重启，通过 API 触发重新加载 | 1-2 周 |
| S3 | 调用策略：技能元数据增加 `invocable_by` 字段，控制 LLM/用户/管理员可调用范围 | 1 周 |
| S4 | 技能市场（远期）：类似 ClawHub 的技能发现与安装机制 | 4+ 周 |

---

## 七、意图路由与安全护栏（本项目优势维度）

### 意图路由

本项目的意图路由设计**优于 OpenClaw 的简单 Supervisor 路由**：

| 能力 | OpenClaw | 本项目 |
|------|---------|--------|
| 预分类 | 无（依赖 LLM function calling） | `intent_classifier.py` 轻量模型预分类，节省 Token |
| 声明式路由 | 无 | `agent_schema.py` Schema 路由（借鉴 TypeAgent），Intent + Entity 双维度匹配 |
| 动态启用/禁用 | 无 | 支持 Agent 动态启用/禁用 |
| 优先级排序 | 无 | 支持 |

待改进：
- 意图分类器缺少 fallback 机制（分类失败时直接返回 unknown）→ 增加关键词 fallback
- Schema 路由未与 DB 中的 `t_agent_skills` 打通

### 安全护栏

本项目在输入/输出层面**优于 OpenClaw**：

| 能力 | OpenClaw | 本项目 |
|------|---------|--------|
| Prompt 注入检测 | 无专门机制 | 9 种模式检测 ✅ |
| 敏感数据脱敏 | 无 | 身份证/手机/银行卡脱敏 ✅ |
| 内容长度限制 | 无 | 50KB 限制 ✅ |
| 输出泄露检测 | 无 | 敏感信息泄露检测 ✅ |
| 工具级权限控制 | Tool Policy Pipeline | 无 ❌ |
| 调用拦截 | before_tool_call 钩子 | 无 ❌ |

差距集中在工具层面：`permission_service.py` 未与工具层打通，护栏仅在 preprocess/postprocess 执行，工具调用过程中无拦截点。

---

## 八、综合改进路线图

### 优先级矩阵

```
                    高业务价值
                        │
         ┌──────────────┼──────────────┐
         │              │              │
         │   M1 数据模型  │  Q4-P1 角色  │
         │   版本化       │  工具过滤    │
         │              │              │
  低可行性 ──────────────┼────────────── 高可行性
         │              │              │
         │   M6 混合检索  │  M3 预压缩   │
         │   S4 技能市场  │  沉淀        │
         │              │              │
         └──────────────┼──────────────┘
                        │
                    低业务价值
```

### 8 周双周迭代计划

```
Week 1-2                Week 3-4                Week 5-6                Week 7-8
────────────────────────────────────────────────────────────────────────────────

[Q4-P1] 角色级          [Q2-L1] Supervisor      [Q3-P1] 基础            [Q2-L2] 子Agent
工具过滤                多意图拆分               消息队列                Session隔离

[M1] 数据模型           [M3] 预压缩前            [M4] 用户记忆           [Q3-P2] collect
版本化+分层注入          自动沉淀                管理API+前端            +防抖

[Q1-P1] API触发          [Q4-P2] 用户级          [S1] 技能注册表          [M5] 会话摘要
工具重载                过滤                                            
```

### 实施优先级排序

| 优先级 | 编号 | 改进项 | 预期效果 | 工作量 |
|--------|------|--------|---------|--------|
| P0 | Q4-P1 | 角色级工具过滤 | 安全性提升，普通用户/管理员看到不同工具集 | 1 周 |
| P0 | M1 | 记忆数据模型版本化 + 分层注入 | 偏好可追溯、可审计，注入更精准 | 1 周 |
| P1 | Q1-P1 | API 触发工具重载 | 新增工具无需重启 | 1 周 |
| P1 | M3 | 预压缩前自动沉淀 | 解决长对话"晚期健忘症" | 0.5 周 |
| P1 | Q2-L1 | Supervisor 多意图拆分 | 支持并行数据查询 | 2 周 |
| P2 | M4 | 用户记忆管理 API + 前端 | 合规要求 + 用户体验 | 1-2 周 |
| P2 | Q3-P1 | 基础消息队列 | 解决"Agent 回复中无法追问" | 1-2 周 |
| P2 | S1 | 技能注册表 | 技能动态管理基础 | 1 周 |
| P3 | M5 | 会话摘要 | 跨会话上下文延续 | 1 周 |
| P3 | M6 | 混合检索（pgvector + BM25） | 从历史对话中召回相关信息 | 2-3 周 |

### 风险提示

| 问题 | 风险 | 缓解措施 |
|------|------|---------|
| Q2 多意图拆分 | LLM 拆分不准确导致错误路由 | 增加 confidence 阈值，低于阈值时不拆分 |
| Q3 消息队列 | 并发状态管理复杂 | Phase 1 只做 `"queue"` 模式（严格顺序），避免并发 |
| Q4 工具过滤 | 过滤过严导致功能不可用 | 默认 `"user"` 角色包含基础工具集，管理员可覆盖 |
| Q1 动态加载 | 插件代码质量不可控 | 加载时 Schema 验证 + 沙箱执行 |
| M1 数据模型扩展 | 迁移脚本影响现有数据 | 新增字段全部有默认值，向后兼容 |

---

## 九、关键设计决策总结

| 决策点 | 结论 | 理由 |
|--------|------|------|
| 记忆存储：DB vs 文件 | DB（已选择） | 多用户系统必须用数据库，OpenClaw 文件方案仅适合单机 Agent |
| 工具治理：7 层 vs 简化版 | 简化为 3 层（全局 + 角色 + Agent） | 本项目无多渠道需求，3 层足够 |
| 技能市场：是否对标 ClawHub | 短期不需要 | 技能数量有限（<10），DB 管理足够 |
| 子 Agent：是否需要 spawn | P3 优先级 | 当前单层路由覆盖大部分银行业务场景 |
| 偏好提取：LLM vs 规则 | 混合方案 | 保留规则提取（快、省 Token），异步 LLM 补充 |
| 消息队列：从哪个模式起步 | `"queue"` 模式 | 最简单，无并发风险，逐步升级 |

---

## 十、与已有方案的关系

| 已有文档 | 与本报告的关系 |
|---------|--------------|
| `output/工具治理架构-评审与方案V0.1.md` | 本报告的 Q4/Q1 改进项直接采用该方案 |
| `output/OpenClaw对标分析报告.md` | 本报告的前身，已整合并更新评分 |
| `output/OpenClaw深挖分析-四大核心问题.md` | 本报告的前身，已整合源码级分析 |
| `docs/开发文档/架构设计/AI模块设计.md` | 改进落地后需同步更新 |
| `docs/内部参考/任务拆解/2026-02-12_skill检索对齐_cursor_mvp/` | S1/S2 改进项与该任务拆解互补 |

---

## 十一、Quick Wins（1 周内可落地，无架构变动）

### QW-1: 扩展偏好提取维度

当前仅支持 4 个维度（语言/长度/结构/语气）。增加银行业务维度：

```python
_DISPLAY_MAPPING["user.default_branch"] = {"label": "默认分行", "values": {}}
_DISPLAY_MAPPING["user.focus_metrics"] = {"label": "关注指标", "values": {}}
_DISPLAY_MAPPING["user.data_scope"] = {
    "label": "数据范围偏好",
    "values": {"retail": "零售", "corporate": "对公", "all": "全部"},
}
```

### QW-2: 意图分类器 fallback 增强

当前分类失败直接返回 `unknown`，增加关键词 fallback：

```python
_KEYWORD_FALLBACK = {
    "todo_management": ["待办", "任务", "提醒", "截止"],
    "data_query": ["查询", "统计", "余额", "贷款", "存款", "分行"],
    "knowledge_query": ["知识库", "文档", "规章", "制度"],
}
```

### QW-3: AgentEvent 增加 tool_call_id

在 `events.py` 的 `tool_start`/`tool_end` 事件中增加可选的 `tool_call_id` 字段，前端可精确关联工具调用的开始和结束。
