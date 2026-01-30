# ToolNode 重构可行性评估

## 评估日期
2026-01-29

## 背景
根据 LangGraph 最佳实践，评估是否应该使用 `ToolNode` 重构当前的手动工具调用方式。

## 当前实现
```python
# 手动在节点中调用工具函数
def execute_operation(state: TodoAgentState) -> Dict:
    if action == "create":
        result = _execute_create(data, state)
    elif action == "update":
        result = _execute_update(data, state)
    # ...
```

## ToolNode 方式
```python
from langgraph.prebuilt import ToolNode, tools_condition

@tool
def create_todo(title: str, priority: int) -> str:
    """创建待办事项"""
    ...

tool_node = ToolNode([create_todo, update_todo, delete_todo])
graph.add_node("tools", tool_node)
graph.add_conditional_edges("agent", tools_condition, {
    "tools": "tools",
    "end": END
})
```

## 评估结论：**不建议当前重构**

### 原因分析

#### 1. Human-in-the-Loop 需求
Todo Agent 的核心特性是用户确认流程：
- 创建/更新/删除操作都需要用户确认
- 使用 `interrupt()` 实现等待确认
- ToolNode 不直接支持这种确认流程

#### 2. 实体解析前置需求
当前流程：
```
analyze_intent → resolve_entity → confirm → execute
```
- `resolve_entity` 负责将用户描述解析为具体 ID
- 这个步骤在工具调用之前进行
- ToolNode 假设工具参数已经完整

#### 3. 复杂的意图分析
- LLM 分析用户意图，不是直接生成工具调用
- 需要规则化检测（关键词匹配）辅助
- ToolNode 更适合 Agent 直接输出工具调用的场景

#### 4. 错误处理定制化
- 当前实现有细化的错误处理
- 不同错误类型有不同的用户提示
- ToolNode 的错误处理较为通用

### ToolNode 适用场景
ToolNode 更适合以下场景：
- Agent 直接决定调用哪个工具
- 不需要额外的确认流程
- 工具参数可以直接从用户输入中提取
- 简单的 ReAct Agent 模式

### 当前架构的优势
1. **清晰的职责分离**：意图分析 → 实体解析 → 确认 → 执行
2. **灵活的确认流程**：支持跳过确认（快速模式）
3. **精细的错误处理**：针对不同场景的友好提示
4. **易于测试**：依赖注入支持独立测试各个模块

### 未来考虑
如果需求变化，可以考虑以下改进：
1. **查询操作**可以使用 ToolNode（不需要确认）
2. 引入 **ValidationNode** 进行执行前验证
3. 使用 `@tool` 装饰器标准化工具定义

## 建议
1. 保持当前手动工具调用的实现方式
2. 考虑为查询类操作单独引入 ToolNode
3. 持续关注 LangGraph 的最佳实践更新
