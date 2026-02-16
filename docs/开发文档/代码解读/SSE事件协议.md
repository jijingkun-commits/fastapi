# SSE 流式协议规范

> **用途**: 定义后端与前端之间的 SSE 通信协议，确保事件处理一致。
>
> **权威性说明（2026-02）**：本文档是 SSE 事件清单的单一权威来源。`done` 仅用于生命周期收口，结构化数据只能通过 `result` 传递。

---

## 📡 协议概述

本项目使用 **Server-Sent Events (SSE)** 实现流式响应，支持多种结构化事件类型。

### 基本格式

```
event: {event_type}
data: {json_payload}

```

- 每个事件以两个换行符 (`\n\n`) 结尾
- `data` 字段使用 JSON 格式
- 所有事件包含 `type`、`data`、`node`（可选）字段

---

## 🎯 事件类型定义

### 完整事件列表

| 事件类型 | 用途 | 触发时机 |
|----------|------|----------|
| `init` | 流初始化 | 连接建立时 |
| `token` | AI 文本输出 | LLM 生成 token 时 |
| `thinking` | 思考过程 | 深度思考模式下 |
| `tool_start` | 工具调用开始 | Tool 执行前 |
| `tool_end` | 工具调用结束 | Tool 执行后 |
| `status` | 状态更新（含 `phase` 阶段） | 长时间操作时 |
| `result` | 结构化结果 | 返回卡片数据时 |
| `kb_images` | 知识库图片映射 | RAG 返回图片占位符映射时 |
| `confirmation` | 确认请求 | 需要用户确认时 |
| `clarification` | 澄清问题 | 需要补充信息时 |
| `handoff` | 专家切换通知 | Supervisor 委派专家时 |
| `interrupt` | 中断等待 | Human-in-the-loop |
| `done` | 流结束 | 处理完成时 |
| `error` | 错误 | 发生异常时 |

### emit 函数与事件来源对照

| 事件类型 | 主要发送来源 | `emit_*` 函数 |
|----------|-------------|---------------|
| `init` | `ChatService.stream` | - |
| `token` | Graph 节点 / 流包装器 | `emit_token` |
| `thinking` | Graph 节点 / 流包装器 | `emit_thinking` |
| `tool_start` | 流包装器 | `emit_tool_start` |
| `tool_end` | 流包装器 | `emit_tool_end` |
| `status` | Graph 节点 | `emit_status` |
| `result` | Graph 节点 / 工具 | `emit_result` |
| `kb_images` | 知识库检索链路 | `emit_kb_images` |
| `confirmation` | Graph 节点 | `emit_confirmation` |
| `clarification` | Graph 节点 | `emit_clarification` |
| `handoff` | Supervisor 事件桥接 | -（使用 `AgentEvent.handoff()`） |
| `interrupt` | LangGraph `interrupt()` 检测与转发 | - |
| `done` | `ChatService.stream` | `emit_done`（可选） |
| `error` | Graph 节点 / Service 异常处理 | `emit_error` |

### 协议约束（2026-02 严格切换）

1. **结构化数据单通道**：`result` 是唯一结构化载荷通道，格式为 `data_type + data + message?`。
2. **`done` 仅生命周期收口**：`done` 仅允许 `thread_id`、`message_id`、`final_content?` 字段。
3. **禁止在 `done` 携带结构化数据**：`done.additional_kwargs` 已废弃，不再作为前端卡片渲染输入。

---

## 📋 事件数据结构

### `init` - 流初始化

```typescript
{
  type: "init",
  data: {
    thread_id: string  // 对话线程 ID
  }
}
```

### `token` - AI 文本输出

```typescript
{
  type: "token",
  data: {
    content: string,           // 文本内容
    reasoning_content?: string // DeepSeek 推理内容
  }
}
```

### `thinking` - 思考过程

```typescript
{
  type: "thinking",
  data: {
    content: string  // 思考内容
  }
}
```

### `tool_start` - 工具调用开始

```typescript
{
  type: "tool_start",
  data: {
    name: string,  // 工具名称
    input: any     // 输入参数
  }
}
```

### `tool_end` - 工具调用结束

```typescript
{
  type: "tool_end",
  data: {
    name: string,   // 工具名称
    output: string  // 输出结果（已截断）
  }
}
```

### `status` - 状态更新

```typescript
{
  type: "status",
  data: {
    message: string,                          // 状态消息
    phase: "processing" | "generating" | "done" // 状态阶段
  }
}
```

> 兼容约定：历史事件若缺少 `phase`，前端按 `processing` 处理。

### `result` - 结构化结果

```typescript
{
  type: "result",
  data: {
    data_type: string,   // 数据类型：todo_list / image / chart
    data: any,           // 结构化数据
    message?: string     // 可选文本描述
  }
}
```

**data_type 类型：**

| data_type | 用途 | data 结构 |
|-----------|------|-----------|
| `todo_list` | 待办列表 | `{todos: Todo[]}` |
| `image` | 图片 | `{url: string}` |
| `chart` | 图表 | `{type: string, ...}` |

### `kb_images` - 知识库图片映射

```typescript
{
  type: "kb_images",
  data: {
    images: Record<string, string> // 占位符索引到 URL 的映射，如 {"1": "https://..."}
  }
}
```

### `handoff` - 专家切换通知

```typescript
{
  type: "handoff",
  data: {
    target_agent: string,      // 目标专家
    task_description: string   // 委派任务描述
  }
}
```

### `confirmation` - 确认请求

```typescript
{
  type: "confirmation",
  data: {
    operation: {
      action: string,      // 操作类型
      target: string,      // 操作目标
      details: any         // 详细信息
    },
    message: string        // 确认提示
  }
}
```

### `clarification` - 澄清问题

```typescript
{
  type: "clarification",
  data: {
    questions: string[],   // 问题列表
    message?: string       // 引导消息
  }
}
```

### `interrupt` - 中断等待

```typescript
{
  type: "interrupt",
  data: {
    thread_id: string,
    interrupt_id: string,
    value: {
      action_requests?: Array<{
        name: string,
        args: Record<string, unknown>,
        description?: string
      }>,
      review_configs?: Array<{
        action_name: string,
        allowed_decisions: string[]
      }>,
      message?: string
    }
  }
}
```

### `done` - 流结束

```typescript
{
  type: "done",
  data: {
    thread_id: string,
    message_id?: number,             // 数据库消息 ID
    final_content?: string           // 可选兜底文本
  }
}
```

> **注意**: `done` 只负责流结束与消息绑定，不承载结构化卡片数据。前端应在 `result` 事件阶段处理并存储结构化数据。

### `error` - 错误

```typescript
{
  type: "error",
  data: {
    message: string  // 错误消息
  }
}
```

---

## 🔄 前端处理流程

### 事件处理

**文件**: `web/src/hooks/useSSEStream.ts`

```typescript
const callbacks: StreamCallbacks = {
  onInit: (threadId) => {
    setThreadId(threadId);
  },
  onToken: (token) => {
    appendToAiMessage(aiId, token);
  },
  onThinking: (content) => {
    handleThinking(aiId, content);
  },
  onToolStart: (name, input) => {
    addToolCallToMessage(aiId, name, input);
  },
  onToolEnd: (name, output) => {
    console.debug(`工具 ${name} 执行完成`);
  },
  onStatus: (message) => {
    setCurrentStatus(message);  // 显示在 UI 中
  },
  onResult: (data) => {
    if (data.data_type === 'image') {
      appendImageToAiMessage(aiId, data.data.url);
    } else if (data.data_type === 'todo_list') {
      // 在 result 阶段存入 additional_kwargs 用于渲染
    }
  },
  onInterrupt: (data) => {
    setInterrupt(data);
    setIsLoading(false);
  },
  onDone: (threadId, messageId) => {
    bindMessageId(aiId, messageId);
    setCurrentStatus(null);  // 清除状态
    setIsLoading(false);
    refreshThreads();
  },
  onError: (message) => {
    setError(new Error(message));
    toast.error("请求失败", { description: message });
  }
};
```

### currentStatus UI 显示

**文件**: `web/src/components/chat/messages/ai.tsx`

当后端发送 `status` 事件时，前端会显示状态消息：

```tsx
const currentStatus = thread.currentStatus;

if (isLoading && currentStatus) {
  return (
    <div className="flex items-center gap-2 text-xs text-gray-500 animate-pulse">
      <span className="inline-block h-1.5 w-1.5 rounded-full bg-blue-500 animate-ping"></span>
      {currentStatus}
    </div>
  );
}
```

### 恢复中断流程

```typescript
// 用户批准
await resumeChat(threadId, { type: 'accept' }, callbacks);

// 用户拒绝
await resumeChat(threadId, { type: 'reject', message: '...' }, callbacks);

// 用户修改参数
await resumeChat(threadId, { type: 'edit', args: {...} }, callbacks);
```

---

## 🔧 后端发送示例

### 在 Graph 节点中发送

```python
from langgraph.config import get_stream_writer
from app.ai.events import emit_status, emit_result, emit_token

def my_node(state):
    writer = get_stream_writer()
    
    # 发送状态
    emit_status(writer, "正在处理...")
    
    # 处理逻辑...
    
    # 发送结果
    emit_result(writer, "todo_list", {"todos": todos}, "找到 5 条待办")
    
    return state
```

### 在 ChatService 中发送

```python
# 格式化 SSE 事件
def _format_sse(self, event_type: str, data: dict) -> str:
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

# 发送事件
yield self._format_sse("token", {"content": token})
```

---

## 📊 工具输出处理

### 截断规则

| 场景 | 长度限制 | 常量 |
|------|----------|------|
| 预览（前端显示） | 500 字符 | `TOOL_OUTPUT_PREVIEW_LEN` |
| 存储（数据库） | 2000 字符 | `TOOL_OUTPUT_STORAGE_LEN` |

### 图片处理
 
 ✅ **统一处理方式**：所有图片来源使用 `result` 事件实时流式发送。
 
 | 图片来源 | 工具 | 处理方式 |
 |---------|------|---------|
 | Agent 生成 | `fig_inter` | `emit_result("image", {url})` |
 | 知识库检索 | `knowledge_search` | `emit_result("image", {url})` |
 
 ```python
 # 后端发送（两种工具统一）
 emit_result(writer, "image", {"url": proxy_url}, "图片描述")
 ```
 
 ```typescript
 // 前端接收 (onResult)
 if (data.data_type === "image") {
     appendImageToAiMessage(aiId, data.data.url);
 }
 ```
 
 **去重机制**：前端 `appendImageToAiMessage` 自动检测重复 URL，防止同一图片显示多次。
 
 ⚠️ **已废弃方式**：旧版使用 `##N$$` 标记引用的方式已不再使用。
```
