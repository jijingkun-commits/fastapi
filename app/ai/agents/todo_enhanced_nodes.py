"""待办Agent增强节点 - 多轮对话能力扩展。

新增节点:
- clarify_node: 澄清追问（LLM驱动版本）
- conflict_detection_node: 冲突检测  
- task_decomposition_node: 任务拆解

设计原则 (LangGraph Best Practices):
1. 所有节点函数返回 Dict 而非直接修改 state
2. 使用配置类管理硬编码值
3. 细化错误处理
4. LLM驱动：clarify_node 直接使用 analyze_intent 生成的 response_message
"""
import json
import logging
from typing import Dict, List, Optional
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from app.ai.utils.message_factory import create_ai_message, create_human_message
from langchain_core.runnables.config import RunnableConfig

from app.ai.llm_util import get_scene_llm, _normalize_text_content
from app.ai.scene_registry import SCENE_KEY_TODO_TASK_DECOMPOSITION
from app.ai.state import TodoAgentState
from app.ai.config.todo_config import get_todo_config

# 导入自定义事件工具
from langgraph.config import get_stream_writer
from app.ai.events import emit_clarification, emit_token, emit_status

logger = logging.getLogger(__name__)

# 获取配置实例
config = get_todo_config()

from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

# ==================== Pydantic 响应模型 ====================

# 注意：ClarificationResult 已移除，clarify_node 现在直接使用 LLM 生成的 response_message

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

def clarify_node(state: TodoAgentState) -> Dict:
    """澄清节点 - LLM驱动版本。
    
    直接使用 analyze_intent 阶段 LLM 生成的 response_message，
    不再内部重新调用 LLM 或自行生成消息。
    
    核心逻辑:
    1. 优先使用 state.response_message（LLM 已生成的回复）
    2. 仅在 response_message 为空时使用兜底消息
    3. 保留多项目追问模式（逐项目循环）
    
    Returns:
        Dict: 需要更新的状态字段（LangGraph 推荐方式）
    """
    logger.info("=== clarify_node节点 (LLM驱动版) ===")
    
    updates: Dict = {}
    
    # 检查上一条消息是否是 AI 回复，避免重复
    if state.get("messages") and isinstance(state["messages"][-1], AIMessage):
        logger.info("上一条消息是 AI 回复，跳过澄清生成")
        return updates
    
    # 获取 StreamWriter 用于发送自定义事件
    try:
        writer = get_stream_writer()
    except Exception:
        writer = lambda x: None
    
    # 多项目追问模式（逐项目循环）
    project_queue = state.get("project_queue", [])
    current_idx = state.get("current_project_index", 0)
    
    if project_queue and current_idx < len(project_queue):
        current_project = project_queue[current_idx]
        remaining = len(project_queue) - current_idx
        
        lines = [f"关于 **{current_project}** (还有 {remaining} 个项目待讨论)：", ""]
        lines.append("请告诉我：")
        lines.append("1. 这个项目的主要任务是什么？")
        lines.append("2. 截止时间是什么时候？")
        lines.append("3. 您负责哪些部分？")
        lines.append("")
        lines.append("*回复后我会继续询问下一个项目*")
        
        clarify_text = "\n".join(lines)
        updates["messages"] = [create_ai_message(clarify_text)]
        
        emit_clarification(writer, 
                          questions=["1. 这个项目的主要任务是什么？", "2. 截止时间是什么时候？", "3. 您负责哪些部分？"],
                          message=clarify_text,
                          node="clarify_node")
        
        updates["current_project_index"] = current_idx + 1
        updates["current_focus"] = current_project
        logger.info(f"逐项目追问: {current_project} ({current_idx + 1}/{len(project_queue)})")
        return updates
    
    # LLM驱动：直接使用 analyze_intent 生成的 response_message
    response_message = state.get("response_message")
    
    if response_message and response_message.strip():
        # 使用 LLM 生成的回复消息
        updates["messages"] = [create_ai_message(response_message)]
        
        # 发送澄清事件
        pending_clarifications = state.get("pending_clarifications", [])
        emit_clarification(writer,
                          questions=pending_clarifications,
                          message=response_message,
                          node="clarify_node")
        
        logger.info(f"使用 LLM 生成的 response_message: {response_message[:50]}...")
    else:
        # 兜底：response_message 为空时，优先使用上下文生成追问
        pending_op = state.get("pending_operation") or {}
        op_data = pending_op.get("data") or {}
        pending_questions = state.get("pending_clarifications") or []

        action = pending_op.get("action")
        target_title = (
            op_data.get("resolved_title")
            or op_data.get("title")
            or op_data.get("target_ref")
            or op_data.get("keyword")
            or "该待办"
        )

        if action in ("update", "complete", "delete"):
            if pending_questions:
                fallback_msg = (
                    f"我正在帮您处理 **{target_title}**。"
                    f"还需要您补充：{'; '.join(pending_questions)}。"
                )
            else:
                fallback_msg = (
                    f"我正在处理 **{target_title}**，"
                    "请告诉我您想执行的动作：修改、完成，还是删除？"
                )
        elif pending_questions:
            fallback_msg = f"为了继续处理，请补充：{'; '.join(pending_questions)}。"
        else:
            fallback_msg = "请告诉我您需要完成什么任务？包括具体内容和时间安排。"

        updates["messages"] = [create_ai_message(fallback_msg)]
        
        emit_clarification(writer,
                          questions=pending_questions,
                          message=fallback_msg,
                          node="clarify_node")
        
        logger.warning("response_message 为空，使用兜底消息")
    
    return updates


# ==================== 冲突检测节点 ====================

def conflict_detection_node(state: TodoAgentState) -> Dict:
    """冲突检测节点 - 检测时间/优先级/工作量冲突。
    
    Phase 2 增强：
    1. 使用 blocked_weekdays 检测不可用日期冲突
    2. 基于工时估算检测工作量超载
    3. 生成调整建议
    
    Returns:
        Dict: 需要更新的状态字段
    """
    logger.info("=== conflict_detection_node节点 ===")
    
    # 初始化更新字典
    updates: Dict = {}
    
    draft_todos = state.get("draft_todos", [])
    time_constraints = state.get("time_constraints", {})
    conflicts = []
    
    if not draft_todos:
        return updates
    
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
            except ValueError as e:
                logger.warning(f"日期格式错误: {deadline}, {e}")
            except Exception as e:
                logger.error(f"日期解析意外错误: {deadline}, {e}")
    
    # 2. 检测工作量超载 (使用配置)
    default_hours = config.default_hours_per_task
    max_hours = config.max_daily_hours
    
    for date_key, group in deadline_groups.items():
        todos = group["todos"]
        weekday = group["weekday"]
        
        # 计算该日总工时
        total_hours = sum(
            t.get("estimated_hours", default_hours) 
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
        elif total_hours > max_hours:
            conflicts.append({
                "type": "workload_overflow",
                "date": date_key,
                "total_hours": total_hours,
                "available_hours": max_hours,
                "tasks": [t.get("title") for t in todos],
                "description": f"📅 {date_key} 任务过载: 预计需要 {total_hours}h，可用 {max_hours}h",
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
        existing_conflicts = list(state.get("detected_conflicts") or [])
        existing_descs = {c["description"] for c in existing_conflicts}
        
        for c in conflicts:
            if c["description"] not in existing_descs:
                existing_conflicts.append(c)
        
        updates["detected_conflicts"] = existing_conflicts
        
        # 生成冲突提示消息
        conflict_text = "⚠️ **检测到以下潜在冲突**:\n\n"
        for i, c in enumerate(existing_conflicts, 1):
            conflict_text += f"{i}. {c['description']}\n"
            if c.get("suggestion"):
                conflict_text += f"   💡 {c['suggestion']}\n"
        conflict_text += "\n是否需要调整任务安排?"
        
        updates["messages"] = [create_ai_message(conflict_text)]
        logger.info(f"检测到 {len(conflicts)} 个新冲突, 总计 {len(existing_conflicts)} 个")
    
    return updates


# ==================== 任务拆解节点 ====================

from app.ai.prompts.todo_prompts import TODO_DECOMPOSE_PROMPT

def task_decomposition_node(state: TodoAgentState) -> Dict:
    """任务拆解节点 - 自动拆分复合任务。
    
    Returns:
        Dict: 需要更新的状态字段
    """
    logger.info("=== task_decomposition_node节点 ===")
    
    # 初始化更新字典
    updates: Dict = {}
    
    draft_todos = state.get("draft_todos", [])
    if not draft_todos:
        return updates
        
    decomposed_todos = []
    messages_to_add = []
    
    for todo in draft_todos:
        if todo.get("is_complex"):
            # 调用 LLM 拆解（internal=True 自动禁用流式 + 添加 tag）
            llm = get_scene_llm(
                scene_key=SCENE_KEY_TODO_TASK_DECOMPOSITION,
                internal=True,
            )
            decompose_messages = [
                SystemMessage(content=TODO_DECOMPOSE_PROMPT),
                create_human_message(f"任务: {todo.get('title')}\n描述: {todo.get('description', '')}")
            ]
            
            # 初始化 Parser
            parser = JsonOutputParser(pydantic_object=DecompositionResult)

            try:
                response = llm.invoke(decompose_messages)  # internal=True 自动添加 tag
                normalized_content = _normalize_text_content(
                    response.content if hasattr(response, "content") else response
                )
                
                # 使用标准 Parser 解析
                result = parser.parse(normalized_content)
                
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
                        messages_to_add.append(create_ai_message(
                            f"📌 注意: {result['main_task']} 依赖于:\n" + 
                            "\n".join([f"- {dep}" for dep in result["external_dependencies"]])
                        ))
                    
                    logger.info(f"拆解任务: {result['main_task']} → {len(result['subtasks'])}个子任务")
                else:
                    decomposed_todos.append(todo)
            
            except json.JSONDecodeError as e:
                logger.warning(f"任务拆解 JSON 解析失败: {e}")
                decomposed_todos.append(todo)
            except Exception as e:
                logger.error(f"任务拆解意外错误: {e}")
                decomposed_todos.append(todo)
        else:
            decomposed_todos.append(todo)
    
    updates["draft_todos"] = decomposed_todos
    if messages_to_add:
        updates["messages"] = messages_to_add
    
    return updates


# ==================== 辅助函数 ====================

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
