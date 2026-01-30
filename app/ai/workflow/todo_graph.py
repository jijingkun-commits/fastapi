"""LangGraph 待办 Agent - 多轮对话增强版（中文注释）。

支持:
- 主动澄清追问
- 任务拆解
- 冲突检测
- 优先级动态调整

设计原则 (LangGraph Best Practices):
1. 所有节点函数返回 Dict 而非直接修改 state
2. 使用配置类管理硬编码值
3. 使用 interrupt() + Command 模式处理人机交互
"""
import logging
import json
from typing import TypedDict, Optional, Dict, List, Annotated, Literal, Union
from datetime import datetime

from langchain_core.messages import BaseMessage, AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables.config import RunnableConfig
from langgraph.graph import StateGraph, END
from langgraph.types import interrupt
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver

from app.ai.llm_util import get_llm
from app.db.session import get_db_context  # 数据库上下文管理器
from app.repositories.todo_repository import TodoRepository  # 待办仓库
from app.core.types import ToolResult, ToolResultBuilder  # 统一类型
from app.ai.config.todo_config import get_todo_config, get_todo_dependencies  # 配置类和依赖注入
from app.ai.exceptions import (
    LLMParseError,
    LLMInvocationError,
    DatabaseError,
    EntityNotFoundError,
    MissingRequiredFieldError,
)

# 导入自定义事件工具
from langgraph.config import get_stream_writer
from app.ai.events import emit_clarification, emit_token, emit_status, emit_error, emit_result

# 导入统一的状态辅助函数
from app.ai.utils.state_helpers import get_user_id, get_user_id_optional

# 导入实体解析节点
from app.ai.agents.resolve_node import resolve_entity, route_after_resolve

# 导入意图分析辅助函数
from app.ai.workflow.todo_intent_helpers import (
    filter_messages_for_todo,
    query_existing_todos,
    parse_time_info,
    detect_urgent_task,
    process_clarify_intent,
    process_confirm_intent,
    determine_confirmation_need,
    check_rule_based_intent,
    extract_heuristic_title,
    get_progressive_strategy,
)

# 创建仓库实例
todo_repo = TodoRepository()

# 获取配置实例
todo_config = get_todo_config()


logger = logging.getLogger(__name__)


# ==================== 状态定义 ====================

class TodoAgentState(TypedDict):
    """待办 Agent 状态 - 简化版。"""
    messages: Annotated[List[BaseMessage], add_messages]
    user_id: Optional[int]
    thread_id: Optional[str]
    pending_operation: Optional[Dict]
    user_confirmed: Optional[bool]
    quick_mode: Optional[bool]
    
    # 对话管理
    conversation_context: Optional[Dict]
    current_focus: Optional[str]
    
    # 冲突检测
    detected_conflicts: Optional[List[Dict]]
    time_constraints: Optional[Dict]
    
    # 提取信息
    extracted_info: Optional[Dict]
    
    # 澄清追问
    pending_clarifications: Optional[List[str]]


# 注意：OperationResult 已废弃，统一使用 ToolResult (从 app.core.types 导入)


# ==================== 系统提示词 ====================

from app.ai.prompts.todo_prompts import (
    TODO_INTENT_ANALYZE_PROMPT,
)


# ==================== 辅助函数 ====================

# 注释: _needs_create_confirmation 函数已废弃
# 当前策略: 所有创建操作都需要确认(除非quick_mode)
# 如需恢复智能确认,可以取消注释以下代码

# def _needs_create_confirmation(extracted_info: Dict) -> bool:
#     """判断创建操作是否需要确认。
#     
#     规则:
#     - 如果标题明确 → 无需确认
#     - 如果标题缺失或模糊 → 需要确认
#     """
#     title = extracted_info.get("title", "").strip()
#     
#     # 标题为空或过短
#     if not title or len(title) < 2:
#         return True
#     
#     # 标题过于模糊
#     vague_keywords = ["这个", "那个", "它", "东西", "事情"]
#     if any(keyword in title for keyword in vague_keywords):
#         return True
#     
#     # 信息完整,无需确认
#     return False


from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

# ==================== Pydantic 响应模型 (P1-4) ====================

class IntentResult(BaseModel):
    """LLM 意图分析结果模型"""
    intent: str = Field(description="用户意图: create, update, delete, query, confirm, clarify 等")
    extracted_info: Dict = Field(default={}, description="提取的实体信息: title, time, due_date, priority 等")
    missing_info: List[str] = Field(default=[], description="缺失的关键信息")
    is_complex: bool = Field(default=False, description="是否为复杂任务")
    conflict_risk: str = Field(default="none", description="冲突风险: high, medium, none")
    context_hints: Dict = Field(default={}, description="上下文线索")
    projects: List[str] = Field(default=[], description="涉及的项目列表")
    time_constraints: Dict = Field(default={}, description="时间约束")


# ==================== 节点函数 ====================

def _get_user_id_from_state(state: TodoAgentState) -> Optional[int]:
    """从 State 中获取用户 ID (统一入口)"""
    return get_user_id_optional(state, config=None)


def _get_user_todo_context(user_id: int, config: dict = None) -> str:
    """获取用户现有待办上下文字符串。
    
    Args:
        user_id: 用户 ID
        config: LangGraph 运行配置（用于依赖注入）
    """
    if not user_id:
        return ""
    
    # 使用依赖注入
    deps = get_todo_dependencies(config)
        
    try:
        with deps.get_db_context() as db:
            repo = deps.get_repository()
            existing_todos = repo.list_by_user(db, user_id, status="pending")
            if not existing_todos:
                return ""
                
            # 构建简洁的任务列表上下文
            limit = todo_config.context_todos_limit
            # 数字到中文优先级映射
            priority_num_to_cn = {1: "高", 2: "中", 3: "低"}
            todo_list = []
            for t in existing_todos[:limit]:
                due_str = t.due_date.strftime("%m月%d日") if t.due_date else "无截止"
                priority_str = priority_num_to_cn.get(t.priority, "中")
                todo_list.append(f"- {t.title} (截止:{due_str}, 优先级:{priority_str})")
            
            context = f"\n\n## 用户现有待办 ({len(existing_todos)}项)\n" + "\n".join(todo_list)
            logger.info(f"加载用户现有待办: {len(existing_todos)} 项")
            return context
    except Exception as e:
        logger.warning(f"查询历史任务失败: {e}")
        return ""


def _check_duplicate_todos(user_id: int, new_title: str, threshold: float = None, config: dict = None) -> List[Dict]:
    """检查是否存在相似的待办任务（重复检测）。
    
    Args:
        user_id: 用户 ID
        new_title: 新任务标题
        threshold: 相似度阈值 (0-1)，默认使用配置值
        config: LangGraph 运行配置（用于依赖注入）
        
    Returns:
        相似任务列表 [{"id": int, "title": str, "similarity": float}, ...]
    """
    if threshold is None:
        threshold = todo_config.duplicate_threshold
        
    if not user_id or not new_title:
        logger.warning(f"重复检测跳过: user_id={user_id}, new_title={new_title}")
        return []

    logger.info(f"Start _check_duplicate_todos: user_id={user_id}, title={new_title}")
    
    # 使用依赖注入获取仓库和数据库上下文
    deps = get_todo_dependencies(config)
    
    try:
        with deps.get_db_context() as db:
            # 获取用户未完成的待办 (使用配置的 limit)
            repo = deps.get_repository()
            existing_todos = repo.list_by_user(db, user_id, status="pending", limit=todo_config.max_todos_per_query)
            logger.info(f"重复检测: 获取到 {len(existing_todos)} 个现有待办 (Limit=200)")
            
            if not existing_todos:
                return []
            
            duplicates = []
            new_title_lower = new_title.lower().strip()
            
            for todo in existing_todos:
                existing_title = todo.title.lower().strip() if todo.title else ""
                
                # 计算相似度（简单的关键词匹配方法）
                similarity = _calculate_title_similarity(new_title_lower, existing_title)
                
                if similarity >= threshold:
                    logger.info(f"发现相似: '{existing_title}' score={similarity}")
                    duplicates.append({
                        "id": todo.id,
                        "title": todo.title,
                        "similarity": round(similarity, 2),
                        "status": todo.status,
                        "due_date": todo.due_date.strftime("%m-%d") if todo.due_date else None
                    })
            
            # 按相似度降序排列
            duplicates.sort(key=lambda x: x["similarity"], reverse=True)
            
            if duplicates:
                logger.info(f"检测到 {len(duplicates)} 个相似任务: {[d['title'] for d in duplicates[:3]]}")
            
            return duplicates[:todo_config.duplicate_max_results]
    except Exception as e:
        logger.warning(f"重复检测失败: {e}")
        return []


def _calculate_title_similarity(new_title: str, existing_title: str) -> float:
    """计算两个标题的相似度（基于关键词重叠）。
    
    使用 Jaccard 相似度计算。
    """
    if not new_title or not existing_title:
        return 0.0
    
    # 完全匹配
    if new_title == existing_title:
        return 1.0
    
    # 包含关系
    if new_title in existing_title or existing_title in new_title:
        return 0.9
    
    # Jaccard 相似度（基于字符 n-gram）
    def get_ngrams(text: str, n: int = 2) -> set:
        return set(text[i:i+n] for i in range(len(text) - n + 1))
    
    ngrams_new = get_ngrams(new_title)
    ngrams_existing = get_ngrams(existing_title)
    
    if not ngrams_new or not ngrams_existing:
        return 0.0
    
    intersection = len(ngrams_new & ngrams_existing)
    union = len(ngrams_new | ngrams_existing)
    
    return intersection / union if union > 0 else 0.0


# ==================== LLM 调用辅助函数 ====================

def _invoke_llm_for_intent(
    recent_messages: List[BaseMessage],
    system_prompt: str,
    heuristic_title: Optional[str] = None,
    pre_extracted_info: Optional[Dict] = None
) -> Dict:
    """调用 LLM 分析用户意图并解析响应。
    
    职责：
    1. 调用 LLM 分析消息
    2. 解析 JSON 响应
    3. 应用启发式标题修正
    4. 合并预提取信息
    
    Args:
        recent_messages: 最近的消息列表
        system_prompt: 系统提示词（应已包含 format_instructions）
        heuristic_title: 启发式提取的标题（可选）
        pre_extracted_info: Handoff 预提取的信息（可选）
        
    Returns:
        Dict: 包含 intent 和 extracted_info 的分析结果
        
    Note:
        此函数可用于替代 analyze_intent 中的 LLM 调用部分。
        未来重构时可以这样使用：
        
        >>> analysis = _invoke_llm_for_intent(recent_messages, system_prompt, ...)
        >>> intent = analysis["intent"]
        >>> extracted_info = analysis["extracted_info"]
    """
    llm = get_llm(enable_streaming=False)
    parser = JsonOutputParser(pydantic_object=IntentResult)
    
    analysis_messages = [SystemMessage(content=system_prompt)]
    analysis_messages.extend(recent_messages)
    
    response = llm.invoke(analysis_messages, config={"tags": ["internal_thought"]})
    result_text = response.content
    logger.info(f"LLM 分析结果长度: {len(result_text)}")
    
    # 解析 JSON 响应
    try:
        analysis_dict = parser.parse(result_text)
    except json.JSONDecodeError as e:
        logger.warning(f"JSON 解析失败，尝试清理: {e}")
        # 简单的 markdown json 清理
        clean_text = result_text.replace("```json", "").replace("```", "").strip()
        start = clean_text.find("{")
        end = clean_text.rfind("}")
        if start != -1 and end != -1:
            clean_text = clean_text[start:end+1]
            try:
                analysis_dict = json.loads(clean_text)
            except json.JSONDecodeError:
                logger.warning("JSON 清理后仍无法解析，使用默认意图")
                analysis_dict = {"intent": "clarify", "extracted_info": {}}
        else:
            analysis_dict = {"intent": "clarify", "extracted_info": {}}
    except Exception as e:
        logger.warning(f"解析意外错误: {e}，使用默认意图")
        analysis_dict = {"intent": "clarify", "extracted_info": {}}
    
    intent = analysis_dict.get("intent", "chat")
    if isinstance(intent, str):
        intent = intent.strip()
        
    extracted_info = analysis_dict.get("extracted_info", {})
    
    # 应用启发式标题修正
    if heuristic_title and not extracted_info.get("title"):
        logger.info(f"LLM 未提取标题，使用 heuristic_title: {heuristic_title}")
        extracted_info["title"] = heuristic_title
        
        # 如果 intent 是 clarify，修正为 create
        if intent == "clarify":
            intent = "create"
            logger.info("根据 heuristic title 将 intent 修正为 create")
    
    logger.info(f"LLM 分析结果: intent='{intent}', extracted_info={extracted_info}")
    
    # 合并 Handoff 预提取的信息（优先级高于 LLM 分析结果）
    if pre_extracted_info:
        for key, value in pre_extracted_info.items():
            if value and not extracted_info.get(key):
                extracted_info[key] = value
                logger.info(f"使用 Handoff 预提取的 {key}: {value}")
    
    # 保留原始分析结果中的其他字段
    return {
        "intent": intent,
        "extracted_info": extracted_info,
        "conflict_risk": analysis_dict.get("conflict_risk", "none"),
        "conflicts": analysis_dict.get("conflicts", []),
        "quick_mode": analysis_dict.get("quick_mode", False),
    }


def _dispatch_intent(
    intent: str,
    extracted_info: Dict,
    analysis: Dict,
    state: TodoAgentState,
    user_id: Optional[int],
    updates: Dict
) -> Optional[Dict]:
    """根据意图分发到对应的处理逻辑。
    
    Args:
        intent: 识别的意图
        extracted_info: 提取的信息
        analysis: LLM 分析结果
        state: 当前状态
        user_id: 用户 ID
        updates: 当前更新字典
        
    Returns:
        Optional[Dict]: 如果需要提前返回则返回更新字典，否则返回 None
    """
    logger.info(f"Processing dispatch with intent='{intent}'")
    
    # 1. clarify 意图
    if intent == "clarify":
        logger.info("Entering clarify intent block")
        # 如果在 clarify 意图中也发现了标题，尝试进行重复检测
        if extracted_info.get("title"):
            logger.info(f"Clarify Intent: Preparing to check duplicates for title='{extracted_info.get('title')}'")
            duplicates = _check_duplicate_todos(user_id, extracted_info.get("title"))
            if duplicates:
                updates["duplicate_candidates"] = duplicates
                updates["pending_operation"] = {
                    "action": "create",
                    "data": extracted_info,
                    "needs_clarification": True,
                    "duplicate_warning": True
                }
                updates["extracted_info"] = extracted_info
                logger.info(f"在澄清意图中发现 {len(duplicates)} 个相似任务，需用户确认")
                return updates

        result = process_clarify_intent(analysis, extracted_info)
        updates.update(result.to_dict())
        return updates
    
    # 2. confirm 意图
    if intent == "confirm":
        result = process_confirm_intent(state.get("pending_operation"), extracted_info)
        updates.update(result.to_dict())
        return updates
    
    # 3. 用户补充信息场景
    pending_op = state.get("pending_operation")
    if pending_op and pending_op.get("needs_clarification") and extracted_info:
        existing_data = dict(pending_op.get("data", {}))
        for key, value in extracted_info.items():
            if value:
                existing_data[key] = value
        updated_op = dict(pending_op)
        updated_op["data"] = existing_data
        updates["pending_operation"] = updated_op
        return updates
    
    # 4. 冲突风险标记
    conflict_risk = analysis.get("conflict_risk", "none")
    if conflict_risk != "none":
        updates["detected_conflicts"] = analysis.get("conflicts", [])
    
    # 5. 重复检测 (Duplicate Detection for create intent)
    if intent == "create" and extracted_info.get("title"):
        duplicates = _check_duplicate_todos(user_id, extracted_info.get("title"))
        if duplicates:
            updates["duplicate_candidates"] = duplicates
            updates["pending_operation"] = {
                "action": "create",
                "data": extracted_info,
                "needs_clarification": True,
                "duplicate_warning": True
            }
            updates["extracted_info"] = extracted_info
            logger.info(f"发现 {len(duplicates)} 个相似任务，需用户确认是否仍需创建")
            return updates
    
    # 不需要提前返回
    return None


def analyze_intent(state: TodoAgentState) -> Dict:
    """分析用户意图节点（重构版）。
    
    使用辅助函数拆分逻辑，返回增量更新字典而非直接修改 state。
    
    职责：
    1. 调用 LLM 分析最后一条用户消息
    2. 判断是否需要确认
    3. 提取待办相关信息
    """
    logger.info("=== analyze_intent 节点 ===")
    
    # 收集需要更新的字段
    updates: Dict = {}
    
    messages = state.get("messages", [])
    
    # Step 1: 消息过滤与 Handoff 上下文构建
    pending_handoff = state.get("pending_handoff")
    filtered_messages, handoff_context, pre_extracted_info = filter_messages_for_todo(messages, pending_handoff)
    recent_messages = filtered_messages[-5:] if filtered_messages else []
    
    logger.info(f"分析用户消息 (Original: {len(messages)}, Filtered: {len(filtered_messages)}, Use: {len(recent_messages)})")
    if pre_extracted_info:
        logger.info(f"Handoff 预提取信息: {pre_extracted_info}")
    
    # Step 2: 历史任务查询 (通过 Helper)
    user_id = _get_user_id_from_state(state)
    existing_todos_context = ""
    if user_id:
        existing_todos_context = query_existing_todos(user_id)
    
    # 清理上一轮的临时状态
    if state.get("pending_clarifications"):
        updates["pending_clarifications"] = []
    if state.get("detected_conflicts"):
        updates["detected_conflicts"] = []
    
    # Step 3: 调用 LLM 分析
    llm = get_llm(enable_streaming=False)
    
    # 构建 Parser
    parser = JsonOutputParser(pydantic_object=IntentResult)
    format_instructions = parser.get_format_instructions()
    
    # Step 4: 渐进式策略注入 (Progressive Prompting)
    progressive_injection = ""
    round_count = len(messages) // 2  # 每轮两条消息 (human + ai)
    user_confirmed = state.get("user_confirmed", False)
    
    # 获取最后一条用户消息
    last_human_msg = ""
    for msg in reversed(messages):
        if hasattr(msg, 'type') and msg.type == 'human':
            last_human_msg = msg.content if hasattr(msg, 'content') else str(msg)
            break
            
    # 启发式标题提取（备用方案）
    heuristic_title = extract_heuristic_title(last_human_msg) if last_human_msg else None

    # 规则化意图检测（在调用 LLM 之前进行快速匹配）
    pending_op = state.get("pending_operation")
    rule_result = check_rule_based_intent(last_human_msg, pending_op)
    if rule_result and rule_result.should_return_early:
        updates.update(rule_result.to_dict())
        return updates
    
    # 快速模式检测
    quick_mode = state.get("quick_mode", False)
    if not quick_mode and todo_config.is_quick_mode(last_human_msg):
        quick_mode = True
        updates["quick_mode"] = True
        logger.info("检测到快速模式关键词，启用 quick_mode")
    
    # 根据轮数获取渐进式策略注入
    progressive_injection = get_progressive_strategy(round_count, user_confirmed, quick_mode)
    
    # 构建 Prompt
    system_prompt = f"{TODO_INTENT_ANALYZE_PROMPT}{progressive_injection}\n{handoff_context}\n{existing_todos_context}\n\n## 冲突检测提示\n如果用户新任务与现有任务在同一天或有潜在冲突，设置 `conflict_risk: 'high'`。\n\n{format_instructions}"
    
    analysis_messages = [SystemMessage(content=system_prompt)]
    analysis_messages.extend(recent_messages)
    
    try:
        response = llm.invoke(analysis_messages, config={"tags": ["internal_thought"]})
        result_text = response.content
        logger.info(f"LLM 分析结果长度: {len(result_text)}")
        
        try:
            analysis_dict = parser.parse(result_text)
        except json.JSONDecodeError as e:
            logger.warning(f"JSON 解析失败，尝试清理: {e}")
            # 简单的 markdown json 清理
            clean_text = result_text.replace("```json", "").replace("```", "").strip()
            start = clean_text.find("{")
            end = clean_text.rfind("}")
            if start != -1 and end != -1:
                clean_text = clean_text[start:end+1]
                try:
                    analysis_dict = json.loads(clean_text)
                except json.JSONDecodeError:
                    # 无法恢复，使用默认值
                    logger.warning("JSON 清理后仍无法解析，使用默认意图")
                    analysis_dict = {"intent": "clarify", "extracted_info": {}}
            else:
                analysis_dict = {"intent": "clarify", "extracted_info": {}}
        except Exception as e:
            logger.warning(f"解析意外错误: {e}，使用默认意图")
            analysis_dict = {"intent": "clarify", "extracted_info": {}}
        
        analysis = analysis_dict

        intent = analysis.get("intent", "chat")
        if isinstance(intent, str):
            intent = intent.strip()
            
        extracted_info = analysis.get("extracted_info", {})
        
        # Heuristic: 使用启发式提取的标题
        if heuristic_title and not extracted_info.get("title"):
             logger.info(f"LLM 未提取标题，使用 heuristic_title: {heuristic_title}")
             extracted_info["title"] = heuristic_title
             
             # 如果 intent 是 clarify，修正为 create
             if intent == "clarify":
                 intent = "create"
                 logger.info(f"根据 heuristic title 将 intent 修正为 create")
        
        logger.info(f"LLM 分析结果: intent='{intent}', extracted_info={extracted_info}")
        
        # 合并 Handoff 预提取的信息（优先级高于 LLM 分析结果）
        if pre_extracted_info:
            for key, value in pre_extracted_info.items():
                if value and not extracted_info.get(key):
                    extracted_info[key] = value
                    logger.info(f"使用 Handoff 预提取的 {key}: {value}")
        
        
        # Step 4: 时间解析
        extracted_info, time_constraints = parse_time_info(
            extracted_info, 
            state.get("time_constraints")
        )
        if time_constraints:
            updates["time_constraints"] = time_constraints
        
        # Step 5: 紧急任务检测
        extracted_info = detect_urgent_task(messages, intent, extracted_info, user_id)
        
        # Step 6: 意图分支处理
        logger.info(f"Processing Step 6 with intent='{intent}'")
        print(f"DEBUG: Processing Step 6 with intent='{intent}', extracted_info={extracted_info}")
        
        # 6.1 clarify 意图
        if intent == "clarify":
            logger.info("Entering clarify intent block")
            # 如果在 clarify 意图中也发现了标题，尝试进行重复检测
            if extracted_info.get("title"):
                 logger.info(f"Clarify Intent: Preparing to check duplicates for title='{extracted_info.get('title')}'")
                 duplicates = _check_duplicate_todos(user_id, extracted_info.get("title"))
                 if duplicates:
                    updates["duplicate_candidates"] = duplicates
                    updates["pending_operation"] = {
                        "action": "create",
                        "data": extracted_info,
                        "needs_clarification": True,
                        "duplicate_warning": True
                    }
                    updates["extracted_info"] = extracted_info
                    logger.info(f"在澄清意图中发现 {len(duplicates)} 个相似任务，需用户确认")
                    return updates

            result = process_clarify_intent(analysis, extracted_info)
            updates.update(result.to_dict())
            return updates
        
        # 6.2 confirm 意图
        if intent == "confirm":
            result = process_confirm_intent(state.get("pending_operation"), extracted_info)
            updates.update(result.to_dict())
            return updates
        
        # 6.3 用户补充信息场景
        pending_op = state.get("pending_operation")
        if pending_op and pending_op.get("needs_clarification") and extracted_info:
            existing_data = pending_op.get("data", {})
            for key, value in extracted_info.items():
                if value:
                    existing_data[key] = value
            pending_op["data"] = existing_data
            updates["pending_operation"] = pending_op
            return updates
        

        
        # Step 7: 冲突风险标记
        conflict_risk = analysis.get("conflict_risk", "none")
        if conflict_risk != "none":
            updates["detected_conflicts"] = analysis.get("conflicts", [])
        
        # Step 7.5: 重复检测 (Duplicate Detection for create intent)
        if intent == "create" and extracted_info.get("title"):
            duplicates = _check_duplicate_todos(user_id, extracted_info.get("title"))
            if duplicates:
                # 发现相似任务，需要用户确认
                updates["duplicate_candidates"] = duplicates
                updates["pending_operation"] = {
                    "action": "create",
                    "data": extracted_info,
                    "needs_clarification": True,
                    "duplicate_warning": True
                }
                updates["extracted_info"] = extracted_info
                logger.info(f"发现 {len(duplicates)} 个相似任务，需用户确认是否仍需创建")
                return updates
        
        # Step 8: 读取 quick_mode 并确定是否需要确认
        # quick_mode 可能来自 LLM 分析或 state
        quick_mode = analysis.get("quick_mode", False) or state.get("quick_mode", False)
        if quick_mode:
            updates["quick_mode"] = True
            logger.info("检测到快速创建模式")
        
        needs_confirmation, needs_clarification = determine_confirmation_need(intent, quick_mode, extracted_info)
        
        if needs_confirmation:
            updates["pending_operation"] = {
                "action": intent,
                "data": extracted_info,
                "needs_clarification": needs_clarification
            }
            updates["extracted_info"] = extracted_info
            logger.info(f"需要确认: {intent}, 需要先澄清: {needs_clarification}")
        else:
            updates["pending_operation"] = {
                "action": intent,
                "data": extracted_info,
                "skip_confirmation": True
            }
            updates["extracted_info"] = extracted_info
            logger.info(f"直接执行: {intent}")
            
    except json.JSONDecodeError as e:
        # JSON 解析错误（可恢复）
        logger.warning(f"意图分析 JSON 解析失败: {e}")
        updates["pending_clarifications"] = ["请告诉我您想要完成什么任务？"]
        updates["messages"] = [AIMessage(content="我没有完全理解您的意思，请告诉我具体需要完成什么任务？")]
    except (ConnectionError, TimeoutError) as e:
        # 网络/超时错误
        logger.error(f"意图分析网络错误: {e}")
        updates["messages"] = [AIMessage(content="网络连接出现问题，请稍后重试。")]
    except Exception as e:
        # 其他意外错误
        logger.exception(f"意图分析意外错误: {e}")
        updates["pending_operation"] = None
        updates["messages"] = [AIMessage(content="抱歉，处理您的请求时出现了问题。请重新描述您的需求。")]
    
    return updates


def ask_confirmation(state: TodoAgentState) -> Dict:
    """请求用户确认节点。
    
    发送包含 Confirmation Card 的消息给用户。
    实际的等待中断在 wait_for_confirmation 节点处理。
    """
    logger.info("=== ask_confirmation 节点 ===")
    
    operation = state.get("pending_operation")
    if not operation:
        logger.warning("无待确认操作")
        return {}
    
    action = operation.get("action")
    # 优先使用 operation["data"]，而非 extracted_info
    # 因为 operation["data"] 是最新的、经过处理的数据
    data = operation.get("data", {})
    
    logger.info(f"待确认的操作数据: action={action}, data={data}")
    
    # 生成确认消息
    if action == "create":
        # 为所有字段提供默认值，避免显示空字符串
        title = data.get("title") or "新待办"
        time_str = data.get("time") or data.get("due_date") or ""
        priority = data.get("priority") or "中"
        category = data.get("category") or ""
        description = data.get("description") or ""
        
        # 如果标题看起来是空的或者只有默认值，尝试从描述或原始消息中提取
        if title == "新待办" and description:
            title = description[:50]  # 使用描述的前50个字符作为标题
        
        location = data.get("location") or ""
        
        confirm_msg = f"""好的，我帮你记录这个待办 📝

**{title}**
- 📅 时间：{time_str if time_str else '未设置'}
{f'- 📍 地点：{location}' if location else ''}
- ⭐ 优先级：{priority}
- 🏷️ 分类：{category if category else '未分类'}
{f'- 📄 待办内容：{description}' if description else ''}

要补充一些信息吗？比如：
1. 具体时间（几点）
2. 详细描述
3. 是否需要提醒

直接说"确认"即可创建，或"拒绝"告诉我补充内容～
"""
    
    elif action == "batch_complete":
        count = data.get("count", 0)
        confirm_msg = f"即将批量完成 {count} 个待办，确认吗？"
    
    elif action == "delete":
        # 优先使用 resolve 节点解析后的信息
        todo_id = data.get("todo_id")
        title = data.get("resolved_title") or data.get("title") or "待办"
        id_hint = f" (ID: {todo_id})" if todo_id else ""
        confirm_msg = f"确认删除 **{title}**{id_hint} 吗？"
    
    elif action == "update":
        # 优先使用 resolve 节点解析后的信息
        todo_id = data.get("todo_id")
        title = data.get("resolved_title") or data.get("title") or "待办"
        id_hint = f" (ID: {todo_id})" if todo_id else ""
        confirm_msg = f"确认更新 **{title}**{id_hint} 吗？"

    elif action == "merge":
        target_tasks = data.get("target_tasks", [])
        confirm_msg = f"确认合并以下任务吗？\n" + "\n".join([f"- {t}" for t in target_tasks])
    
    else:
        # 改进默认确认消息，显示数据概要
        data_summary = ", ".join([f"{k}: {v}" for k, v in data.items() if v])[:100]
        confirm_msg = f"确认执行 {action} 操作吗？\n\n参数：{data_summary if data_summary else '(无)'}"
    
    # 生成客户能看懂的详细摘要（用于前端显示）
    friendly_summary = ""
    if action == "create":
        # 提取所有可能的字段
        title = data.get("title") or "新待办"
        time_str = data.get("time") or data.get("due_date") or ""
        priority = data.get("priority") or "中"
        category = data.get("category") or ""
        description = data.get("description") or ""
        tags = data.get("tags") or []
        
        # 构建详细的多行摘要
        lines = [f"**创建待办**"]
        lines.append(f"📝 标题：{title}")
        if time_str:
            lines.append(f"⏰ 时间：{time_str}")
        lines.append(f"⭐ 优先级：{priority}")
        if category:
            lines.append(f"🏷️ 分类：{category}")
        if description:
            lines.append(f"📄 描述：{description}")
        if tags:
            lines.append(f"🔖 标签：{', '.join(tags) if isinstance(tags, list) else tags}")
        
        friendly_summary = "\n".join(lines)
        
    elif action == "update":
        title = data.get("title", "待办")
        lines = [f"**更新待办**", f"📝 标题：{title}"]
        
        # 显示所有要更新的字段
        if "time" in data or "due_date" in data:
            time_str = data.get("time") or data.get("due_date")
            lines.append(f"⏰ 新时间：{time_str}")
        if "priority" in data:
            lines.append(f"⭐ 新优先级：{data.get('priority')}")
        if "category" in data:
            lines.append(f"🏷️ 新分类：{data.get('category')}")
        if "status" in data:
            lines.append(f"📊 新状态：{data.get('status')}")
        
        friendly_summary = "\n".join(lines)
        
    elif action == "delete":
        title = data.get("title", "待办")
        friendly_summary = f"**删除待办**\n📝 标题：{title}"
        
    elif action == "batch_complete":
        count = data.get("count", 0)
        friendly_summary = f"**批量操作**\n✅ 完成 {count} 个待办"
        
    elif action == "merge":
        target_tasks = data.get("target_tasks", [])
        friendly_summary = f"**合并待办**\n🔗 将合并以下任务:\n" + "\n".join([f"- {t}" for t in target_tasks])

    else:
        friendly_summary = f"**执行操作**\n操作类型：{action}"
    
    # 构造前端期望的确认数据结构（与 CompactApproval 组件适配）
    # 将 data 字段复制并添加客户可读的显示消息
    display_args = {
        **data,
        "_display_message": friendly_summary  # 关键：前端优先显示此字段
    }
    
    confirmation_data = {
        "action_requests": [
            {
                "name": action,  # create / update / delete 等
                "args": display_args
            }
        ]
    }
    
    logger.info(f"请求用户确认: {action}, message_preview={confirm_msg[:50]}...")
    
    # 构造结构化 operation 对象用于前端渲染 ConfirmationCard
    operation_data = {
        "action": action, # 统一使用 action 字段
        "data": data,
        "summary": friendly_summary
    }
    
    # 对于更新操作，尝试构造 diff 数据
    if action == "update":
        todo_id = data.get("todo_id")
        resolved_title = data.get("resolved_title")
        
        # 填充 target_task
        if todo_id:
            operation_data["target_task"] = {
                "id": todo_id,
                "title": resolved_title or title
            }
        
        # 填充 diff
        # 注意：这里简化处理，实际 diff 需要从数据库获取原始值进行对比
        # 但在 route_next 或 resolve 阶段我们可能已经有了原始数据
        # 如果 state 中没有原始待办，这里只能显示新值
        diff = {}
        for key, value in data.items():
            if key in ["title", "priority", "due_date", "description", "category"] and value:
                # 假设旧值未知，前端会显示 "-> 新值"
                diff[key] = {"old": None, "new": value}
        operation_data["diff"] = diff
        
    elif action == "delete":
         todo_id = data.get("todo_id")
         if todo_id:
            operation_data["target_task"] = {
                "id": todo_id,
                "title": data.get("resolved_title") or data.get("title")
            }

    # 返回 AIMessage
    msg = AIMessage(
        content=confirm_msg,
        additional_kwargs={
            "operation": operation_data
        }
    )
    
    return {
        "messages": [msg],
        "pending_operation": operation_data, # 更新包含 summary 的完整信息
        "user_confirmed": None # 重置确认状态
    }


def wait_for_confirmation(state: TodoAgentState) -> Dict:
    """等待用户确认节点。
    
    接受前端 resume 的数据并更新状态。
    """
    logger.info("=== wait_for_confirmation 节点 ===")
    
    # 触发中断，等待用户回复
    # 前端 resume 时传递的数据将作为 interrupt 的返回值
    
    # 构造前端 CompactApproval 需要的数据格式
    pending_op = state.get("pending_operation") or {}
    
    # 确保有 summary，避免前端显示空
    if not pending_op.get("summary") and pending_op.get("data"):
         # 尝试从 data 生成简单的 summary
         data = pending_op["data"]
         summary_lines = ["**待确认操作**"]
         if data.get("title"): summary_lines.append(f"📝 标题: {data['title']}")
         if data.get("due_date"): summary_lines.append(f"⏰ 时间: {data['due_date']}")
         pending_op["summary"] = "\n".join(summary_lines)
    
    interrupt_value = {
        "action_requests": [{
            "name": pending_op.get("action", "unknown"),
            "args": {
                **pending_op.get("data", {}),
                "_display_message": pending_op.get("summary", "")
            }
        }]
    }
    
    decision = interrupt(interrupt_value)
    
    logger.info(f"收到用户决策 (resume): {decision}")
    
    # 如果 decision 为空（非预期情况，可能是上下文切换导致），保持等待状态或静默退出
    # 不要返回 False，否则会触发 execute_operation 的“已取消”消息
    if not decision:
        logger.warning("wait_for_confirmation 收到空决策，可能是非 Resume 调用")
        return {"user_confirmed": None}
    
    # 根据决策更新状态
    # 兼容两种格式：
    # 1. 完整数据: {"confirmed": True, ...}
    # 2. 也是完整数据，前端直接把 ConfirmationCard 的表单传回来
    
    # 检查是否包含 confirmed 字段 (前端 ai.tsx 默认传 {confirmed: true})
    is_confirmed = decision.get("confirmed", False)
    
    if is_confirmed or decision.get("type") in ("accept", "edit"):
        # 如果用户修改了参数 (例如修改了时间)
        # 前端可能直接混在 decision 顶层，也可能在 args 里
        update_data = {}
        for k, v in decision.items():
            if k not in ["confirmed", "type", "_display_message"]:
                update_data[k] = v
                
        if "args" in decision:
            update_data.update(decision["args"])
            
        if update_data and state.get("pending_operation"):
            # 返回更新后的 pending_operation（增量更新，不直接修改 state）
            logger.info(f"用户更新了参数: {update_data}")
            pending_op = state.get("pending_operation")
            updated_pending_op = dict(pending_op)
            updated_data = dict(pending_op.get("data", {}))
            updated_data.update(update_data)
            updated_pending_op["data"] = updated_data
            return {
                "user_confirmed": True,
                "pending_operation": updated_pending_op
            }
        
        return {"user_confirmed": True}
        
    elif decision.get("type") == "reject" or not is_confirmed:
        logger.info("用户拒绝了操作")
        return {"user_confirmed": False}
        
    return {"user_confirmed": False}


def execute_operation(state: TodoAgentState) -> Dict:
    """执行操作节点。
    
    职责：
    1. 检查用户确认状态
    2. 调用对应的工具函数
    3. 通过 custom 事件发送结构化结果
    4. 返回更新字典（LangGraph 推荐方式）
    
    Returns:
        Dict: 需要更新的状态字段
    """
    logger.info("=== execute_operation 节点 ===")
    
    # 初始化更新字典
    updates: Dict = {}
    
    # 获取 StreamWriter 用于发送自定义事件
    try:
        writer = get_stream_writer()
    except Exception:
        # Fallback for testing or when running outside of LangGraph context
        writer = lambda x: None
    
    user_confirmed = state.get("user_confirmed")
    operation = state.get("pending_operation")
    extracted_info = state.get("extracted_info", {})
    
    # 如果用户取消：静默处理，清理状态
    if user_confirmed is False:
        logger.info("用户拒绝操作，静默退出")
        updates["pending_operation"] = None
        updates["user_confirmed"] = None
        updates["quick_mode"] = None
        return updates
    
    # 如果没有操作（如查询）
    if not operation:
        # 直接调用查询
        result = _execute_query(extracted_info, state)
        
        # 转换 ToolResult 为 AIMessage
        if result["success"]:
            additional_kwargs = {}
            if result.get("data"):
                additional_kwargs["data"] = result["data"]
            if result.get("data_type"):
                additional_kwargs["data_type"] = result["data_type"]
            
            updates["messages"] = [AIMessage(
                content=result["message"],
                additional_kwargs=additional_kwargs
            )]
            
            # 发送 custom 事件用于前端流式渲染
            if result.get("data_type"):
                emit_result(writer, 
                           data_type=result["data_type"],
                           data=result.get("data", {}),
                           message=result["message"],
                           node="execute_operation")
            else:
                emit_token(writer, content=result["message"], node="execute_operation")
        else:
            error_msg = f"❌ {result['message']}"
            if result.get("error"):
                error_msg += f"\n错误详情: {result['error']}"
            updates["messages"] = [AIMessage(content=error_msg)]
        
        return updates

    
    # 执行确认后的操作
    action = operation.get("action")
    data = operation.get("data", {})
    
    logger.info(f"执行操作: {action}")
    
    try:
        # 使用统一的分派函数（executor_map 模式）
        result = _dispatch_execute(action, data, state)
        
        # 统一转换 ToolResult 为 AIMessage
        if result["success"]:
            # 成功：构造包含数据的 AIMessage
            additional_kwargs = {}
            if result.get("data"):
                additional_kwargs["data"] = result["data"]
            if result.get("data_type"):
                additional_kwargs["data_type"] = result["data_type"]
            
            updates["messages"] = [AIMessage(
                content=result["message"],
                additional_kwargs=additional_kwargs
            )]
            
            # 发送 custom 事件用于前端流式渲染
            if result.get("data_type"):
                emit_result(writer, 
                           data_type=result["data_type"],
                           data=result.get("data", {}),
                           message=result["message"],
                           node="execute_operation")
            else:
                emit_token(writer, content=result["message"], node="execute_operation")
        else:
            # 失败：显示错误信息
            error_msg = f"❌ {result['message']}"
            if result.get("error"):
                error_msg += f"\n错误详情: {result['error']}"
            updates["messages"] = [AIMessage(content=error_msg)]
            
    except ValueError as e:
        logger.warning(f"执行参数错误: {e}")
        updates["messages"] = [AIMessage(content=f"❌ 参数错误: {str(e)}")]
    except Exception as e:
        logger.exception(f"执行意外错误: {e}")
        updates["messages"] = [AIMessage(content="❌ 操作失败，请稍后重试")]
    
    # 清理操作状态
    updates["pending_operation"] = None
    updates["user_confirmed"] = None
    updates["quick_mode"] = None
    
    return updates


# ==================== 工具调用辅助函数 ====================

# _get_user_id_from_state 已迁移到 app.ai.utils.state_helpers
# 为保持向后兼容，创建别名
_get_user_id_from_state = get_user_id


# ==================== 执行器映射表 ====================
# 使用延迟绑定，在函数定义后初始化
_EXECUTOR_MAP: Dict[str, callable] = {}


def _get_executor_map() -> Dict[str, callable]:
    """获取执行器映射表（延迟初始化）。
    
    Returns:
        Dict: action -> executor 函数映射
    """
    global _EXECUTOR_MAP
    if not _EXECUTOR_MAP:
        _EXECUTOR_MAP = {
            "create": _execute_create,
            "update": _execute_update,
            "complete": _execute_complete,
            "delete": _execute_delete,
            "query": _execute_query,
            "batch_create": _execute_batch_create,
            "batch_complete": _execute_batch_complete,
            "merge": _execute_merge,
        }
    return _EXECUTOR_MAP


def _dispatch_execute(action: str, data: Dict, state: TodoAgentState) -> ToolResult:
    """统一的操作分派函数。
    
    Args:
        action: 操作类型
        data: 操作数据
        state: Agent 状态
        
    Returns:
        ToolResult: 执行结果
    """
    executor_map = _get_executor_map()
    executor = executor_map.get(action)
    
    if executor:
        return executor(data, state)
    else:
        return ToolResultBuilder.error(f"暂不支持操作: {action}")


def _execute_query(data: Dict, state: TodoAgentState, config: dict = None) -> ToolResult:
    """执行查询操作 - 返回结构化数据以供前端渲染 UI。
    
    Args:
        data: 查询参数
        state: Agent 状态
        config: LangGraph 运行配置（用于依赖注入）
    """
    
    user_id = _get_user_id_from_state(state)
    
    status = data.get("status")
    category = data.get("category")
    priority = _parse_priority(data.get("priority")) if data.get("priority") else None
    keyword = data.get("keyword")
    
    logger.info(f"执行查询: user_id={user_id}, status={status}, category={category}, priority={priority}, keyword={keyword}")
    
    # 使用依赖注入
    deps = get_todo_dependencies(config)
    
    try:
        with deps.get_db_context() as db:
            repo = deps.get_repository()
            todos = repo.list_by_user(
                db, 
                user_id, 
                status=status,
                category=category,
                priority=priority,
                keyword=keyword
            )
            
            # 序列化待办数据
            todos_data = []
            for t in todos:
                todos_data.append({
                    "id": t.id,
                    "title": t.title,
                    "status": t.status,
                    "description": t.description,
                    "priority": t.priority,
                    "due_date": t.due_date.strftime("%Y-%m-%d %H:%M") if t.due_date else None,
                    "category": t.category,
                    "tags": t.tags,
                    # 新增字段支持 TodoListCard
                    "start_time": t.start_time.strftime("%Y-%m-%d %H:%M") if t.start_time else None,
                    "progress": t.progress,
                    "progress_notes": t.progress_notes
                })
            
            # 返回统一的 ToolResult
            message = f"为您找到 {len(todos)} 个待办事项" if todos else "没有找到符合条件的待办事项"
            
            return ToolResultBuilder.success(
                message, 
                data={"todos": todos_data}, 
                data_type="todo_list"
            )
    
    except (ConnectionError, TimeoutError) as e:
        logger.error(f"查询待办网络错误: {e}")
        return ToolResultBuilder.error("网络连接失败，请稍后重试")
    except ValueError as e:
        logger.warning(f"查询参数错误: {e}")
        return ToolResultBuilder.error(f"查询参数无效: {str(e)}")
    except Exception as e:
        logger.exception(f"查询待办意外错误: {e}")
        return ToolResultBuilder.error("查询待办失败，请稍后重试")


def _execute_create(data: Dict, state: TodoAgentState) -> ToolResult:
    """执行创建操作。"""
    from app.ai.tools.todo_tools import add_todo
    
    user_id = _get_user_id_from_state(state)
    # config = RunnableConfig(configurable={"user_id": user_id}) 
    # Use dict literal to avoid TypedDict instantiation issues
    config = {"configurable": {"user_id": user_id}}
    
    logger.info(f"Invoking add_todo with user_id={user_id} and config={config}")
    
    # 优先使用 due_date (ISO 格式)，再回退到 time (可能是自然语言)
    due_date = data.get("due_date") or data.get("time")
    
    try:
        # 直接调用 func 以确保 config 正确传递
        result_str = add_todo.func(
            title=data.get("title", "新待办"),
            description=data.get("description", ""),
            priority=_parse_priority(data.get("priority")),
            due_date=due_date,
            category=data.get("category"),
            tags=data.get("tags"),
            reminder_enabled=data.get("reminder_enabled", False),
            location=data.get("location"),
            config=config  # 显式传递 config
        )
        
        return ToolResultBuilder.success(result_str)
    except ValueError as e:
        logger.warning(f"创建待办参数错误: {e}")
        return ToolResultBuilder.error(f"创建失败: {str(e)}")
    except (ConnectionError, TimeoutError) as e:
        logger.error(f"创建待办网络错误: {e}")
        return ToolResultBuilder.error("网络连接失败，请稍后重试")
    except Exception as e:
        logger.exception(f"创建待办意外错误: {e}")
        return ToolResultBuilder.error("创建待办失败，请稍后重试")


def _execute_batch_create(data: Dict, state: TodoAgentState) -> ToolResult:
    """执行批量创建操作。
    
    用于处理用户在一条消息中提到多个待办的场景，如：
    "明天开会，后天出差"
    """
    from app.ai.tools.todo_tools import add_todo
    
    user_id = _get_user_id_from_state(state)
    # config = RunnableConfig(configurable={"user_id": user_id})
    config = {"configurable": {"user_id": user_id}}
    
    todos = data.get("todos", [])
    if not todos:
        return ToolResultBuilder.error("没有待创建的待办项")
    
    created = []
    failed = []
    
    for todo_data in todos:
        try:
            # 直接调用 func 以确保 config 正确传递
            due_date = todo_data.get("time") or todo_data.get("due_date")
            result_str = add_todo.func(
                title=todo_data.get("title", "新待办"),
                description=todo_data.get("description", ""),
                priority=_parse_priority(todo_data.get("priority")),
                due_date=due_date,
                category=todo_data.get("category"),
                tags=todo_data.get("tags"),
                reminder_enabled=todo_data.get("reminder_enabled", False),
                location=todo_data.get("location"),
                config=config
            )
            created.append(todo_data.get("title", "新待办"))
            logger.info(f"批量创建: 成功创建 '{todo_data.get('title')}'")
        except Exception as e:
            failed.append(todo_data.get("title", "未知"))
            logger.exception(f"批量创建失败: {todo_data.get('title')}, 错误: {e}")
    
    # 汇总结果
    if created and not failed:
        return ToolResultBuilder.success(
            f"成功创建 {len(created)} 个待办：{', '.join(created)}"
        )
    elif created and failed:
        return ToolResultBuilder.success(
            f"部分成功：创建了 {len(created)} 个，失败 {len(failed)} 个\n"
            f"成功：{', '.join(created)}\n"
            f"失败：{', '.join(failed)}"
        )
    else:
        return ToolResultBuilder.error(f"批量创建失败：{', '.join(failed)}")


def _execute_update(data: Dict, state: TodoAgentState) -> ToolResult:
    """执行更新操作。
    
    注意：必须提供 todo_id。ID 解析应在 resolve_entity 阶段完成。
    如果缺失 todo_id，将返回系统错误。
    """
    from app.ai.tools.todo_tools import update_todo
    
    user_id = _get_user_id_from_state(state)
    # config = RunnableConfig(configurable={"user_id": user_id})
    config = {"configurable": {"user_id": user_id}}
    
    todo_id = data.get("todo_id") or data.get("id")
    
    # 如果没有 todo_id，直接报错 (ID 解析应在 resolve 阶段完成)
    if not todo_id:
        return ToolResultBuilder.error("系统错误：缺失待办 ID (请先尝试解析该任务)")
    
    try:
        # 直接调用 func
        result_str = update_todo.func(
            todo_id=todo_id,
            title=data.get("new_title"),  # 注意：更新时使用 new_title
            description=data.get("description"),
            priority=_parse_priority(data.get("priority")) if data.get("priority") else None,
            due_date=data.get("due_date") or data.get("time"),
            category=data.get("category"),
            status=data.get("status"),
            config=config
        )
        
        return ToolResultBuilder.success(result_str)
    except ValueError as e:
        logger.warning(f"更新待办参数错误: {e}")
        return ToolResultBuilder.error(f"更新失败: {str(e)}")
    except (ConnectionError, TimeoutError) as e:
        logger.error(f"更新待办网络错误: {e}")
        return ToolResultBuilder.error("网络连接失败，请稍后重试")
    except Exception as e:
        logger.exception(f"更新待办意外错误: {e}")
        return ToolResultBuilder.error("更新待办失败，请稍后重试")



def _execute_complete(data: Dict, state: TodoAgentState) -> ToolResult:
    """执行完成操作。"""
    from app.ai.tools.todo_tools import complete_todo
    
    user_id = _get_user_id_from_state(state)
    # config = RunnableConfig(configurable={"user_id": user_id})
    config = {"configurable": {"user_id": user_id}}
    
    try:
        # 直接调用 func
        result_str = complete_todo.func(
            todo_id=data.get("todo_id") or data.get("id"),
            config=config
        )
        
        return ToolResultBuilder.success(result_str)
    except ValueError as e:
        logger.warning(f"完成待办参数错误: {e}")
        return ToolResultBuilder.error(f"完成失败: {str(e)}")
    except (ConnectionError, TimeoutError) as e:
        logger.error(f"完成待办网络错误: {e}")
        return ToolResultBuilder.error("网络连接失败，请稍后重试")
    except Exception as e:
        logger.exception(f"完成待办意外错误: {e}")
        return ToolResultBuilder.error("完成待办失败，请稍后重试")


def _execute_delete(data: Dict, state: TodoAgentState) -> ToolResult:
    """执行删除操作。"""
    from app.ai.tools.todo_tools import delete_todo
    
    user_id = _get_user_id_from_state(state)
    # config = RunnableConfig(configurable={"user_id": user_id})
    config = {"configurable": {"user_id": user_id}}
    
    todo_id = data.get("todo_id") or data.get("id")
    if not todo_id:
        return ToolResultBuilder.error("系统错误：缺失待办 ID (请先尝试解析该任务)")
    
    try:
        # 直接调用 func
        result_str = delete_todo.func(
            todo_id=todo_id,
            config=config
        )
        
        return ToolResultBuilder.success(result_str)
    except ValueError as e:
        logger.warning(f"删除待办参数错误: {e}")
        return ToolResultBuilder.error(f"删除失败: {str(e)}")
    except (ConnectionError, TimeoutError) as e:
        logger.error(f"删除待办网络错误: {e}")
        return ToolResultBuilder.error("网络连接失败，请稍后重试")
    except Exception as e:
        logger.exception(f"删除待办意外错误: {e}")
        return ToolResultBuilder.error("删除待办失败，请稍后重试")


def _execute_batch_complete(data: Dict, state: TodoAgentState) -> ToolResult:
    """执行批量完成操作。"""
    from app.ai.tools.batch_todo_tools import batch_complete_todos
    
    user_id = _get_user_id_from_state(state)
    # config = RunnableConfig(configurable={"user_id": user_id})
    config = {"configurable": {"user_id": user_id}}
    
    try:
        # 直接调用 func
        result_str = batch_complete_todos.func(
            todo_ids=data.get("todo_ids", []),
            config=config
        )
        
        return ToolResultBuilder.success(result_str)
    except ValueError as e:
        logger.warning(f"批量完成待办参数错误: {e}")
        return ToolResultBuilder.error(f"批量完成失败: {str(e)}")
    except (ConnectionError, TimeoutError) as e:
        logger.error(f"批量完成待办网络错误: {e}")
        return ToolResultBuilder.error("网络连接失败，请稍后重试")
    except Exception as e:
        logger.exception(f"批量完成待办意外错误: {e}")
        return ToolResultBuilder.error("批量完成待办失败，请稍后重试")


def _execute_merge(data: Dict, state: TodoAgentState) -> ToolResult:
    """执行合并操作。
    
    逻辑：
    1. 如果是 draft_todos 里的任务，合并描述
    2. 如果是现有任务，建议更新（目前简化为返回提示）
    """
    target_tasks = data.get("target_tasks", [])
    merge_strategy = data.get("merge_strategy", "combine_description")
    
    logger.info(f"执行合并: target={target_tasks}, strategy={merge_strategy}")
    
    if not target_tasks:
        return ToolResultBuilder.error("合并失败", "没有指定要合并的任务")
    
    draft_todos = state.get("draft_todos", [])
    
    # 尝试在 draft_todos 中找到这些任务
    merged_indices = []
    merged_titles = []
    base_todo = None
    
    for i, todo in enumerate(draft_todos):
        # 模糊匹配标题
        for target in target_tasks:
            if target in todo.get("title", ""):
                if i not in merged_indices:
                    merged_indices.append(i)
                    merged_titles.append(todo.get("title"))
                    
                    if base_todo is None:
                        base_todo = todo
                    else:
                         # 合并逻辑：将后续任务的 标题/描述/hint 合并到 base
                        base_todo["description"] = (base_todo.get("description", "") + "\n\n" + 
                                                  f"【合并自 {todo.get('title')}】:\n" + todo.get("description", "")).strip()
                        
                        # 合并子任务提示
                        if todo.get("subtask_hints"):
                            base_todo_hints = base_todo.get("subtask_hints", [])
                            base_todo_hints.extend(todo.get("subtask_hints", []))
                            base_todo["subtask_hints"] = list(set(base_todo_hints)) # 去重
                        
                        # 合并依赖
                        if todo.get("dependencies"):
                            base_todo_deps = base_todo.get("dependencies", [])
                            base_todo_deps.extend(todo.get("dependencies", []))
                            base_todo["dependencies"] = list(set(base_todo_deps))
    
    if len(merged_indices) > 1:
        # 从 draft_todos 中移除被合并的任务（除了 base）
        # 倒序移除以免影响索引
        state["draft_todos"] = [t for i, t in enumerate(draft_todos) if i == merged_indices[0] or i not in merged_indices]
        
        return ToolResultBuilder.success(
            f"已将 {', '.join(merged_titles[1:])} 合并到 **{merged_titles[0]}** 中",
            data={"merged_todo": base_todo}
        )
    else:
        # 如果找不到足够的 draft 任务，可能是针对已存在任务的合并建议
        # 这里仅做简单反馈
        return ToolResultBuilder.success(
            f"收到合并请求 ({', '.join(target_tasks)})，已记录偏好。建议手动更新主任务描述。"
        )


def _parse_priority(priority_str: Optional[str]) -> int:
    """解析优先级字符串为数字。
    
    使用配置类中的解析方法。
    """
    return todo_config.parse_priority(priority_str)


# ==================== 路由函数 ====================

def route_next(state: TodoAgentState) -> Literal["clarify", "conflict", "resolve", "execute", "end"]:
    """路由到下一个节点 - 简化版。
    
    流程优先级:
    1. 有待办 + 需要澄清 → clarify
    2. 跳过确认（如查询）→ execute
    3. 有待办需要实体解析 → resolve
    4. 默认执行 → execute
    """
    pending_op = state.get("pending_operation")
    
    # 1. 检查是否需要跳过确认（如查询操作）
    if pending_op and pending_op.get("skip_confirmation"):
        logger.info("路由到: execute (跳过确认)")
        return "execute"
    
    # 2. 有待办 + 需要澄清 → clarify
    if pending_op and pending_op.get("needs_clarification"):
        logger.info("路由到: clarify (待办需要补充信息)")
        return "clarify"
    
    # 3. 纯澄清 (无待办) → clarify
    if state.get("pending_clarifications") and not pending_op:
        logger.info("路由到: clarify (纯澄清模式)")
        return "clarify"
    
    # 4. 有待办需要实体解析或确认 → resolve
    if pending_op:
        logger.info("路由到: resolve (实体解析)")
        return "resolve"
    
    # 5. 默认路由 (无待办 -> 澄清/聊天)
    # Fix: 避免无 pending_operation 时错误进入 execute
    logger.info("路由到: clarify (默认)")
    return "clarify"



# ==================== 图构建 ====================

def create_todo_graph(model=None, enable_thinking: bool = False, model_id: str = None, checkpointer=None):
    """创建 LangGraph 待办 Agent - 简化版。
    
    Args:
        model: LLM 实例
        enable_thinking: 是否启用深度思考
        model_id: 模型 ID
        checkpointer: 检查点保存器（可选）
        
    Returns:
        编译后的 Graph 实例
    """
    from app.ai.agents.todo_enhanced_nodes import (
        clarify_node,
        conflict_detection_node
    )
    
    workflow = StateGraph(TodoAgentState)
    
    # === 添加节点 ===
    workflow.add_node("analyze", analyze_intent)
    workflow.add_node("clarify", clarify_node)
    workflow.add_node("conflict", conflict_detection_node)
    workflow.add_node("resolve", resolve_entity)
    workflow.add_node("confirm", ask_confirmation)
    workflow.add_node("wait_confirm", wait_for_confirmation)
    workflow.add_node("execute", execute_operation)
    
    workflow.set_entry_point("analyze")
    
    # === 设置边 ===
    workflow.add_conditional_edges(
        "analyze",
        route_next,
        {
            "clarify": "clarify",
            "conflict": "conflict",
            "resolve": "resolve",
            "execute": "execute"
        }
    )
    
    workflow.add_edge("clarify", END)
    
    workflow.add_conditional_edges(
        "conflict",
        lambda state: "resolve" if state.get("pending_operation") else "execute",
        {
            "resolve": "resolve",
            "execute": "execute"
        }
    )
    
    workflow.add_conditional_edges(
        "resolve",
        route_after_resolve,
        {
            "clarify": "clarify",
            "confirm": "confirm",
            "execute": "execute"
        }
    )
    
    workflow.add_edge("confirm", "wait_confirm")
    workflow.add_edge("wait_confirm", "execute")
    workflow.add_edge("execute", END)
    
    # === 编译图 ===
    # 允许外部传入 checkpointer，以便在多智能体集成时共享或使用持久化存储
    if checkpointer is None:
        checkpointer = MemorySaver()
        
    # 注意：使用 wait_for_confirmation 内部的 interrupt() 实现暂停
    graph = workflow.compile(
        checkpointer=checkpointer
    )
    
    logger.info("待办Agent Graph (多轮对话增强版) 创建成功")
    return graph
