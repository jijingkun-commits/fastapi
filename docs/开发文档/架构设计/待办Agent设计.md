# 待办 Agent 设计详解

> **状态**: 已更新 (LLM驱动版)
> **更新日期**: 2026-02-04
> **版本**: 3.0
>
> **重要更新 v3.0 (2026-02-04)**:
> - 移除硬编码关键词规则，采用 LLM 驱动的意图识别
> - 新增 `action_state` 和 `response_message` 机制
> - 简化 `clarify_node`，直接使用 LLM 生成的回复


## 文档导航

- 全局架构入口：[系统总览](系统总览.md)
- AI 核心设计：[AI模块设计](AI模块设计.md)
- 后端分层设计：[后端架构](后端架构.md)
- 前端分层设计：[前端架构](前端架构.md)
- 数据模型与双库：[数据库设计](数据库设计.md)
- 对外接口定义：[接口文档](../../API文档/接口文档.md)
- 需求来源总览：[系统需求](../../产品文档/系统需求.md)

## 目录

1. [概述](#1-概述)
2. [数据模型](#2-数据模型)
3. [状态定义](#3-状态定义)
4. [LangGraph 图架构](#4-langgraph-图架构)
5. [节点详解](#5-节点详解)
6. [路由逻辑](#6-路由逻辑)
7. [意图识别](#7-意图识别)
8. [智能特性](#8-智能特性)
9. [工具函数](#9-工具函数)
10. [执行器映射](#10-执行器映射)
11. [配置管理](#11-配置管理)
12. [提示词设计](#12-提示词设计)
13. [Repository 层](#13-repository-层)
14. [异常处理](#14-异常处理)
15. [前端交互协议](#15-前端交互协议)
16. [Goal 模板系统](#16-goal-模板系统) *(新增)*
17. [测试](#17-测试)

---

## 1. 概述

### 1.1 设计理念

Todo Agent 是一个基于 LangGraph 的**意图驱动型** AI Agent，专门处理待办事项管理。核心设计原则：

| 原则 | 说明 | 实现 |
|-----|------|------|
| **极简输入** | 用户只需说"明天开会"，Agent 自动补充默认字段 | LLM 意图分析 + 启发式提取 |
| **交互式确认** | 危险操作需用户确认，创建操作展示详情后确认 | `interrupt()` 机制 |
| **渐进式策略** | 多轮对话后自动给出默认方案，避免无限追问 | 轮次检测 + 策略注入 |
| **逻辑删除** | 所有删除操作为软删除，数据可追溯 | `is_deleted` 字段 |
| **增量更新** | 所有节点返回 Dict 而非修改 state | LangGraph 最佳实践 |

### 1.2 代码结构

```
app/ai/
├── workflow/
│   ├── todo_graph.py              # 图定义、核心节点
│   └── todo_intent_helpers.py     # 意图分析辅助函数
├── agents/
│   ├── resolve_node.py            # 实体解析节点
│   └── todo_enhanced_nodes.py     # 增强节点（澄清/冲突检测/任务拆解）
├── tools/
│   └── todo_tools.py              # 待办工具函数
├── prompts/
│   └── todo_prompts.py            # 提示词定义
├── config/
│   └── todo_config.py             # 配置类 + 依赖注入
├── state.py                       # 状态类型定义
└── exceptions.py                  # 异常类型定义

app/
├── models/
│   └── todo.py                    # ORM 模型
└── repositories/
    └── todo_repository.py         # 数据仓库层
```

### 1.3 与 MultiAgentGraph 的关系

Todo Agent 作为**子图**被 `MultiAgentGraph` 的 Supervisor 调用：

```
用户消息 → Supervisor → [handoff to todo_expert] → Todo Graph → 返回结果
```

Supervisor 通过 `assign_to_todo_expert` 工具触发委派，`pending_handoff` 字段传递任务上下文。

---

## 2. 数据模型

### 2.1 t_todo 表

**文件**: `app/models/todo.py`

```python
class Todo(Base):
    __tablename__ = "t_todo"
```

| 字段 | 类型 | 默认值 | 说明 |
|-----|------|-------|------|
| `id` | Integer | 自增 | 主键 |
| `user_id` | Integer | - | 用户 ID（索引） |
| `title` | String(255) | - | 待办标题（必填） |
| `description` | Text | NULL | 详细描述（地点信息当前拼接在 description 中，未单独建字段） |
| `start_time` | DateTime | NULL | 开始时间 |
| `due_date` | DateTime | NULL | 截止时间 |
| `actual_completion_time` | DateTime | NULL | 实际完成时间 |
| `status` | String(20) | "todo" | 状态 |
| `progress` | Integer | 0 | 进度百分比 (0-100) |
| `progress_notes` | Text | NULL | 进展说明 |
| `priority` | Integer | 2 | 优先级 (1=高, 2=中, 3=低) |
| `category` | String(50) | NULL | 分类标签 |
| `tags` | JSON | NULL | 标签数组 |
| `reminder_enabled` | Boolean | False | 是否启用提醒 |
| `reminder_type` | String(20) | NULL | 提醒方式（planned：当前仅存储配置，不含通知发送） |
| `reminder_advance_minutes` | Integer | NULL | 提前提醒分钟数 |
| `reminder_times` | JSON | NULL | 多次提醒时间点（planned：当前仅存储配置，不含通知发送） |
| `last_reminded_at` | DateTime | NULL | 最后提醒时间（planned：当前仅存储配置，不含通知发送） |
| `is_deleted` | Boolean | False | 逻辑删除标记 |
| `is_recurring` | Boolean | False | 是否重复任务 |
| `recurrence_pattern` | String(50) | NULL | 重复模式 (daily/weekly/monthly) |
| `recurrence_interval` | Integer | 1 | 重复间隔 |
| `recurrence_days` | JSON | NULL | 重复的星期几 |
| `recurrence_end_date` | DateTime | NULL | 重复结束日期 |
| `parent_recurring_id` | Integer | NULL | 关联的重复任务模板 ID |
| `parent_id` | Integer | NULL | 父任务 ID（子任务支持，planned） |
| `task_order` | Integer | 0 | 任务排序（planned） |
| `depth_level` | Integer | 0 | 层级深度（planned） |
| `create_time` | DateTime | now() | 创建时间 |
| `update_time` | DateTime | now() | 更新时间 |
| `extra_data` | JSON | NULL | 扩展元数据（预留） |

### 2.2 状态枚举

| 状态值 | 图标 | 说明 |
|-------|-----|------|
| `todo` | ⬜ | 待办（初始状态） |
| `in_progress` | ◐ | 进行中（progress > 0 且 < 100） |
| `done` | ✅ | 已完成（progress = 100） |
| `cancelled` | ✗ | 已取消 |

> **planned**: 规划扩展状态 `on_hold`（挂起/暂停）。当前不作为 `t_todo.status` 的存储值。

### 2.3 状态流转规则

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│   todo ──────────────────────────► done                    │
│     │                                 ▲                     │
│     │ (progress > 0)                  │                     │
│     ▼                                 │                     │
│   in_progress ────────────────────────┘                    │
│     │           (progress = 100 或 complete)               │
│     │                                                       │
│     │ (cancel)                                              │
│     ▼                                                       │
│   cancelled                                                 │
│                                                             │
│   自动化规则:                                                │
│   1. progress > 0 且 < 100 → status = in_progress          │
│   2. progress = 100 → status = done                        │
│   3. status = done → progress = 100                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 2.4 t_todo_history 表

操作审计日志表，记录所有变更。

| 字段 | 类型 | 说明 |
|-----|------|------|
| `id` | Integer | 主键 |
| `todo_id` | Integer | 待办 ID（索引） |
| `user_id` | Integer | 用户 ID（索引） |
| `action` | String(20) | 操作类型 |
| `changed_fields` | JSON | 变更字段列表 |
| `old_values` | JSON | 变更前值 |
| `new_values` | JSON | 变更后值 |
| `confirmed_by_user` | Boolean | 是否用户确认 |
| `operation_time` | DateTime | 操作时间 |
| `extra_data` | JSON | 元数据 |

**操作类型 (action)**:

| 值 | 说明 |
|---|------|
| `create` | 创建 |
| `update` | 更新 |
| `complete` | 完成 |
| `cancel` | 取消 |
| `soft_delete` | 软删除 |
| `hard_delete` | 物理删除 |

---

## 3. 状态定义

**文件**: `app/ai/state.py`

### 3.1 TodoAgentState

```python
class TodoAgentState(TypedDict, total=False):
    """待办 Agent 状态 - 多轮对话增强版。"""
    
    # ========== 核心字段 ==========
    messages: Annotated[Sequence[BaseMessage], add_messages]  # 消息历史
    user_id: int                    # 用户 ID
    thread_id: str                  # 对话线程 ID
    
    # ========== 操作控制 ==========
    pending_operation: Dict         # 待执行的操作
    user_confirmed: bool            # 用户确认状态
    quick_mode: bool                # 快速模式（跳过确认）
    
    # ========== 对话管理 ==========
    conversation_context: Dict      # 当前对话上下文
    current_focus: str              # 当前焦点任务
    active_projects: List[str]      # 正在讨论的项目列表
    
    # ========== 澄清追问 ==========
    pending_clarifications: List[str]  # 待澄清的问题列表
    project_queue: List[str]           # 待处理项目队列
    current_project_index: int         # 当前处理的项目索引
    
    # ========== 冲突检测 ==========
    detected_conflicts: List[Dict]     # 检测到的冲突
    time_constraints: Dict             # 时间约束
    
    # ========== 信息提取 ==========
    extracted_info: Dict               # LLM 提取的信息
    draft_todos: List[Dict]            # 草稿待办（未确认）
```

### 3.2 字段详解

#### pending_operation

待执行操作的完整描述：

```python
{
    "action": "create",              # 操作类型: create/update/delete/complete/query/...
    "data": {                        # 操作数据
        "title": "明天开会",
        "due_date": "2026-01-31T09:00:00",
        "priority": 2,
        "todo_id": 123,              # update/delete/complete 时必填
        "resolved_title": "周一项目会议"  # resolve 节点填充
    },
    "needs_clarification": False,    # 是否需要澄清
    "skip_confirmation": False,      # 是否跳过确认
    "summary": "**创建待办**\n..."   # 用于前端显示
}
```

#### extracted_info

LLM 从用户消息中提取的信息：

```python
{
    "title": "去上海开会",
    "time": "明天下午3点",           # 原始时间表达
    "due_date": "2026-01-31T15:00:00",  # 解析后的 ISO 格式
    "original_time": "明天下午3点", # 保留原始表达
    "priority": "高",               # 可能是中文
    "category": "工作",
    "location": "上海",
    "description": "讨论Q1计划",
    "is_urgent": True,              # 紧急标记
    "affected_tasks": ["任务A", "任务B"]  # 受影响的任务
}
```

#### time_constraints

时间约束（用于冲突检测）：

```python
{
    "blocked_weekdays": [6, 7],  # 周六、周日不可用
    "working_hours": {"start": 9, "end": 18}
}
```

---

## 4. LangGraph 图架构

### 4.1 图结构图

```
                    ┌───────────────┐
                    │   START       │
                    └───────┬───────┘
                            │
                            ▼
                    ┌───────────────┐
                    │analyze_intent │
                    └───────┬───────┘
                            │
                            ▼
                    ┌───────────────┐
                    │  route_next   │
                    └───────┬───────┘
                            │
           ┌────────────────┼────────────────┐
           │                │                │
           ▼                ▼                ▼
    ┌───────────┐    ┌───────────┐    ┌───────────┐
    │  clarify  │    │  resolve  │    │  execute  │
    └─────┬─────┘    └─────┬─────┘    └─────┬─────┘
          │                │                │
          ▼                ▼                │
         END        ┌───────────────┐       │
                    │route_after_res│       │
                    └───────┬───────┘       │
                            │               │
               ┌────────────┼───────┐       │
               │            │       │       │
               ▼            ▼       ▼       │
        ┌───────────┐ ┌─────────┐ ┌─────────┤
        │  clarify  │ │ confirm │ │ execute ◄─────────┐
        └─────┬─────┘ └────┬────┘ └────┬────┘         │
              │            │           │              │
              ▼            ▼           │              │
             END    ┌─────────────┐    │              │
                    │wait_confirm │    │              │
                    └──────┬──────┘    │              │
                           │           │              │
                           └───────────┴──────────────┘
                                       │
                                       ▼
                                      END
```

### 4.2 图构建代码

**文件**: `app/ai/workflow/todo_graph.py` → `create_todo_graph()`

```python
def create_todo_graph(model=None, enable_thinking=False, model_id=None, checkpointer=None):
    """创建 LangGraph 待办 Agent。"""
    
    workflow = StateGraph(TodoAgentState)
    
    # 添加节点
    workflow.add_node("analyze", analyze_intent)
    workflow.add_node("clarify", clarify_node)
    workflow.add_node("conflict", conflict_detection_node)
    workflow.add_node("resolve", resolve_entity)
    workflow.add_node("confirm", ask_confirmation)
    workflow.add_node("wait_confirm", wait_for_confirmation)
    workflow.add_node("execute", execute_operation)
    
    # 设置入口
    workflow.set_entry_point("analyze")
    
    # 设置边
    workflow.add_conditional_edges("analyze", route_next, {
        "clarify": "clarify",
        "conflict": "conflict",
        "resolve": "resolve",
        "execute": "execute"
    })
    
    workflow.add_edge("clarify", END)
    
    workflow.add_conditional_edges("conflict", 
        lambda s: "resolve" if s.get("pending_operation") else "execute",
        {"resolve": "resolve", "execute": "execute"}
    )
    
    workflow.add_conditional_edges("resolve", route_after_resolve, {
        "clarify": "clarify",
        "confirm": "confirm",
        "execute": "execute"
    })
    
    workflow.add_edge("confirm", "wait_confirm")
    workflow.add_edge("wait_confirm", "execute")
    workflow.add_edge("execute", END)
    
    # 编译
    if checkpointer is None:
        checkpointer = MemorySaver()
    
    return workflow.compile(checkpointer=checkpointer)
```

---

## 5. 节点详解

### 5.1 analyze_intent 节点（v3.0 LLM驱动版）

**职责**: 完全依赖 LLM 分析用户意图，决定下一步动作，生成回复消息。

**文件**: `app/ai/workflow/todo_graph.py`

**输入**: `TodoAgentState`

**输出**: `Dict`（增量更新，包含 `action_state` 和 `response_message`）

> **v3.0 变更**: 移除规则化意图检测，完全由 LLM 决策

**处理流程**:

```
1. 消息过滤与 Handoff 上下文构建
   │
   ├── filter_messages_for_todo()
   └── 解析 pending_handoff 中的预提取信息

2. 历史任务查询
   │
   └── query_existing_todos() → 注入到提示词

3. 渐进式策略注入
   │
   └── get_progressive_strategy() → 根据轮次注入策略

4. LLM 调用（核心决策）
   │
   ├── 构建 Prompt（意图分析 + 渐进策略 + 历史上下文）
   ├── 解析 JSON 响应 → IntentResult
   └── 提取 action_state, response_message, intent, quick_mode

5. 时间解析
   │
   └── parse_time_info() → 自然语言时间 → ISO 格式

6. 根据 action_state 设置状态
   │
   ├── cancelled → 清空 pending_operation，返回取消消息
   ├── need_clarify → 设置 needs_clarification，保存 response_message
   ├── ready → 设置 skip_confirmation，直接执行
   └── need_confirm → 进入确认流程
```

**关键代码片段**:

```python
def analyze_intent(state: TodoAgentState) -> Dict:
    updates: Dict = {}
    
    # Step 1: 消息过滤
    filtered_messages, handoff_context, pre_extracted_info = filter_messages_for_todo(
        messages, state.get("pending_handoff")
    )
    
    # Step 4: LLM 调用（完全依赖 LLM 决策）
    parser = JsonOutputParser(pydantic_object=IntentResult)
    response = llm.invoke(analysis_messages, config={"tags": ["internal_thought"]})
    analysis_dict = parser.parse(response.content)
    
    # 提取 LLM 返回的核心字段
    action_state = analysis_dict.get("action_state", "need_confirm")
    response_message = analysis_dict.get("response_message", "")
    
    # 保存供后续节点使用
    updates["response_message"] = response_message
    
    # Step 6: 根据 action_state 路由
    if action_state == "cancelled":
        updates["pending_operation"] = None
        updates["messages"] = [create_ai_message(response_message or "好的，已取消。")]
    elif action_state == "need_clarify":
        updates["pending_operation"] = {"action": intent, "data": extracted_info, "needs_clarification": True}
    # ... 其他状态处理
    
    return updates
```

### 5.2 clarify_node 节点（v3.0 LLM驱动版）

**职责**: 使用 LLM 生成的 `response_message` 进行追问或确认。

**文件**: `app/ai/agents/todo_enhanced_nodes.py`

> **v3.0 变更**: 不再内部调用 LLM，直接使用 `analyze_intent` 阶段生成的 `response_message`

**核心逻辑**:

```python
def clarify_node(state: TodoAgentState) -> Dict:
    # 优先使用 LLM 生成的 response_message
    response_message = state.get("response_message")
    
    if response_message and response_message.strip():
        updates["messages"] = [create_ai_message(response_message)]
    else:
        # 兜底消息
        updates["messages"] = [create_ai_message("请告诉我您需要完成什么任务？")]
    
    return updates
```

**保留的特殊模式**:

| 模式 | 触发条件 | 行为 |
|-----|---------|------|
| 逐项目追问 | `project_queue` 非空 | 依次询问每个项目的详情 |

**输出示例**（由 LLM 生成）:

```
好的，我帮您记录这个待办：

📝 标题：去上海开会
⏰ 时间：明天下午3点
⭐ 优先级：中

确认创建吗？您也可以补充更多信息。
```

### 5.3 resolve_entity 节点

**职责**: 将模糊的待办标识解析为具体 `todo_id`。

**文件**: `app/ai/agents/resolve_node.py`

**处理逻辑**:

| 场景 | 处理 |
|-----|------|
| 已有 `todo_id` | 直接放行 |
| 操作是 create/query | 直接放行 |
| 无关键词 | 设置 `needs_clarification`，提示输入名称或 ID |
| 匹配 0 个 | 设置 `needs_clarification`，提示找不到 |
| 匹配 1 个 | 写入 `todo_id` 和 `resolved_title` |
| 匹配多个 | 设置 `needs_clarification`，列出选项 |

**代码片段**:

```python
def resolve_entity(state: TodoAgentState) -> Dict:
    pending_op = state.get("pending_operation")
    
    # 不需要解析的操作（batch_create 已废弃）
    if action in ["create", "query", "summarize", "clarify"]:
        return {}
    
    # 已有 todo_id
    if data.get("todo_id"):
        return {}
    
    # 模糊搜索
    keyword = data.get("target_title") or data.get("title")
    matches = _find_matching_todos(user_id, keyword)
    
    if len(matches) == 0:
        return {
            "pending_operation": {**pending_op, "needs_clarification": True},
            "messages": [AIMessage(content=f"❌ 找不到包含「{keyword}」的待办事项。")]
        }
    elif len(matches) == 1:
        data["todo_id"] = matches[0]["id"]
        data["resolved_title"] = matches[0]["title"]
        return {"pending_operation": {**pending_op, "data": data}}
    else:
        return {
            "pending_operation": {**pending_op, "needs_clarification": True},
            "messages": [AIMessage(content=f"找到 {len(matches)} 个匹配，请选择...")]
        }
```

### 5.4 ask_confirmation 节点

**职责**: 生成确认消息，构造前端 ConfirmationCard 数据。

**文件**: `app/ai/workflow/todo_graph.py`

**输出结构**:

```python
{
    "messages": [AIMessage(
        content="确认删除 **周一会议** 吗？",
        additional_kwargs={
            "operation": {
                "action": "delete",
                "data": {"todo_id": 45, "title": "周一会议"},
                "summary": "**删除待办**\n📝 标题：周一会议",
                "target_task": {"id": 45, "title": "周一会议"}
            }
        }
    )],
    "pending_operation": {操作详情},
    "user_confirmed": None  # 重置确认状态
}
```

### 5.5 wait_for_confirmation 节点

**职责**: 使用 `interrupt()` 暂停图执行，等待用户确认。

**文件**: `app/ai/workflow/todo_graph.py`

**核心机制**:

```python
def wait_for_confirmation(state: TodoAgentState) -> Dict:
    # 构造 interrupt 值（前端 CompactApproval 需要的格式）
    interrupt_value = {
        "action_requests": [{
            "name": pending_op.get("action"),
            "args": {
                **pending_op.get("data", {}),
                "_display_message": pending_op.get("summary", "")
            }
        }]
    }
    
    # 触发中断，等待前端 resume
    decision = interrupt(interrupt_value)
    
    # 前端 resume 时传入的数据
    # 格式: {"confirmed": True} 或 {"confirmed": False}
    
    if decision.get("confirmed"):
        return {"user_confirmed": True}
    else:
        return {"user_confirmed": False}
```

### 5.6 execute_operation 节点

**职责**: 执行具体的 CRUD 操作。

**文件**: `app/ai/workflow/todo_graph.py`

**处理流程**:

```
1. 检查 user_confirmed
   │
   ├── False → 静默退出，清理状态
   └── True 或 None → 继续

2. 如果无 pending_operation → 执行查询

3. 调用执行器
   │
   └── _dispatch_execute(action, data, state)

4. 转换 ToolResult 为 AIMessage

5. 发送 custom 事件（emit_result）

6. 清理状态
   │
   └── pending_operation = None, user_confirmed = None
```

### 5.7 conflict_detection_node 节点

**职责**: 检测时间/工作量冲突。

**文件**: `app/ai/agents/todo_enhanced_nodes.py`

**检测类型**:

| 类型 | 触发条件 | 描述 |
|-----|---------|------|
| `blocked_day` | 任务截止日在屏蔽的星期 | "周六您不可用，但有 2 个任务截止" |
| `workload_overflow` | 单日工时 > 8h | "预计需要 12h，可用 8h" |
| `time_overload` | 同一天 ≥ 3 个任务 | "1月30日有 4 个任务需要完成" |
| `priority_overload` | 高优先级 ≥ 3 个 | "有 5 个高优先级任务" |

---

## 6. 路由逻辑

### 6.1 route_next

**位置**: `analyze_intent` 之后

```python
def route_next(state: TodoAgentState) -> Literal["clarify", "conflict", "resolve", "execute", "end"]:
    pending_op = state.get("pending_operation")
    
    # 优先级 1: 跳过确认（如 query）
    if pending_op and pending_op.get("skip_confirmation"):
        return "execute"
    
    # 优先级 2: 需要澄清
    if pending_op and pending_op.get("needs_clarification"):
        return "clarify"
    
    # 优先级 3: 纯澄清（无 pending_op）
    if state.get("pending_clarifications") and not pending_op:
        return "clarify"
    
    # 优先级 4: 有操作需要解析
    if pending_op:
        return "resolve"
    
    # 默认: 澄清
    return "clarify"
```

### 6.2 route_after_resolve

**位置**: `resolve_entity` 之后

```python
def route_after_resolve(state: TodoAgentState) -> Literal["clarify", "confirm", "execute"]:
    pending_op = state.get("pending_operation")
    
    if not pending_op:
        return "execute"
    
    # 用户已确认（规则化检测）
    if state.get("user_confirmed"):
        return "execute"
    
    # 需要澄清（找不到或多个匹配）
    if pending_op.get("needs_clarification"):
        return "clarify"
    
    # 跳过确认
    if pending_op.get("skip_confirmation"):
        return "execute"
    
    # 正常进入确认
    return "confirm"
```

---

## 7. 意图识别

### 7.1 支持的意图类型

| 意图 | 触发关键词 | 说明 |
|-----|----------|------|
| `create` | 创建、添加、记录、明天、下周 | 创建待办 |
| `query` | 列出、查看、显示、有哪些 | 查询待办 |
| `update` | 修改、改成、延后、推迟 | 更新待办 |
| `complete` | 完成、做完了 | 标记完成 |
| `delete` | 删除、取消 | 删除待办 |
| `confirm` | 好、确认、可以、行、OK | 用户确认 |
| `clarify` | - | 信息不完整 |
| `chat` | - | 非待办相关 |

### 7.2 IntentResult 模型（LLM驱动版 v3.0）

**文件**: `app/ai/workflow/todo_graph.py`

```python
class IntentResult(BaseModel):
    """LLM 意图分析结果模型 - LLM驱动版本"""
    intent: str = Field(description="用户意图: create, update, delete, query, confirm, cancel, chat 等")
    action_state: str = Field(default="need_confirm", description="下一步动作: need_clarify, need_confirm, ready, cancelled")
    response_message: str = Field(default="", description="LLM生成的自然语言回复")
    extracted_info: Dict = Field(default={}, description="提取的实体信息: title, time, due_date, priority 等")
    missing_info: List[str] = Field(default=[], description="缺失的关键信息")
    conflict_risk: str = Field(default="none", description="冲突风险: high, medium, none")
    quick_mode: bool = Field(default=False, description="是否为快速模式")
    context_hints: Dict = Field(default={}, description="上下文线索")
    projects: List[str] = Field(default=[], description="涉及的项目列表")
    time_constraints: Dict = Field(default={}, description="时间约束")
```

**核心字段说明**：

| 字段 | 说明 | 值示例 |
|-----|------|-------|
| `action_state` | LLM 决定的下一步动作 | `need_clarify`, `need_confirm`, `ready`, `cancelled` |
| `response_message` | LLM 生成的自然语言回复 | "好的，我帮您创建这个待办：明天下午3点开会。确认创建吗？" |
| `quick_mode` | LLM 检测的快速模式标记 | `true` (用户说"直接创建"时) |

### 7.3 意图检测策略（v3.0 LLM驱动）

> **v3.0 更新**: 规则化意图检测已移除，完全由 LLM 驱动

**旧版架构** (v2.0):
- `check_rule_based_intent()` 在 LLM 之前进行关键词匹配
- 硬编码取消、确认、快速模式、紧急关键词

**新版架构** (v3.0):
- 完全依赖 LLM 的 `action_state` 和 `intent` 判断
- 关键词识别逻辑内化到提示词中（`TODO_INTENT_ANALYZE_PROMPT`）
- 优势：更灵活的语义理解，无需维护关键词列表

**action_state 路由映射**:

| action_state | 路由目标 | 说明 |
|-------------|---------|------|
| `cancelled` | END | 用户取消，清空 pending_operation |
| `need_clarify` | clarify | 信息不完整，使用 LLM 生成的 response_message |
| `ready` | execute | 可直接执行（查询、已确认） |
| `need_confirm` | confirm | 需要用户确认后执行 |

### 7.4 启发式标题提取

当 LLM 未能提取标题时的备用方案：

```python
def extract_heuristic_title(message: str) -> Optional[str]:
    patterns = [
        r"(?:再|帮我|请)?创建一个?任务[：:]\s*(.+)",
        r"创建待办[：:]\s*(.+)",
        r"记一下[：:]\s*(.+)"
    ]
    for pattern in patterns:
        match = re.search(pattern, message)
        if match:
            return match.group(1).strip()
    return None
```

---

## 8. 智能特性

### 8.1 渐进式策略

**文件**: `app/ai/prompts/todo_prompts.py`

| 轮数 | 策略 | 行为 |
|-----|------|------|
| ≤ 2 | 正常 | 继续追问 |
| 3-4 | 果断策略 | 停止追问，给出默认方案 |
| ≥ 5 | 重置策略 | 询问是否重新开始 |

**果断策略默认值**:
- 时间未知 → "明天下午3点"
- 优先级未知 → "🟡中"
- 分类未知 → "工作"

**获取策略注入**:

```python
def get_progressive_strategy(round_count: int, user_confirmed: bool, quick_mode: bool) -> str:
    if round_count > 5:
        return PROGRESSIVE_STRATEGY_RESET
    elif round_count > 2 and not user_confirmed and not quick_mode:
        return PROGRESSIVE_STRATEGY_DECISIVE
    return ""
```

### 8.3 快速模式（v3.0 LLM驱动）

> **v3.0 变更**: 不再使用硬编码关键词，由 LLM 识别

**触发方式**: LLM 分析用户消息，返回 `quick_mode: true`

**典型触发表达**:
- "快速创建..."
- "直接帮我记..."
- "别问了，马上创建"
- "不要问那么多"

**行为**: `quick_mode=True` 时跳过确认流程直接执行。

### 8.4 紧急任务检测（v3.0 LLM驱动）

> **v3.0 变更**: 不再使用硬编码关键词，由 LLM 识别

**触发方式**: LLM 分析用户消息，在 `extracted_info` 中设置 `is_urgent: true` 和 `priority: 1`

**典型触发表达**:
- "紧急任务..."
- "领导/老板说..."
- "赶紧/立刻..."
- "刚刚来了个急事"

**行为**:
1. LLM 自动设置 `priority: 1`（高优先级）
2. LLM 在 `response_message` 中提醒用户这是紧急任务

### 8.5 自然语言时间解析

**文件**: `app/services/time_parser.py` → `NaturalTimeParser`

支持的时间表达：
- "明天下午3点" → 2026-01-31T15:00:00
- "下周一" → 下周一 00:00:00
- "三天后" → 当前时间 + 3 天
- "周五上午10点" → 本周五 10:00:00

---

## 9. 工具函数

### 9.1 工具列表

**文件**: `app/ai/tools/todo_tools.py`

| 工具 | 说明 | 参数 |
|-----|------|------|
| `add_todo` | 创建待办 | title, description, priority, start_time, due_date, location, category, tags, reminder_enabled, reminder_advance_minutes |
| `list_todos` | 查询待办 | status, category, priority, keyword |
| `update_progress` | 更新进度 | todo_id, progress, progress_notes |
| `update_todo` | 更新待办 | todo_id, title, description, priority, due_date, category, status |
| `complete_todo` | 标记完成 | todo_id |
| `delete_todo` | 删除待办 | todo_id |

> `location` 参数当前不单独落库，会在工具层拼接到 `description` 字段中。

当前版本未提供独立的批量工具文件；批量创建能力已在工作流层标记为废弃（2026-02-01）。

### 9.2 工具输入模型

```python
class AddTodoInput(BaseModel):
    """添加待办输入参数"""
    title: str = Field(description="待办标题")
    description: str = Field(default="", description="详细描述")
    priority: int = Field(default=2, description="优先级 1=高 2=中 3=低")
    start_time: Optional[str] = Field(default=None, description="开始时间")
    due_date: Optional[str] = Field(default=None, description="截止日期")
    location: Optional[str] = Field(default=None, description="地点")
    category: Optional[str] = Field(default=None, description="分类")
    tags: Optional[List[str]] = Field(default=None, description="标签列表")
    reminder_enabled: bool = Field(default=False, description="是否启用提醒")
    reminder_advance_minutes: Optional[int] = Field(default=None, description="提前提醒分钟数")
```

### 9.3 工具返回格式

所有工具返回字符串，使用 emoji 前缀：

```python
# 成功
"✅ 待办已创建！\n\n**去上海开会** (ID: 123)\n优先级：🟡中\n截止：01-31 15:00"

# 失败
"❌ 创建待办失败: 无法解析时间"

# 列表
"📋 **待办事项列表**\n\n⬜ [1] 🔴 紧急会议 | 截止: 01-30 09:00\n..."
```

---

## 10. 执行器映射

### 10.1 映射表

**文件**: `app/ai/workflow/todo_graph.py`

```python
# 注：batch_create/batch_complete 已废弃（2026-02-01）
_EXECUTOR_MAP = {
    "create": _execute_create,
    "update": _execute_update,
    "delete": _execute_delete,
    "complete": _execute_complete,
    "query": _execute_query,
    "merge": _execute_merge,
}
```

### 10.2 分派函数

```python
def _dispatch_execute(action: str, data: Dict, state: TodoAgentState) -> ToolResult:
    executor = _EXECUTOR_MAP.get(action)
    if executor:
        return executor(data, state)
    else:
        return ToolResultBuilder.error(f"暂不支持操作: {action}")
```

### 10.3 ToolResult 类型

**文件**: `app/core/types.py`

```python
class ToolResult(TypedDict):
    success: bool           # 操作是否成功
    message: str            # 用户可见消息
    data: Optional[dict]    # 结构化数据
    data_type: Optional[str]  # 数据类型（用于前端渲染）
    error: Optional[str]    # 错误详情
```

**常用 data_type**:
- `todo_item`: 单个待办
- `todo_list`: 待办列表

---

## 11. 配置管理

### 11.1 配置类（v3.0 简化版）

**文件**: `app/ai/config/todo_config.py`

> **v3.0 变更**: 关键词配置已移除，相关检测由 LLM 处理

```python
class TodoAgentConfig(BaseSettings):
    """Todo Agent 配置类，支持环境变量覆盖"""
    
    # 工作量配置
    default_hours_per_task: int = 2
    max_daily_hours: int = 8
    max_todos_per_query: int = 200
    context_todos_limit: int = 10
    
    # 渐进式策略配置
    progressive_round_threshold: int = 2
    progressive_reset_threshold: int = 5
    
    # 标题验证配置（仅保留兜底验证）
    vague_title_keywords: List[str] = ["这个", "那个", "它", "东西", "事情"]
    
    # 优先级映射
    priority_map_cn: dict = {"高": 1, "中": 2, "低": 3}
    priority_map_en: dict = {"high": 1, "medium": 2, "low": 3}
    priority_map_num: dict = {"1": 1, "2": 2, "3": 3}
    
    model_config = {"env_prefix": "TODO_AGENT_"}
```

**已移除的配置** (v3.0):
- `cancel_keywords` - 取消意图由 LLM 识别
- `confirm_keywords` - 确认意图由 LLM 识别
- `quick_mode_keywords` - 快速模式由 LLM 识别
- `urgent_keywords` - 紧急任务由 LLM 识别

**已移除的方法** (v3.0):
- `is_cancel()` - 由 LLM 的 `action_state: "cancelled"` 替代
- `is_confirm()` - 由 LLM 的 `intent: "confirm"` 替代
- `is_quick_mode()` - 由 LLM 的 `quick_mode: true` 替代
- `is_urgent()` - 由 LLM 的 `extracted_info.is_urgent` 替代

### 11.2 环境变量

| 变量 | 默认值 | 说明 |
|-----|-------|------|
| `TODO_AGENT_DEFAULT_HOURS_PER_TASK` | 2 | 默认任务工时 |
| `TODO_AGENT_MAX_DAILY_HOURS` | 8 | 每日最大工时 |
| `TODO_AGENT_PROGRESSIVE_ROUND_THRESHOLD` | 2 | 果断策略触发轮数 |
| `TODO_AGENT_PROGRESSIVE_RESET_THRESHOLD` | 5 | 重置策略触发轮数 |

### 11.3 依赖注入

```python
class TodoDependencies:
    """依赖容器，用于测试注入"""
    
    def get_repository(self):
        """获取待办仓库实例"""
        
    def get_db_context(self):
        """获取数据库上下文管理器"""
        
    def get_llm(self, **kwargs):
        """获取 LLM 实例"""
```

**使用方式**:

```python
# 获取依赖（优先从 config 获取）
deps = get_todo_dependencies(config)
repo = deps.get_repository()
with deps.get_db_context() as db:
    todos = repo.list_by_user(db, user_id)
```

---

## 12. 提示词设计

### 12.1 意图分析提示词

**文件**: `app/ai/prompts/todo_prompts.py` → `TODO_INTENT_ANALYZE_PROMPT`

关键规则：
1. 一次只处理一个待办事项
2. 如果用户一句话提到多个任务，识别为 `clarify` 意图
3. 确认关键词检测规则（仅包含关键词 → confirm）
4. 快速模式检测（设置 `quick_mode: true`）

### 12.2 澄清提示词

**文件**: `app/ai/prompts/todo_prompts.py` → `TODO_CLARIFY_PROMPT`

场景识别：
- 模糊起始: "帮我理一理"
- 高层级输入: "有几个项目要做"
- 隐含需求: "领导下周要听汇报"

### 12.3 任务拆解提示词

**文件**: `app/ai/prompts/todo_prompts.py` → `TODO_DECOMPOSE_PROMPT`

识别复合任务的特征：
- 包含 "和"/"以及" 等连接词
- 提到多个动作
- 明确列举子项

### 12.4 Agent 系统提示词

**文件**: `app/ai/prompts/todo_prompts.py` → `TODO_AGENT_SYSTEM_PROMPT`

核心能力说明、工作方式、示例对话。

---

## 13. Repository 层

**文件**: `app/repositories/todo_repository.py`

### 13.1 方法列表

| 方法 | 说明 | 参数 |
|-----|------|------|
| `create` | 创建待办 | db, user_id, title, description, priority, start_time, due_date, category, tags, reminder_enabled, ... |
| `get_by_id` | 按 ID 获取 | db, todo_id, user_id |
| `list_by_user` | 列表查询 | db, user_id, status, category, priority, keyword, include_deleted, limit |
| `update_fields` | 字段更新 | db, todo_id, user_id, **updates |
| `update_progress` | 进度更新 | db, todo_id, user_id, progress, progress_notes |
| `complete` | 标记完成 | db, todo_id, user_id |
| `cancel` | 取消任务 | db, todo_id, user_id |
| `delete` | 软删除 | db, todo_id, user_id, soft=True |
| `batch_complete` | 批量完成 | db, todo_ids, user_id |
| `get_history` | 获取历史 | db, todo_id, user_id, limit |

### 13.2 status 参数特殊值

| 值 | 含义 |
|---|------|
| `pending` | todo + in_progress |
| `completed` | done |
| `todo` / `in_progress` / `done` / `cancelled` | 精确匹配 |

### 13.3 审计日志

所有写操作自动记录到 `t_todo_history`：

```python
def _log_history(self, db, todo_id, user_id, action, changed_fields=None, old_values=None, new_values=None):
    history = TodoHistory(
        todo_id=todo_id,
        user_id=user_id,
        action=action,
        changed_fields=changed_fields,
        old_values=old_values,
        new_values=new_values
    )
    db.add(history)
    db.commit()
```

---

## 14. 异常处理

**文件**: `app/ai/exceptions.py`

### 14.1 异常层次

```
TodoAgentError (基类)
├── LLMError
│   ├── LLMInvocationError (网络/超时)
│   ├── LLMParseError (JSON 解析失败)
│   └── LLMRateLimitError (速率限制)
├── DatabaseError
│   ├── EntityNotFoundError (实体未找到)
│   ├── DuplicateEntityError (重复实体)
│   └── DatabaseConnectionError (连接失败)
├── UserInputError
│   ├── MissingRequiredFieldError (缺少必填)
│   ├── InvalidFieldValueError (值无效)
│   └── AmbiguousEntityError (多个匹配)
└── WorkflowError
    ├── NodeExecutionError (节点执行失败)
    ├── StateTransitionError (状态转换错误)
    └── TimeoutError (超时)
```

### 14.2 错误处理策略

| 错误类型 | 是否可恢复 | 处理方式 |
|---------|----------|---------|
| `LLMParseError` | ✅ | 降级为默认意图 |
| `EntityNotFoundError` | ✅ | 路由到 clarify |
| `AmbiguousEntityError` | ✅ | 列出选项让用户选择 |
| `NetworkError` | ❌ | 返回友好错误消息 |
| `DatabaseConnectionError` | ❌ | 返回服务不可用 |

---

## 15. 前端交互协议

### 15.1 SSE 事件

| 事件类型 | 触发时机 | 数据格式 |
|---------|---------|---------|
| `token` | LLM 输出 | `{content: "..."}`|
| `result` | 操作完成 | `{data_type: "todo_list", data: {...}, message: "..."}` |
| `confirmation` | 需要确认 | `{action_requests: [{name, args}]}` |
| `clarification` | 需要澄清 | `{questions: [...], message: "..."}` |
| `error` | 发生错误 | `{message: "..."}` |

### 15.2 Confirmation 交互

**发送确认请求**:

```python
interrupt_value = {
    "action_requests": [{
        "name": "create",
        "args": {
            "title": "去上海开会",
            "_display_message": "**创建待办**\n📝 标题：去上海开会"
        }
    }]
}
decision = interrupt(interrupt_value)
```

**前端 Resume**:

```typescript
// 确认
graph.resume(thread_id, { confirmed: true })

// 带修改的确认
graph.resume(thread_id, { confirmed: true, due_date: "2026-02-01" })

// 拒绝
graph.resume(thread_id, { confirmed: false })
```

### 15.3 AIMessage additional_kwargs

```python
AIMessage(
    content="确认删除待办吗？",
    additional_kwargs={
        "operation": {
            "action": "delete",
            "data": {"todo_id": 45},
            "summary": "**删除待办**\n...",
            "target_task": {"id": 45, "title": "周一会议"},
            "diff": {"status": {"old": "todo", "new": "deleted"}}
        }
    }
)
```

### 15.4 ConfirmationCard 组件

> **更新**: 2026-01-31

前端 `ConfirmationCard` 组件根据 `operation.action` 渲染不同的确认视图。

**支持的操作类型**：

| action | 视图样式 | 特性 | target_task | diff |
|--------|---------|------|-------------|------|
| `create` | 蓝色边框 | 单条创建，支持编辑 | - | - |
| `update` | 蓝色边框 | Diff 视图，显示变更前后 | ✅ 必须 | ✅ 可选 |
| `delete` | 红色边框 | 警告提示，不可恢复 | ✅ 必须 | - |
| `complete` | 绿色边框 | 庆祝动画 🎉 | ✅ 必须 | - |

> **注**: `batch_create` 已废弃（2026-02-01），系统仅支持单任务创建

**operation 数据格式约定**：

```typescript
// 注：batch_create/batch_complete 已废弃（2026-02-01）
interface ConfirmationData {
    action: 'create' | 'update' | 'delete' | 'complete'
    data: Record<string, any>       // 操作数据
    summary?: string                // 友好摘要（Markdown）
    target_task?: {                 // 目标任务（update/delete/complete 必须）
        id: number
        title: string
    }
    diff?: Record<string, {         // 变更对比（update 可选）
        old: any
        new: any
    }>
}
```

**后端构造示例**（`todo_graph.py`）：

```python
operation_data = {
    "action": action,
    "data": data,
    "summary": friendly_summary
}

# update 操作添加 target_task 和 diff
if action == "update":
    operation_data["target_task"] = {"id": todo_id, "title": resolved_title}
    operation_data["diff"] = {"priority": {"old": 2, "new": 1}}

# delete/complete 操作添加 target_task
elif action in ["delete", "complete"]:
    operation_data["target_task"] = {"id": todo_id, "title": resolved_title}
```

**前端组件路径**：`web/src/components/todo/ConfirmationCard.tsx`

---

## 16. Goal 模板系统

> **新增**: 2026-01-30
> **来源**: 借鉴 Temporal AI Agent 的 `example_conversation_history` 设计

### 16.1 设计理念

Goal 模板系统为每种意图定义：
- **槽位（Slots）**：必填和选填字段
- **默认值**：渐进式策略第 3 轮后自动填充
- **Few-shot 示例**：引导 LLM 准确提取信息

```
用户输入 → 规则匹配（预检测意图）→ 注入 Few-shot 示例 → LLM 分析 → 提取准确率↑
```

### 16.2 数据结构

**文件**: `app/ai/config/goal_templates.py`

```python
@dataclass
class GoalTemplate:
    required_slots: List[str]       # 必填槽位
    optional_slots: List[str]       # 选填槽位
    default_values: Dict[str, str]  # 默认值（渐进式策略）
    few_shot_examples: List[Tuple[str, Dict]]  # Few-shot 示例
    prompt_hint: str                # Prompt 提示
    requires_confirmation: bool     # 是否需要确认
```

### 16.3 支持的意图

| 意图 | 必填槽位 | 选填槽位 | Few-shot 数量 | 需确认 |
|-----|---------|---------|--------------|-------|
| create | title | due_date, priority, category, description, location | 6 | ✅ |
| query | - | keyword, date_range, status, category, priority | 5 | ❌ |
| update | target_ref | new_title, new_due_date, new_priority | 4 | ✅ |
| complete | target_ref | - | 5 | ✅ |
| delete | target_ref | - | 4 | ✅ |
| confirm | - | - | 7 | ❌ |
| clarify | - | - | 4 | ❌ |

### 16.4 Prompt 注入

**函数**: `build_intent_prompt_with_goal()`

```python
def build_intent_prompt_with_goal(
    base_prompt: str,
    detected_intent: Optional[str] = None,
    max_examples: int = 3
) -> str:
    """
    如果规则匹配检测到意图，注入对应的 Few-shot 示例
    """
    if detected_intent and detected_intent in GOAL_TEMPLATES:
        template = GOAL_TEMPLATES[detected_intent]
        # 注入: 提示 + 槽位信息 + Few-shot 示例
        ...
```

### 16.5 与渐进式策略的协作

```
用户输入
    │
    ▼
Goal 模板生效（Few-shot 注入）
    │
    ▼
信息完整？ ─── 是 → 确认/执行
    │
    否（轮次 1-2）
    ▼
追问用户
    │
    ▼
轮次 > 2？ ─── 是 → 渐进式策略生效
    │                - apply_goal_defaults()
    │                - 使用 default_values 填充
    否
    ▼
继续追问
```

**函数**: `apply_goal_defaults()`

```python
def apply_goal_defaults(intent: str, extracted_info: Dict, round_count: int) -> Dict:
    """
    当轮次超过阈值时，使用 Goal 模板的默认值填充缺失字段
    """
    if round_count <= todo_config.progressive_round_threshold:
        return extracted_info
    
    template = get_goal_template(intent)
    for key, default_value in template.default_values.items():
        if not result.get(key):
            result[key] = default_value
    return result
```

### 16.6 示例

**create 意图的 Few-shot 示例**：

```json
[
    {"input": "帮我记一下明天开会", "output": {"intent": "create", "extracted_info": {"title": "开会", "due_date": "明天"}}},
    {"input": "下周五前要完成报告", "output": {"intent": "create", "extracted_info": {"title": "完成报告", "due_date": "下周五"}}},
    {"input": "添加一个高优先级任务：紧急修复Bug", "output": {"intent": "create", "extracted_info": {"title": "紧急修复Bug", "priority": "高"}}}
]
```

---

## 17. 测试

### 17.1 单元测试

**文件**: `tests/unit/test_todo_nodes.py`

| 测试类 | 覆盖范围 |
|-------|---------|
| `TestResolveEntity` | resolve_entity 节点各分支 |
| `TestDispatchExecute` | 执行器分派逻辑 |
| `TestWaitForConfirmationReturnType` | 返回类型检查 |
| `TestInvokeLLMForIntent` | LLM 调用辅助函数 |

**运行**:

```bash
pytest tests/unit/test_todo_nodes.py -v
```

### 17.2 E2E 测试

**文件**: `web/e2e/todo_agent_stress_test.spec.cjs`

覆盖场景：
- T1: 简单创建
- T2: 批量创建
- T3: 模糊输入与澄清
- T4: 快速模式
- T5: 冲突检测
- T6: 多轮澄清与渐进式
- T7: 查询待办
- T8: 完成待办
- T9: 任务拆解

### 17.3 测试依赖注入

```python
# 注入 Mock 仓库
mock_repo = MockTodoRepository()
set_todo_dependencies(TodoDependencies(
    repository_factory=lambda: mock_repo,
    db_session_factory=lambda: mock_db_context()
))

# 测试后重置
reset_todo_dependencies()
```

---

## 注意事项

### 模型选择最佳实践

**前端不应硬编码模型 ID**，应让后端根据数据库配置决定默认模型：

```typescript
// ❌ 错误：硬编码模型 ID
export const DEFAULT_MODEL_ID = "deepseek-chat";

// ✅ 正确：使用 undefined，让后端决定
export const DEFAULT_MODEL_ID: string | undefined = undefined;
```

**原因**：
1. 后端 `t_llm_model.is_default` 字段统一管理默认模型
2. 避免因服务商余额不足导致全站不可用
3. 便于运维动态切换模型，无需重新部署前端

**后端模型选择逻辑** (`app/ai/llm_util.py`)：
1. 如果 `model_id` 有值，使用指定模型
2. 否则使用 `LLMConfigService.get_default_model_code()` 获取数据库默认模型
3. 如果数据库无默认模型，使用配置文件的环境变量

---

## 2026-02 实现状态（会话意图内核 V2）

- `todo_graph.analyze_intent` 已接入统一会话意图内核，输出 `turn_act/session_frame/frame_source_map/clarify_fsm_state/clarify_round`。
- `todo_intent_helpers` 已实现提取字段归一化（`target_ref/new_* -> canonical`），并优先消费 `pending_handoff.frame`。
- `resolve_entity` 已支持多候选二次消歧选择（`第 X 个 / ID 为 XX / 标题片段`），降低重复追问。
- 待办链路已加入超范围输入能力边界兜底（天气/新闻/问数/绘图等场景返回能力提示，不触发待办查询）。
- 回滚口径：Todo 侧当前默认启用 V2 内核（无独立运行时开关）；故障时优先降级 handoff 为纯文本，再视情况回退发布版本。

## 相关文档

| 文档 | 说明 |
|-----|------|
| [产品文档/待办助手需求](../../产品文档/待办助手需求.md) | 面向用户的功能介绍 |
| [AI模块设计](./AI模块设计.md) | AI 模块全局概览 |
| [测试管理/待办助手测试案例](../测试管理/待办助手测试案例.md) | 测试用例与已知问题 |
| [代码解读/多智能体工作流](../代码解读/多智能体工作流.md) | Todo Agent 与主图的集成 |
