# 聊天 API

聊天对话相关接口，支持流式响应和历史管理。

## 流式对话

### POST /api/v1/chat/stream

发起流式对话请求，返回 SSE 事件流。

**请求体**:

```json
{
  "prompt": "你好，请帮我查询待办",
  "thread_id": "abc123",
  "enable_thinking": false,
  "model_id": "qwen-max",
  "use_multi_agent": true,
  "attachments": [],
  "current_todo_id": null,
  "delay_ms": 0
}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `prompt` | string | 是 | 用户输入内容 |
| `thread_id` | string | 否 | 对话线程 ID，为空则新建 |
| `enable_thinking` | boolean | 否 | 是否启用深度思考 |
| `model_id` | string | 否 | 指定模型 |
| `use_multi_agent` | boolean | 否 | 是否使用多智能体 |
| `attachments` | array | 否 | 附件列表 |
| `current_todo_id` | int | 否 | 当前讨论的待办 ID |

**响应**: SSE 事件流

```
event: token
data: {"content": "你好"}

event: tool_start
data: {"name": "list_todos", "input": {}}

event: tool_end
data: {"name": "list_todos", "output": "找到3条待办"}

event: done
data: {"thread_id": "abc123"}
```

---

## 恢复中断

### POST /api/v1/chat/resume

恢复被中断的流程（用户确认后）。

**请求体**:

```json
{
  "thread_id": "abc123",
  "decision": {
    "type": "accept"
  }
}
```

| decision.type | 说明 |
|---------------|------|
| `accept` | 确认执行 |
| `reject` | 拒绝执行 |
| `edit` | 编辑后执行，需带 `args` 字段 |

---

## 获取对话列表

### GET /api/v1/chat/threads

获取当前用户的对话列表。

**查询参数**:

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `limit` | int | 50 | 最大返回数量 |

**响应**:

```json
[
  {
    "thread_id": "abc123",
    "title": "待办查询",
    "created_at": "2024-01-15T10:00:00",
    "updated_at": "2024-01-15T10:30:00"
  }
]
```

---

## 获取对话消息

### GET /api/v1/chat/threads/{thread_id}/messages

获取指定对话的消息历史。

**响应**:

```json
[
  {
    "id": 1,
    "thread_id": "abc123",
    "role": "human",
    "content_type": "text",
    "content": "你好",
    "created_at": "2024-01-15T10:00:00"
  },
  {
    "id": 2,
    "thread_id": "abc123",
    "role": "ai",
    "content_type": "markdown",
    "content": "你好！有什么可以帮你的？",
    "created_at": "2024-01-15T10:00:05"
  }
]
```

---

## 删除对话

### DELETE /api/v1/chat/threads/{thread_id}

删除对话及其关联资产。

**响应**:

```json
{
  "message": "已删除 10 条消息, 2 个资产",
  "thread_id": "abc123",
  "stats": {
    "messages": 10,
    "assets": 2
  }
}
```

---

## 更新对话标题

### PATCH /api/v1/chat/threads/{thread_id}/title

更新对话标题。

**请求体**:

```json
{
  "title": "新标题"
}
```
