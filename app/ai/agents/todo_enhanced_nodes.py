"""待办Agent增强节点 - 多轮对话能力扩展。

新增节点:
- clarify_node: 澄清追问
- conflict_detection_node: 冲突检测  
- task_decomposition_node: 任务拆解
"""
import logging
from typing import Dict, List, Optional
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables.config import RunnableConfig

from app.ai.llm_util import get_llm
from app.ai.workflow.todo_graph import TodoAgentState

# 🆕 导入自定义事件工具
from langgraph.config import get_stream_writer
from app.ai.events import emit_clarification, emit_token, emit_status

logger = logging.getLogger(__name__)

from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field  # 使用标准 pydantic（LangChain 1.x+ 兼容）

# ==================== Pydantic 响应模型 ====================

class ClarificationResult(BaseModel):
    """澄清节点输出模型"""
    needs_clarification: bool = Field(description="是否需要进一步澄清")
    missing_info: List[str] = Field(default=[], description="缺失的信息列表")
    questions: List[str] = Field(default=[], description="需要向用户提问的问题列表")
    context_summary: Optional[str] = Field(None, description="上下文摘要")

class SubTask(BaseModel):
    """子任务模型"""
    title: str
    dependencies: List[str] = []
    estimated_hours: Optional[float] = None

class DecompositionResult(BaseModel):
    """拆解节点输出模型"""
    main_task: str
    subtasks: List[SubTask]
    external_dependencies: List[str] = []


# ==================== 澄清节点 ====================

CLARIFY_PROMPT = """你是待办助手的澄清专家。

## 任务
评估信息完整度,生成精准追问。

## 场景识别

### 场景1: 模糊起始
**用户**: "帮我理一理", "太多了", "整理一下"
**问题**: 缺少范围、时间、类型
**追问**:
- 您希望整理哪个时间段的任务?(本周/本月/全部)
- 是否只关注工作相关的事项?
- 有特别紧急需要优先处理的吗?

### 场景2: 高层级输入
**用户**: "有几个项目要做"
**问题**: 缺少项目细节


**追问**:
- 这些项目分别是什么?
- 每个项目的截止时间是?  
- 您负责哪些部分?

### 场景3: 隐含需求
**用户**: "领导下周要听汇报"
**问题**: 未明确要做什么
**追问**:
- 汇报的主题是什么?
- 需要准备哪些材料?(PPT/报告/数据)
- 有哪些关键要点needs覆盖?

## 输出格式
```json
{
  "needs_clarification": true,
  "missing_info": ["具体任务", "时间范围"],
  "questions": [
    "您希望整理哪个时间段的任务?",
    "是否只关注工作相关的事项?"
  ],
  "context_summary": "用户提到有很多事情,但未具体说明"
}
```
"""

def clarify_node(state: TodoAgentState) -> TodoAgentState:
    """澄清节点 - 识别信息不完整并生成追问。
    
    支持三种模式:
    1. 纯澄清: 无待办信息,生成开放式追问
    2. 确认式澄清: 有部分待办信息,展示待办详情并询问用户确认或补充
    3. 🆕 逐项目追问: 多个项目时依次追问每个项目详情
    """
    logger.info("=== clarify_node节点 ===")
    
    # 🆕 获取 StreamWriter 用于发送自定义事件
    writer = get_stream_writer()
    
    # 🆕 模式3: 逐项目追问循环
    project_queue = state.get("project_queue", [])
    current_idx = state.get("current_project_index", 0)
    
    if project_queue and current_idx < len(project_queue):
        current_project = project_queue[current_idx]
        remaining = len(project_queue) - current_idx
        
        # 生成针对当前项目的追问
        lines = [f"📋 关于 **{current_project}** (还有 {remaining} 个项目待讨论)：", ""]
        lines.append("请告诉我：")
        lines.append("1. 这个项目的主要任务是什么？")
        lines.append("2. 截止时间是什么时候？")
        lines.append("3. 您负责哪些部分？")
        lines.append("")
        lines.append("*回复后我会继续询问下一个项目*")
        
        clarify_text = "\n".join(lines)
        state["messages"].append(AIMessage(content=clarify_text))
        
        # 🆕 发送澄清事件给前端
        emit_clarification(writer, 
                          questions=["1. 这个项目的主要任务是什么？", "2. 截止时间是什么时候？", "3. 您负责哪些部分？"],
                          message=clarify_text,
                          node="clarify_node")
        
        state["current_project_index"] = current_idx + 1
        state["current_focus"] = current_project
        logger.info(f"逐项目追问: {current_project} ({current_idx + 1}/{len(project_queue)})")
        return state
    
    # 检查是否有部分待办信息
    pending_op = state.get("pending_operation")
    
    if pending_op and pending_op.get("needs_clarification"):
        # 模式2: 确认式澄清 (有部分待办信息)
        data = pending_op["data"]
        action = pending_op.get("action", "create")
        
        # 提取所有可能的字段
        title = data.get("title") or "未命名待办"
        time_str = data.get("time") or data.get("due_date") or ""
        priority = data.get("priority")
        category = data.get("category") or ""
        description = data.get("description") or ""
        location = data.get("location") or ""  # 地点字段
        is_urgent = data.get("is_urgent", False)
        affected_tasks = data.get("affected_tasks", [])
        
        # 优先级映射
        priority_map = {1: "🔴 高", 2: "🟡 中", 3: "🟢 低"}
        priority_str = priority_map.get(priority, "中")
        
        # 构建详细的待办信息展示
        if is_urgent:
            lines = ["🚨 **紧急任务** 📝", ""]
        else:
            lines = ["我可以帮您记录这个待办 📝", ""]
            
        lines.append(f"**待办信息：**")
        lines.append(f"- 📝 标题：{title}")
        if time_str:
            lines.append(f"- ⏰ 时间：{time_str}")
        else:
            lines.append(f"- ⏰ 时间：未设置")
        if location:
            lines.append(f"- 📍 地点：{location}")
        lines.append(f"- ⭐ 优先级：{priority_str}")
        if category:
            lines.append(f"- 🏷️ 分类：{category}")
        if description:
            lines.append(f"- 📄 描述：{description}")
        
        # 🆕 Phase 3: 显示受影响的任务
        if affected_tasks:
            lines.append("")
            lines.append("⚠️ **注意：以下同日任务可能需要调整：**")
            for task in affected_tasks[:5]:  # 最多显示5个
                lines.append(f"  - {task}")
            if len(affected_tasks) > 5:
                lines.append(f"  - ...还有 {len(affected_tasks) - 5} 个任务")
        
        # 添加确认提示
        lines.append("")
        lines.append("您可以：")
        lines.append("1. 回复「**确认**」直接创建")
        lines.append("2. 补充更多信息（如具体时间、地点、提醒等）")
        
        clarify_text = "\n".join(lines)
        state["messages"].append(AIMessage(content=clarify_text))
        
        # 🆕 发送澄清事件给前端
        emit_clarification(writer, 
                          questions=["1. 回复「确认」直接创建", "2. 补充更多信息"],
                          message=clarify_text,
                          node="clarify_node")
        
        logger.info(f"生成确认式澄清: {title}")
        
    else:
        # 模式1: 纯澄清 (无待办信息)
        messages = state.get("messages", [])
        last_user_msg = None
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                last_user_msg = msg.content
                break
        
        if not last_user_msg:
            return state
        
        # 调用LLM评估
        llm = get_llm()
        clarify_messages = [
            SystemMessage(content=CLARIFY_PROMPT),
            HumanMessage(content=f"用户消息: {last_user_msg}\n\n当前上下文: {state.get('conversation_context', {})}")
        ]
        
        # 初始化 Parser
        parser = JsonOutputParser(pydantic_object=ClarificationResult)
        
        try:
            # 🔧 添加 internal_thought tag，防止原始 JSON 被流式发送到前端
            response = llm.invoke(clarify_messages, config={"tags": ["internal_thought"]})
            
            # ✅ 使用标准 Parser 解析，无需正则 hacking
            result = parser.parse(response.content)
            
            if result.get("needs_clarification"):
                # 生成追问消息
                questions = result.get("questions", [])
                if questions:
                    clarify_text = "我需要了解更多信息:\n\n" + "\n".join([f"{i+1}. {q}" for i, q in enumerate(questions)])
                else:
                    # fallback: 使用 missing_info
                    missing = result.get("missing_info", [])
                    if missing:
                        clarify_text = "请补充以下信息:\n\n" + "\n".join([f"• {m}" for m in missing])
                    else:
                        clarify_text = "请告诉我更多细节，以便我更好地帮助你。"
                
                state["pending_clarifications"] = questions
                state["messages"].append(AIMessage(content=clarify_text))
                
                # 🆕 发送澄清事件给前端
                emit_clarification(writer, 
                                  questions=questions,
                                  message=clarify_text,
                                  node="clarify_node")
                
                logger.info(f"生成澄清追问: {len(questions)}个问题")
            else:
                # 不需要澄清，生成友好提示
                friendly_msg = "好的，请告诉我具体需要完成什么任务？"
                state["messages"].append(AIMessage(content=friendly_msg))
            
        except json.JSONDecodeError as e:
            logger.error(f"澄清节点 JSON 解析失败: {e}, 原始内容: {response.content[:200]}")
            # 降级: 生成友好的提示消息,避免JSON泄漏
            fallback_msg = "我需要了解更多信息:\n\n请告诉我:\n1. 您希望完成什么任务?\n2. 相关的时间安排是?\n3. 有什么特别要注意的吗?"
            state["messages"].append(AIMessage(content=fallback_msg))
        except Exception as e:
            logger.error(f"澄清节点失败: {e}")
            # 降级: 生成友好的提示消息,避免JSON泄漏
            fallback_msg = "我需要了解更多信息:\n\n请告诉我:\n1. 您希望完成什么任务?\n2. 相关的时间安排是?\n3. 有什么特别要注意的吗?"
            state["messages"].append(AIMessage(content=fallback_msg))
    
    return state


# ==================== 冲突检测节点 ====================

def conflict_detection_node(state: TodoAgentState) -> TodoAgentState:
    """冲突检测节点 - 检测时间/优先级/工作量冲突。
    
    Phase 2 增强：
    1. 使用 blocked_weekdays 检测不可用日期冲突
    2. 基于工时估算检测工作量超载
    3. 生成调整建议
    """
    logger.info("=== conflict_detection_node节点 ===")
    
    draft_todos = state.get("draft_todos", [])
    time_constraints = state.get("time_constraints", {})
    conflicts = []
    
    if not draft_todos:
        return state
    
    # 获取 blocked_weekdays (来自 NaturalTimeParser 提取)
    blocked_weekdays = set(time_constraints.get("blocked_weekdays", []))
    
    # 1. 时间冲突检测 - 按日期分组
    deadline_groups = {}
    for todo in draft_todos:
        deadline = todo.get("due_date")
        if deadline:
            # 解析日期 (支持 ISO 格式)
            try:
                from datetime import datetime
                if isinstance(deadline, str):
                    dt = datetime.fromisoformat(deadline.replace('Z', '+00:00'))
                else:
                    dt = deadline
                date_key = dt.date().isoformat()
                weekday = dt.weekday() + 1  # 1=周一, 7=周日
                
                if date_key not in deadline_groups:
                    deadline_groups[date_key] = {"todos": [], "weekday": weekday}
                deadline_groups[date_key]["todos"].append(todo)
            except Exception as e:
                logger.warning(f"日期解析失败: {deadline}, {e}")
    
    # 2. 检测工作量超载 (同一天 > 2个任务 或 > 6小时)
    DEFAULT_HOURS_PER_TASK = 2  # 默认每个任务2小时
    MAX_DAILY_HOURS = 8
    
    for date_key, group in deadline_groups.items():
        todos = group["todos"]
        weekday = group["weekday"]
        
        # 计算该日总工时
        total_hours = sum(
            t.get("estimated_hours", DEFAULT_HOURS_PER_TASK) 
            for t in todos
        )
        
        # 检查是否是被屏蔽的星期
        if weekday in blocked_weekdays:
            conflicts.append({
                "type": "blocked_day",
                "date": date_key,
                "weekday": weekday,
                "tasks": [t.get("title") for t in todos],
                "description": f"⚠️ {date_key} (周{['一','二','三','四','五','六','日'][weekday-1]}) 您不可用，但有 {len(todos)} 个任务截止",
                "suggestion": f"建议将任务调整到其他日期"
            })
        elif total_hours > MAX_DAILY_HOURS:
            conflicts.append({
                "type": "workload_overflow",
                "date": date_key,
                "total_hours": total_hours,
                "available_hours": MAX_DAILY_HOURS,
                "tasks": [t.get("title") for t in todos],
                "description": f"📅 {date_key} 任务过载: 预计需要 {total_hours}h，可用 {MAX_DAILY_HOURS}h",
                "suggestion": "建议延后部分低优先级任务"
            })
        elif len(todos) > 2:
            conflicts.append({
                "type": "time_overload",
                "date": date_key,
                "count": len(todos),
                "tasks": [t.get("title") for t in todos],
                "description": f"{date_key} 有 {len(todos)} 个任务需要完成，时间可能紧张"
            })
    
    # 3. 优先级冲突 (多个高优先级)
    high_priority_count = sum(1 for t in draft_todos if t.get("priority") == 1)
    if high_priority_count > 3:
        conflicts.append({
            "type": "priority_overload",
            "count": high_priority_count,
            "description": f"有 {high_priority_count} 个高优先级任务，建议重新评估优先级"
        })
    
    if conflicts:
        # 合并到已有冲突列表 (避免重复)
        existing_conflicts = state.get("detected_conflicts") or []
        existing_descs = {c["description"] for c in existing_conflicts}
        
        for c in conflicts:
            if c["description"] not in existing_descs:
                existing_conflicts.append(c)
        
        state["detected_conflicts"] = existing_conflicts
        
        # 生成冲突提示消息
        conflict_text = "⚠️ **检测到以下潜在冲突**:\n\n"
        for i, c in enumerate(existing_conflicts, 1):
            conflict_text += f"{i}. {c['description']}\n"
            if c.get("suggestion"):
                conflict_text += f"   💡 {c['suggestion']}\n"
        conflict_text += "\n是否需要调整任务安排?"
        
        state["messages"].append(AIMessage(content=conflict_text))
        logger.info(f"检测到 {len(conflicts)} 个新冲突, 总计 {len(existing_conflicts)} 个")
    
    return state


# ==================== 任务拆解节点 ====================

DECOMPOSE_PROMPT = """你是任务分解专家。

## 任务
识别复合任务并拆解为可执行子任务。

## 拆解规则

### 识别复合任务
**特征**:
- 包含"和"/"以及"等连接词
- 提到多个动作 (写、准备、提交)
- 明确列举子项

**示例**:
"技术方案里要写系统架构、信创适配、实施计划"
→ 复合任务,需拆解

### 拆解方法
1. 提取主任务标题
2. 识别所有子任务
3. 标记依赖关系
4. 评估工作量

## 输出格式
```json
{
  "is_complex": true,
  "main_task": "预售资金投标材料",
  "subtasks": [
    {
      "title": "技术方案 - 系统架构设计",
      "parent": "预售资金投标材料",
      "estimated_hours": 4,
      "dependencies": []
    },
    {
      "title": "技术方案 - 信创适配说明",
      "estimated_hours": 2,
      "dependencies": ["系统架构设计"]
    }
  ],
  "external_dependencies": [
    "等待公司部提supply商务方案"
  ]
}
```
"""

def task_decomposition_node(state: TodoAgentState) -> TodoAgentState:
    """任务拆解节点 - 自动拆分复合任务。"""
    logger.info("=== task_decomposition_node节点 ===")
    
    draft_todos = state.get("draft_todos", [])
    decomposed_todos = []
    
    for todo in draft_todos:
        if todo.get("is_complex"):
            # 调用LLM拆解
            llm = get_llm()
            decompose_messages = [
                SystemMessage(content=DECOMPOSE_PROMPT),
                HumanMessage(content=f"任务: {todo.get('title')}\n描述: {todo.get('description', '')}")
            ]
            
            # 初始化 Parser
            parser = JsonOutputParser(pydantic_object=DecompositionResult)

            try:
                # 🔧 添加 internal_thought tag，防止原始 JSON 被流式发送到前端
                response = llm.invoke(decompose_messages, config={"tags": ["internal_thought"]})
                
                # ✅ 使用标准 Parser 解析
                result = parser.parse(response.content)
                

                
                if result.get("subtasks"):
                    # 添加子任务
                    for subtask in result["subtasks"]:
                        decomposed_todos.append({
                            "title": subtask["title"],
                            "parent_task": result["main_task"],
                            "dependencies": subtask.get("dependencies", []),
                            "estimated_hours": subtask.get("estimated_hours"),
                            "priority": todo.get("priority", 2),
                            "due_date": todo.get("due_date")
                        })
                    
                    # 标记外部依赖
                    if result.get("external_dependencies"):
                        state["messages"].append(AIMessage(
                            content=f"📌 注意: {result['main_task']} 依赖于:\n" + 
                            "\n".join([f"- {dep}" for dep in result["external_dependencies"]])
                        ))
                    
                    logger.info(f"拆解任务: {result['main_task']} → {len(result['subtasks'])}个子任务")
                else:
                    decomposed_todos.append(todo)
            
            except Exception as e:
                logger.error(f"任务拆解失败: {e}")
                decomposed_todos.append(todo)
        else:
            decomposed_todos.append(todo)
    
    state["draft_todos"] = decomposed_todos
    return state


# ==================== 辅助函数 ====================

import json

def assess_clarity(message: str) -> float:
    """评估消息清晰度 (0-1)。"""
    # 简单规则
    if len(message) < 10:
        return 0.3
    
    vague_keywords = ["太多", "理一理", "整理", "有几个", "一些"]
    if any(kw in message for kw in vague_keywords):
        return 0.4
    
    specific_keywords = ["创建", "查看", "完成", "删除", "明天", "下周"]
    if any(kw in message for kw in specific_keywords):
        return 0.9
    
    return 0.6


def detect_time_conflicts(todos: List[Dict], constraints: Dict) -> List[Dict]:
    """检测时间冲突。"""
    conflicts = []
    
    # 按截止时间分组
    deadline_groups = {}
    for todo in todos:
        deadline = todo.get("due_date")
        if deadline:
            key = str(deadline).split("T")[0]  # 只取日期
            if key not in deadline_groups:
                deadline_groups[key] = []
            deadline_groups[key].append(todo)
    
    # 检测同一天多任务
    for date, tasks in deadline_groups.items():
        if len(tasks) >= 3:
            conflicts.append({
                "type": "同一天多任务",
                "date": date,
                "count": len(tasks),
                "tasks": [t["title"] for t in tasks]
            })
    
    return conflicts
