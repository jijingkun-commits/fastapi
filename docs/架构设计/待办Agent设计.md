# 待办 Agent 设计详解

> **状态**: 已发布
> **验证日期**: 2026-01-21
> **代码对应**: `app/ai/tools/todo_tools.py`, `app/repositories/todo_repository.py`

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

### 2.3 批量操作

为了提高效率，系统支持批量操作工具 `batch_complete_todos`：
*   **场景**: "把今天的待办都完成了"
*   **逻辑**: Agent 先检索符合条件的 Todo ID，然后一次性调用批量完成接口。

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
