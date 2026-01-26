# SSE 事件系统解读

本文档解读事件系统的实现细节。

**文件**: `app/ai/events.py`

## 事件定义

```python
class EventType(str, Enum):
    TOKEN = "token"
    THINKING = "thinking"
    TOOL_START = "tool_start"
    TOOL_END = "tool_end"
    STATUS = "status"
    RESULT = "result"
    CONFIRMATION = "confirmation"
    INTERRUPT = "interrupt"
    DONE = "done"
    ERROR = "error"
```

---

## 事件发送函数

### emit_token

```python
def emit_token(writer, content: str, node: str = ""):
    """发送文本 token 事件。"""
    writer({
        "type": "token",
        "data": {"content": content},
        "node": node
    })
```

### emit_result

```python
def emit_result(writer, data_type: str, data: dict, message: str = "", node: str = ""):
    """发送结构化结果事件。"""
    writer({
        "type": "result",
        "data": {
            "data_type": data_type,  # todo_list / image / chart
            "data": data,
            "message": message
        },
        "node": node
    })
```

### emit_confirmation

```python
def emit_confirmation(writer, operation: dict, message: str, node: str = ""):
    """发送确认请求事件。"""
    writer({
        "type": "confirmation",
        "data": {
            "operation": operation,
            "message": message
        },
        "node": node
    })
```

---

## 前端处理

**文件**: `web/src/hooks/useSSEStream.ts`

```typescript
function parseSSEEvent(line: string): SSEEvent | null {
  if (line.startsWith("data: ")) {
    return JSON.parse(line.slice(6));
  }
  return null;
}

function handleEvent(event: SSEEvent, callbacks: StreamCallbacks) {
  switch (event.type) {
    case "token":
      callbacks.onToken?.(event.data.content);
      break;
    case "tool_start":
      callbacks.onToolStart?.(event.data.name, event.data.input);
      break;
    case "result":
      callbacks.onResult?.(event.data);
      break;
    case "done":
      callbacks.onDone?.(event.data.thread_id);
      break;
  }
}
```
