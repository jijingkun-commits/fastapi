# OpenClaw 深挖分析：四大核心问题

> 生成时间：2026-02-18
> 基于源码级分析，非推测

---

## Q1: OpenClaw 工具是动态加载的吗？本项目能实现吗？

### 结论：半动态

OpenClaw 工具分两类，加载方式不同：

| 类型 | 加载方式 | 关键文件 |
|------|---------|---------|
| 内置工具 | `createOpenClawTools()` 硬编码注册，但通过 Tool Policy Pipeline 动态过滤 | `openclaw-tools.ts` |
| 插件工具 | `jiti` (Just-In-Time Importer) 真正动态加载 `.ts/.js` 文件 | `plugins/loader.ts`, `plugins/tools.ts` |

插件工具的动态加载链路：

```
~/.openclaw/plugins/ 或 workspace/plugins/
    ↓ jiti 动态导入
loadOpenClawPlugins({ config, workspaceDir })
    ↓ Schema 验证 + 权限检查
resolvePluginTools({ context, existingToolNames, toolAllowlist })
    ↓ 动态过滤
最终工具集
```

关键设计：
- 插件目录支持两个位置：全局 `~/.openclaw/plugins/` 和工作区 `plugins/`
- 加载时进行 Schema 验证，防止恶意插件
- `existingToolNames` 参数防止插件覆盖内置工具
- `toolAllowlist` 参数支持运行时过滤

### 本项目实现方案

难度：中等。推荐分两步：

1. **Phase 1 - API 触发重载**（1 周）：在 `app/ai/tools/` 下建立 Tool Registry，支持通过管理 API 触发工具集重新加载，无需重启服务
2. **Phase 2 - 插件目录扫描**（2 周）：支持从约定目录（如 `plugins/`）动态加载自定义工具，每个插件导出标准 Tool Schema

---

## Q2: 多意图拆分与并行 Agent 调度

### OpenClaw 的 Subagent 架构

OpenClaw 不是在 Supervisor 层做"多意图拆分"，而是通过 **Subagent 工具** 让 Agent 自主决定何时 spawn 子任务。这是一个关键的设计差异。

#### 核心组件

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
│    - SubagentRunRecord: 完整的运行记录                   │
│    - 磁盘持久化 + 内存缓存                               │
│    - lifecycle 事件监听 (start/end/error)                │
│    - 完成后触发 announce flow (结果回传给请求者)          │
│    - 自动归档 (archiveAfterMinutes, 默认 60 分钟)        │
│    - 跨进程可见 (disk-backed registry)                   │
│                                                         │
│  subagent-depth.ts (深度控制)                            │
│    - maxSpawnDepth 限制嵌套层级（默认 1）                 │
│    - 叶子 Agent 看到兄弟，编排 Agent 看到子代             │
└─────────────────────────────────────────────────────────┘
```

#### SubagentRunRecord 数据结构

```typescript
type SubagentRunRecord = {
  runId: string;
  childSessionKey: string;
  requesterSessionKey: string;
  requesterOrigin?: DeliveryContext;
  requesterDisplayKey: string;
  task: string;
  cleanup: "delete" | "keep";
  label?: string;
  model?: string;
  runTimeoutSeconds?: number;
  createdAt: number;
  startedAt?: number;
  endedAt?: number;
  outcome?: SubagentRunOutcome;  // { status: "ok" | "error" | "timeout", error?: string }
  archiveAtMs?: number;
  cleanupCompletedAt?: number;
  suppressAnnounceReason?: "steer-restart" | "killed";
  expectsCompletionMessage?: boolean;
  announceRetryCount?: number;     // 防止无限重试 (max 3)
  lastAnnounceRetryAt?: number;
};
```

#### Steer 机制（源码级）

`steer` 是 OpenClaw 最精巧的设计之一——允许父 Agent 在子 Agent 运行过程中修改其任务方向：

```
steer 调用流程:
1. 速率限制检查 (同一对 caller→child 间隔 ≥ 2s)
2. 禁止自我 steer (callerSessionKey !== childSessionKey)
3. markSubagentRunForSteerRestart() → 抑制旧 run 的 announce
4. abortEmbeddedPiRun(sessionId) → 中断当前生成
5. clearSessionQueues() → 清空队列
6. callGateway("agent.wait") → 等待中断生效 (最多 5s)
7. callGateway("agent") → 以新 message 重启子 Agent
8. replaceSubagentRunAfterSteer() → 用新 runId 替换旧记录
```

#### 级联终止（Cascade Kill）

```typescript
// 递归终止所有后代子 Agent
async function cascadeKillChildren(params: {
  cfg, parentChildSessionKey, cache, seenChildSessionKeys
}): Promise<{ killed: number; labels: string[] }>
```

当终止一个子 Agent 时，会递归遍历其所有后代并逐一终止，防止孤儿进程。

#### 可见性规则

```
编排 Agent (depth < maxSpawnDepth):
  → 看到自己 spawn 的子 Agent (requesterSessionKey = self)

叶子 Agent (depth >= maxSpawnDepth):
  → 看到兄弟 Agent (requesterSessionKey = parent)
  → 通过 spawnedBy 字段向上追溯到父级
```

### 本项目改进方案

当前 Supervisor 只能路由到单个 Agent，无法拆分多意图。改进分三个层次：

#### Level 1: Supervisor 多意图拆分（推荐先做）

在 `multi_agent_graph.py` 的 Supervisor 节点中增加意图拆分逻辑：

```python
# Supervisor Prompt 增加指令：
# "如果用户请求包含多个独立子任务，请拆分为多个路由决策，
#  按依赖关系排序，依次执行。"

# 使用 LangGraph 的 Send() 实现并行分发：
def supervisor_node(state):
    intents = classify_multi_intent(state["messages"][-1])
    if len(intents) == 1:
        return Command(goto=intents[0].route_to)
    else:
        # 并行分发到多个 Agent
        return [Send(intent.route_to, {"task": intent.description}) for intent in intents]
```

#### Level 2: 子 Agent Session 隔离

为每个子任务创建独立的消息上下文，防止互相干扰。参考 OpenClaw 的 `SubagentRunRecord` 设计。

#### Level 3: Steer + Kill 操作

允许 Supervisor 在子 Agent 执行过程中修改任务方向或终止执行。这是最复杂的部分，建议在 Level 1/2 稳定后再实施。

### 实施建议

| 阶段 | 内容 | 工作量 | 前置条件 |
|------|------|--------|---------|
| Level 1 | Supervisor 多意图拆分 + `Send()` 并行 | 2 周 | 无 |
| Level 2 | 子 Agent Session 隔离 + 结果汇总 | 2-3 周 | Level 1 |
| Level 3 | Steer/Kill 操作 + 级联终止 | 3-4 周 | Level 2 |

---

## Q3: 追问/消息队列机制

### OpenClaw 的 Followup Queue 系统

OpenClaw 实现了完整的消息队列系统，处理"Agent 正在回复时用户继续提问"的场景。

#### 队列模式 (QueueMode)

| 模式 | 行为 | 适用场景 |
|------|------|---------|
| `"collect"` | 收集多个消息后一起处理（默认） | 用户连续发多条补充信息 |
| `"steer"` | 立即处理，允许中断当前生成 | 用户想改变方向 |
| `"interrupt"` | 强制中断当前生成，处理新消息 | 紧急修正 |
| `"queue"` | 严格队列，等待当前完成 | 保证顺序执行 |
| `"steer-backlog"` | 混合模式 | 复杂编排场景 |

#### 去重机制 (QueueDedupeMode)

| 模式 | 行为 |
|------|------|
| `"message-id"` | 按消息 ID 去重（推荐） |
| `"prompt"` | 按内容去重 |
| `"none"` | 不去重 |

#### 丢弃策略 (QueueDropPolicy)

| 策略 | 行为 |
|------|------|
| `"old"` | 丢弃旧消息 |
| `"new"` | 丢弃新消息 |
| `"summarize"` | 对超出容量的消息进行 LLM 摘要后丢弃 |

#### 核心数据结构

```typescript
type FollowupRun = {
  prompt: string;
  messageId?: string;
  enqueuedAt: number;
  originatingChannel?: string;
  originatingTo?: string;
};

type FollowupQueueState = {
  items: FollowupRun[];
  draining: boolean;
  mode: QueueMode;
  debounceMs: number;      // 防抖时间，默认 1000ms
  cap: number;             // 最大队列长度
  dropPolicy: QueueDropPolicy;
  droppedCount: number;
  summaryLines: string[];  // 被丢弃消息的摘要
};
```

#### 工作流

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
  - interrupt: 强制中断，立即处理
    ↓
逐个/批量处理队列消息
    ↓
处理完后继续检查队列，直到为空
```

### 本项目现状

完全没有队列机制。当 Agent 正在生成回复时，新消息的行为取决于前端实现——通常是阻塞或丢弃。

### 改进方案

#### Phase 1: 基础队列 + `"queue"` 模式（1-2 周）

```python
# app/ai/queue/followup_queue.py

from dataclasses import dataclass, field
from typing import Optional
from collections import deque
import asyncio
import time

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
        """入队，返回是否成功"""
        if len(self.items) >= self.max_size:
            return False
        # 按 message_id 去重
        if item.message_id:
            for existing in self.items:
                if existing.message_id == item.message_id:
                    return False
        self.items.append(item)
        return True
    
    def drain_next(self) -> Optional[FollowupItem]:
        """取出下一个待处理消息"""
        if not self.items:
            return None
        return self.items.popleft()

# 每个 thread_id 维护一个队列
_queues: dict[str, FollowupQueue] = {}
```

在 SSE 流处理层集成：

```python
# app/ai/sse_stream.py 中
async def handle_new_message(thread_id: str, message: str):
    queue = _queues.get(thread_id)
    if queue and queue.draining:
        # Agent 正在处理中，入队等待
        queue.enqueue(FollowupItem(prompt=message))
        yield AgentEvent(type="queued", data={"position": len(queue.items)})
        return
    # 正常处理...
```

#### Phase 2: `"collect"` 模式 + 防抖（1 周）

```python
# 防抖：等待 debounce_ms 后再处理，允许用户继续输入
async def debounced_drain(queue: FollowupQueue, debounce_ms: int = 1000):
    await asyncio.sleep(debounce_ms / 1000)
    # 合并队列中所有消息
    messages = []
    while item := queue.drain_next():
        messages.append(item.prompt)
    if messages:
        combined = "\n".join(messages)
        # 作为单条消息处理
        yield combined
```

#### Phase 3: `"interrupt"` 模式（2 周）

需要 LangGraph 的中断机制配合，在 `astream_events` 中检测中断信号并优雅终止当前生成。

### 前端配合

前端需要支持：
1. "消息已排队"的 UI 反馈（显示队列位置）
2. 队列中消息的取消操作
3. Agent 正在处理时的输入框状态提示

---

## Q4: Skill 和工具的用户级隔离方案

### OpenClaw 的 Tool Policy Pipeline

OpenClaw 使用 **7 层策略管线** 逐层收紧工具可见性：

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

#### 源码关键实现

```typescript
// tool-policy-pipeline.ts
export function buildDefaultToolPolicyPipelineSteps(params: {
  profilePolicy?: ToolPolicyLike;
  profile?: string;                    // "minimal" | "coding" | "messaging" | "full"
  providerProfilePolicy?: ToolPolicyLike;
  providerProfile?: string;
  globalPolicy?: ToolPolicyLike;
  globalProviderPolicy?: ToolPolicyLike;
  agentPolicy?: ToolPolicyLike;
  agentProviderPolicy?: ToolPolicyLike;
  groupPolicy?: ToolPolicyLike;
  agentId?: string;
}): ToolPolicyPipelineStep[]

// 每一层都执行:
// 1. stripPluginOnlyAllowlist → 防止插件工具越权覆盖核心工具
// 2. expandPolicyWithPluginGroups → 展开 "group:xxx" 为具体工具名
// 3. filterToolsByPolicy → 按 allow/deny 过滤
```

#### 工具分组机制

```typescript
const TOOL_GROUPS: Record<string, string[]> = {
  "group:memory": ["memory_search", "memory_get"],
  "group:web": ["web_search", "web_fetch"],
  "group:fs": ["read", "write", "edit", "apply_patch"],
  "group:runtime": ["exec", "process"],
  "group:sessions": ["sessions_list", "sessions_spawn", ...],
};

const TOOL_PROFILES: Record<ToolProfileId, ToolProfilePolicy> = {
  minimal: { allow: ["session_status"] },
  coding: { allow: ["group:fs", "group:runtime", "group:sessions", "group:memory"] },
  messaging: { allow: ["group:messaging", "sessions_list", ...] },
  full: { allow: ["group:openclaw"] },  // 所有工具
};
```

#### stripPluginOnlyAllowlist 安全机制

这是一个精巧的安全设计：当 allowlist 中只包含插件工具名（不包含任何核心工具名）时，自动忽略该 allowlist，防止配置错误导致核心工具被意外禁用。

```typescript
// 如果 allowlist 全是未知名称（可能是插件工具），忽略它
// 这样核心工具不会被意外过滤掉
const resolved = stripPluginOnlyAllowlist(policy, pluginGroups, coreToolNames);
if (resolved.unknownAllowlist.length > 0) {
  warn(`allowlist contains unknown entries (${entries}). Ignoring...`);
}
```

### 本项目现状

- 无用户级工具隔离
- 所有 Agent 看到相同的工具集
- `permission_service.py` 存在但未与工具层打通

### 改进方案

#### Phase 1: 按 user_role 过滤（1 周）

在已有的工具治理 V0.1 方案基础上，增加用户角色维度：

```python
# app/ai/tool_policy.py

from dataclasses import dataclass
from typing import Optional

# 工具分组定义
TOOL_GROUPS: dict[str, list[str]] = {
    "group:data": ["data_query", "chart_generation", "sql_executor"],
    "group:todo": ["todo_create", "todo_update", "todo_list", "todo_delete"],
    "group:knowledge": ["knowledge_search", "ragflow_search"],
    "group:admin": ["system_config", "user_management", "model_management"],
}

# 角色 Profile 定义
ROLE_PROFILES: dict[str, dict] = {
    "admin": {
        "allow": ["group:data", "group:todo", "group:knowledge", "group:admin"],
    },
    "analyst": {
        "allow": ["group:data", "group:knowledge"],
    },
    "user": {
        "allow": ["group:todo", "group:knowledge"],
    },
}

@dataclass
class ToolPolicyContext:
    user_id: int
    user_role: str       # "admin" / "analyst" / "user"
    agent_id: str        # "data_expert" / "todo_expert" / ...
    scene_key: str       # "multi_agent" / "single_agent"

def filter_tools_by_policy(
    tools: list,
    context: ToolPolicyContext,
) -> list:
    """按策略过滤工具集"""
    profile = ROLE_PROFILES.get(context.user_role, ROLE_PROFILES["user"])
    allowed_groups = profile.get("allow", [])
    
    # 展开分组
    allowed_tools = set()
    for group_or_tool in allowed_groups:
        if group_or_tool.startswith("group:"):
            allowed_tools.update(TOOL_GROUPS.get(group_or_tool, []))
        else:
            allowed_tools.add(group_or_tool)
    
    return [t for t in tools if t.name in allowed_tools]
```

在 `multi_agent_graph.py` 中集成：

```python
# 在 _get_supervisor_tools() 中
def _get_supervisor_tools(user_id: int, user_role: str) -> list:
    all_tools = _get_all_available_tools()
    context = ToolPolicyContext(
        user_id=user_id,
        user_role=user_role,
        agent_id="supervisor",
        scene_key="multi_agent",
    )
    return filter_tools_by_policy(all_tools, context)
```

#### Phase 2: 按 user_id 个性化过滤（1 周）

```python
# 在 ROLE_PROFILES 基础上增加用户级覆盖
USER_OVERRIDES: dict[int, dict] = {
    # 特定用户禁用某些工具
    123: {"deny": ["sql_executor"]},
    # 特定用户额外开放工具
    456: {"also_allow": ["group:admin"]},
}
```

#### Phase 3: Skill 用户级可见性（1-2 周）

在 `t_agent_skills` 表中增加 `visibility` 字段：

```sql
ALTER TABLE t_agent_skills ADD COLUMN visibility VARCHAR(50) DEFAULT 'public';
-- 可选值: 'public', 'role:admin', 'role:analyst', 'user:123'
```

在 Skill 检索时按用户过滤：

```python
def get_skills_for_user(user_id: int, user_role: str) -> list:
    all_skills = skill_repo.list_active()
    return [
        s for s in all_skills
        if s.visibility == "public"
        or s.visibility == f"role:{user_role}"
        or s.visibility == f"user:{user_id}"
    ]
```

---

## 综合实施路线图

```
Week 1-2          Week 3-4          Week 5-6          Week 7-8
────────────────────────────────────────────────────────────────

[Q4-P1]            [Q2-L1]           [Q3-P1]           [Q2-L2]
角色级工具过滤      Supervisor        基础消息队列       子Agent
                   多意图拆分                           Session隔离

[Q1-P1]            [Q4-P2]           [Q3-P2]           [Q4-P3]
API触发工具重载     用户级过滤         collect+防抖       Skill可见性
```

### 优先级排序依据

1. **Q4-P1 角色级工具过滤**（最高优先）：直接提升安全性，工作量小，与已有 V0.1 方案衔接
2. **Q1-P1 API 触发工具重载**：解除"新增工具必须重启"的痛点
3. **Q2-L1 多意图拆分**：提升用户体验，LangGraph `Send()` 原生支持
4. **Q3-P1 基础消息队列**：解决"Agent 回复中无法追问"的体验问题

### 风险提示

| 问题 | 风险 | 缓解措施 |
|------|------|---------|
| Q2 多意图拆分 | LLM 拆分不准确导致错误路由 | 增加 confidence 阈值，低于阈值时不拆分 |
| Q3 消息队列 | 并发状态管理复杂 | Phase 1 只做 `"queue"` 模式（严格顺序），避免并发 |
| Q4 工具过滤 | 过滤过严导致功能不可用 | 默认 `"user"` 角色包含基础工具集，管理员可覆盖 |
| Q1 动态加载 | 插件代码质量不可控 | 加载时 Schema 验证 + 沙箱执行 |
