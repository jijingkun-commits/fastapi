# 待办 Agent 设计详解

> **状态**: 已更新 (LangGraph 重构版)
> **验证日期**: 2026-01-29
> **代码对应**: `app/ai/workflow/todo_graph.py`, `app/ai/agents/resolve_node.py`, `app/ai/tools/todo_tools.py`

## 1. 核心设计理念

Todo Agent 旨在提供极其灵活且智能的任务管理体验。核心设计原则包括：

*   **极简输入**: 用户只需提供最少信息（如"明天开会"），Agent 自动补充其余字段。
*   **交互式确认**: Agent 不会静默创建，而是提取信息后向用户确认，并引导补充（如提醒时间）。
*   **状态全生命周期管理**: 支持从待办、进行中、挂起、完成到删除的全流程。
*   **逻辑删除**: 数据安全第一，所有删除操作均为软删除（逻辑删除）。

## 2. 功能特性

### 2.1 智能创建

Agent 会从自然语言中提取以下信息：
*   **必填**: `title`
*   **可选**:
    *   `due_date` / `start_time` (智能日期解析)
    *   `priority` (默认 2-中)
    *   `category` (如工作、生活)
    *   `reminders` (是否提醒、提前时间)

### 2.2 状态管理

系统支持 5 种标准状态：
1.  `todo` (待办): 初始状态
2.  `in_progress` (进行中): 进度 1-99%
3.  `on_hold` (挂起): 暂停执行
4.  `done` (已完成): 进度 100%
5.  `cancelled` (已取消): 放弃执行

**进度自动化**:
*   更新进度到 100% 会自动将状态置为 `done`。
*   标记为 `done` 会自动将进度置为 100%。

### 2.3 批量操作 (UI 专属)

*   **说明**: Agent 对话层**不再支持**通过自然语言触发批量创建或完成。
*   **支持渠道**: 仅前端 UI 支持批量勾选操作，后台通过 `batch_complete` 接口支持。

### 2.4 数据安全

*   **逻辑删除**: `is_deleted` 字段控制显隐。默认查询接口会过滤掉 `is_deleted=True` 的记录。
*   **审计日志**: 所有关键操作（创建、更新、删除、完成）都会通过 `TodoHistory` 表记录，包括操作类型、变更字段、旧值和新值。

## 3. 技术实现

### 3.1 数据模型 (Todo)

| 字段 | 类型 | 说明 |
| :--- | :--- | :--- |
| `id` | Integer | 主键 |
| `user_id` | Integer | 用户归属 |
| `title` | String | 标题 |
| `status` | Enum | todo, in_progress, on_hold, done, cancelled |
| `priority` | Integer | 1=高, 2=中, 3=低 |
| `is_deleted` | Boolean | 逻辑删除标记 |
| `progress` | Integer | 0-100 |

### 3.2 关键工具 (Tools)

位于 `app/ai/tools/todo_tools.py`:

*   `add_todo`: 创建任务，支持自然语言日期解析。
*   `list_todos`: 支持按 status, category, priority, keyword 过滤。
*   `update_progress`: 更新进度和备注，自动联动状态。
*   `update_todo`: 通用更新接口。
*   `delete_todo`: 软删除接口。

位于 `app/ai/tools/batch_todo_tools.py`:
*   `batch_complete_todos`: 批量完成。

### 3.3 Repository 层

位于 `app/repositories/todo_repository.py`:

*   实现所有数据库原子操作。
*   `delete(soft=True)`: 执行 `UPDATE t_todo SET is_deleted=true`。
*   `batch_complete`: 执行批量 UPDATE 语句，并批量插入 History 记录，保证高性能。

## 4. LangGraph 状态机架构

### 4.1 核心节点

| 节点 | 文件位置 | 职责 |
| :--- | :--- | :--- |
| `analyze_intent` | `todo_graph.py` | 调用 LLM 分析用户意图，提取待办信息 |
| `resolve_entity` | `resolve_node.py` | 实体解析，将模糊标识转换为具体 todo_id |
| `ask_confirmation` | `todo_graph.py` | 生成确认消息，构造前端 Confirmation Card |
| `wait_for_confirmation` | `todo_graph.py` | 使用 `interrupt()` 等待用户确认 |
| `execute_operation` | `todo_graph.py` | 执行具体操作（增删改查） |
| `clarify_node` | `todo_enhanced_nodes.py` | 处理信息不完整时的澄清追问 |

### 4.2 状态流转图

```
┌──────────────┐
│   analyze    │
└──────┬───────┘
       │
       ▼
  ┌────────────┐
  │ route_next │ ──── clarify ────► END
  └────┬───────┘
       │ resolve
       ▼
┌──────────────┐
│   resolve    │
└──────┬───────┘
       │
       ▼
  ┌────────────────┐
  │route_after_res │ ──── clarify ────► END
  └────┬───────────┘
       │ confirm
       ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   confirm    │────►│ wait_confirm │────►│   execute    │
└──────────────┘     └──────────────┘     └──────┬───────┘
                                                 │
                                                 ▼
                                                END
```

### 4.3 节点返回类型规范

**重要**: 所有节点函数必须返回 `Dict`（增量更新），而非直接修改 state。

```python
# ✅ 正确写法
def resolve_entity(state: TodoAgentState) -> Dict:
    return {"pending_operation": updated_op}

# ❌ 错误写法
def resolve_entity(state: TodoAgentState) -> TodoAgentState:
    state["pending_operation"] = updated_op  # 直接修改
    return state
```

### 4.4 执行器映射模式

`execute_operation` 节点使用 `executor_map` 模式统一分派操作：

```python
# 定义映射表
_EXECUTOR_MAP = {
    "create": _execute_create,
    "update": _execute_update,
    "delete": _execute_delete,
    "complete": _execute_complete,
    "query": _execute_query,
}

# 统一分派
def _dispatch_execute(action: str, data: Dict, state: TodoAgentState) -> ToolResult:
    executor = _EXECUTOR_MAP.get(action)
    if executor:
        return executor(data, state)
    return ToolResultBuilder.error(f"暂不支持操作: {action}")
```

**优势**:
- 避免冗长的 if-elif 链
- 便于添加新操作类型
- 支持动态注册执行器

### 4.5 单元测试

测试文件: `tests/unit/test_todo_nodes.py`

| 测试类 | 测试数 | 覆盖范围 |
| :--- | :--- | :--- |
| `TestResolveEntity` | 7 | 实体解析节点各分支 |
| `TestDispatchExecute` | 3 | 执行器分派逻辑 |
| `TestWaitForConfirmationReturnType` | 1 | 返回类型检查 |
| `TestInvokeLLMForIntent` | 2 | LLM 调用辅助函数 |

运行测试:
```bash
pytest tests/unit/test_todo_nodes.py -v
```
