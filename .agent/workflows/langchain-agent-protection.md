---
description: LangChain/LangGraph Agent 创建规则
---

## 当前版本

- Python: 3.11+
- langchain: 1.2.0
- langgraph: 1.0.5

## 核心 API - langchain 1.2.0

### 1. create_agent（新 API，推荐使用）

```python
from langchain.agents import create_agent

agent = create_agent(
    model=llm,                          # 语言模型（或模型名字符串）
    tools=tools,                        # 工具列表
    system_prompt=SYSTEM_PROMPT,        # 系统提示词
    middleware=[my_middleware],         # 中间件列表
    response_format=MyFormat,           # 可选：响应格式
    state_schema=MyState,               # 可选：自定义状态 schema
    context_schema=MyContext,           # 可选：上下文 schema
    checkpointer=checkpointer,          # 可选：检查点存储
    store=store,                        # 可选：持久化存储
    interrupt_before=["node_name"],     # 可选：在指定节点前中断
    interrupt_after=["node_name"],      # 可选：在指定节点后中断
    debug=False,                        # 可选：调试模式
    name="my_agent",                    # 可选：Agent 名称
    cache=my_cache,                     # 可选：缓存
)
```

### 2. Middleware 装饰器

```python
from langchain.agents.middleware import (
    before_model,      # 模型调用前
    after_model,       # 模型调用后
    before_agent,      # Agent 执行前
    after_agent,       # Agent 执行后
    wrap_model_call,   # 包装模型调用
    wrap_tool_call,    # 包装工具调用
)

@before_model
def trim_messages(state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
    """模型调用前处理消息。"""
    messages = state["messages"]
    if len(messages) <= 3:
        return None  # 无需修改
    
    # 保留第一条和最后几条消息
    first_msg = messages[0]
    recent_messages = messages[-3:]
    new_messages = [first_msg] + recent_messages
    
    return {
        "messages": [
            RemoveMessage(id=REMOVE_ALL_MESSAGES),
            *new_messages
        ]
    }

@wrap_tool_call
def image_capture(request, execute, runtime):
    """拦截工具输出，捕获图片 URL。"""
    result = execute(request)
    
    if result and result.content:
        # 处理工具输出中的图片
        for match in re.finditer(r'!\[[^\]]*\]\(([^)]+)\)', str(result.content)):
            url = match.group(1)
            print(f"捕获图片: {url}")
    
    return result

# 使用中间件
agent = create_agent(
    model="gpt-4",
    tools=[my_tool],
    system_prompt="You are a helpful assistant",
    middleware=[trim_messages, image_capture],
)
```

### 3. 可用的内置中间件

```python
from langchain.agents.middleware import (
    # 功能型中间件
    SummarizationMiddleware,        # 消息摘要
    ModelCallLimitMiddleware,       # 模型调用限制
    ToolCallLimitMiddleware,        # 工具调用限制
    ModelRetryMiddleware,           # 模型重试
    ToolRetryMiddleware,            # 工具重试
    ModelFallbackMiddleware,        # 模型降级
    HumanInTheLoopMiddleware,       # 人工介入
    PIIMiddleware,                  # PII 检测
    
    # 工具型中间件
    ShellToolMiddleware,            # Shell 工具
    FilesystemFileSearchMiddleware, # 文件搜索
)
```

## 禁止事项

- **不要**使用 `from langgraph.prebuilt import create_react_agent`（旧 API）
- **不要**使用 `prompt` 参数（应使用 `system_prompt`）
- **不要**使用 `pre_model_hook` / `post_model_hook`（应使用 `middleware` + 装饰器）
- **不要**手动创建 `ToolNode`（`create_agent` 内部处理）

## 从旧 API 迁移

| 旧写法 (langgraph.prebuilt) | 新写法 (langchain.agents) |
|---------------------------|-------------------------|
| `create_react_agent` | `create_agent` |
| `prompt=...` | `system_prompt=...` |
| `pre_model_hook=func` | `@before_model` + `middleware=[...]` |
| `ToolNode(tools, wrap_tool_call=...)` | `@wrap_tool_call` + `middleware=[...]` |

## 升级命令

```bash
# 需要 Python 3.10+
pip install langchain==1.2.0 langgraph==1.0.5
```
