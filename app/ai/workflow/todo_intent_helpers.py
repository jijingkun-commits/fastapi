"""待办意图分析辅助函数（中文注释）。

从 todo_graph.py 的 analyze_intent 函数中拆分出的辅助函数。
目的：提升代码可读性和可测试性。

设计原则：
1. 辅助函数接收必要参数，返回处理结果
2. 不直接修改 state，而是返回需要更新的数据
3. 便于单元测试
4. 使用配置类管理硬编码值

注意（LLM驱动重构）：
- check_rule_based_intent, detect_urgent_task, process_clarify_intent, process_confirm_intent 已移除
- 这些功能现在由 LLM 在 analyze_intent 阶段统一处理
- 保留的函数：filter_messages_for_todo, query_existing_todos, parse_time_info,
  get_progressive_strategy, apply_goal_defaults, determine_confirmation_need, extract_heuristic_title
"""
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

from langchain_core.messages import BaseMessage, AIMessage, HumanMessage, SystemMessage
from app.ai.utils.message_factory import create_ai_message
from app.ai.config.todo_config import get_todo_config

logger = logging.getLogger(__name__)

# 获取配置实例
todo_config = get_todo_config()


# ==================== 消息过滤 ====================

def filter_messages_for_todo(
    messages: List[BaseMessage], 
    pending_handoff: Optional[Dict] = None
) -> Tuple[List[BaseMessage], str, Optional[Dict]]:
    """过滤消息并构建 Handoff 上下文。
    
    Args:
        messages: 原始消息列表
        pending_handoff: 来自 Supervisor 的 Handoff 信息
        
    Returns:
        (过滤后的消息列表, Handoff 上下文字符串, 预提取的 extracted_info)
    """
    from app.ai.protocol import MessageFilter
    import re
    
    # 待办相关的安全工具白名单
    SAFE_TOOLS = {'add_todo', 'list_todos', 'update_todo', 'complete_todo', 'delete_todo', 'update_progress'}
    
    filtered_messages = MessageFilter.filter_for_tool_whitelist(messages, SAFE_TOOLS)
    
    # 构建 Handoff 上下文 + 解析结构化信息
    handoff_context = ""
    pre_extracted_info = None
    
    if pending_handoff:
        task_desc = pending_handoff.get("task_description", "")
        if task_desc:
            handoff_context = f"\n\n## 任务来源 (Supervisor Handoff)\n用户意图已由 Supervisor 预识别：{task_desc}\n请基于此描述进行操作。"
            
            # 从 task_description 中解析结构化信息
            pre_extracted_info = {}
            
            # 解析标题
            title_match = re.search(r'标题[：:]\s*(.+?)(?:\n|$|-)', task_desc)
            if title_match:
                pre_extracted_info["title"] = title_match.group(1).strip()
            
            # 解析时间
            time_match = re.search(r'时间[：:]\s*(.+?)(?:\n|$|-)', task_desc)
            if time_match:
                pre_extracted_info["time"] = time_match.group(1).strip()
            
            # 解析地点
            location_match = re.search(r'地点[：:]\s*(.+?)(?:\n|$|-)', task_desc)
            if location_match:
                pre_extracted_info["location"] = location_match.group(1).strip()
            
            # 解析参与人员
            participants_match = re.search(r'参与人员[：:]\s*(.+?)(?:\n|$|-)', task_desc)
            if participants_match:
                pre_extracted_info["participants"] = [p.strip() for p in participants_match.group(1).split('、')]
            
            if pre_extracted_info:
                logger.info(f"从 Handoff 预提取信息: {pre_extracted_info}")
    
    return filtered_messages, handoff_context, pre_extracted_info


# ==================== 历史任务查询 ====================

def query_existing_todos(user_id: int, limit: int = 10) -> str:
    """查询用户现有待办列表。
    
    Args:
        user_id: 用户 ID
        limit: 返回的最大条数
        
    Returns:
        格式化的待办列表上下文字符串，用于注入到提示词中
    """
    from app.db.session import get_db_context
    from app.repositories.todo_repository import todo_repo
    
    try:
        with get_db_context() as db:
            existing_todos = todo_repo.list_by_user(db, user_id, status="pending")
            if not existing_todos:
                return ""
            
            todo_list = []
            for t in existing_todos[:limit]:
                due_str = t.due_date.strftime("%m月%d日") if t.due_date else "无截止"
                priority_map = {1: "高", 2: "中", 3: "低"}
                priority_str = priority_map.get(t.priority, "中")
                todo_list.append(f"- {t.title} (截止:{due_str}, 优先级:{priority_str})")
            
            context = f"\n\n## 用户现有待办 ({len(existing_todos)}项)\n" + "\n".join(todo_list)
            logger.info(f"加载用户现有待办: {len(existing_todos)} 项")
            return context
    except Exception as e:
        logger.warning(f"查询历史任务失败: {e}")
        return ""


# ==================== 时间解析 ====================

def parse_time_info(extracted_info: Dict, state_time_constraints: Optional[Dict] = None) -> Tuple[Dict, Optional[Dict]]:
    """解析时间信息并提取约束。
    
    Args:
        extracted_info: LLM 提取的信息
        state_time_constraints: 现有的时间约束
        
    Returns:
        (更新后的 extracted_info, 更新后的 time_constraints)
    """
    from app.services.time_parser import NaturalTimeParser
    
    time_parser = NaturalTimeParser()
    
    raw_time = extracted_info.get("time") or extracted_info.get("due_date")
    if not raw_time or not isinstance(raw_time, str):
        return extracted_info, state_time_constraints
    
    parsed_time, meta = time_parser.parse(raw_time)
    if parsed_time:
        extracted_info["due_date"] = parsed_time.isoformat()
        extracted_info["original_time"] = meta.get("original_text")
        logger.info(f"时间解析: '{raw_time}' -> {extracted_info['due_date']}")
    
    # 提取约束 (如 "周一不可用")
    constraints = meta.get("constraints")
    if constraints:
        current_constraints = state_time_constraints or {}
        if "blocked_weekdays" in constraints:
            current_blocked = set(current_constraints.get("blocked_weekdays", []))
            current_blocked.update(constraints["blocked_weekdays"])
            current_constraints["blocked_weekdays"] = list(current_blocked)
        logger.info(f"解析到时间约束: {constraints}")
        return extracted_info, current_constraints
    
    return extracted_info, state_time_constraints


# ==================== 紧急任务检测 ====================
# 注意：detect_urgent_task 函数已移除
# 紧急任务检测现在由 LLM 在意图分析阶段处理，通过 extracted_info.is_urgent 和 priority 字段返回


# ==================== 意图处理结果（已废弃） ====================
# 注意：以下类和函数已移除，功能由 LLM 驱动的 analyze_intent 统一处理：
# - IntentProcessResult
# - process_clarify_intent
# - process_confirm_intent  
# - check_rule_based_intent
#
# 原因：LLM 现在直接返回 action_state 和 response_message，
# 不再需要规则化的意图处理函数


def extract_heuristic_title(message: str) -> Optional[str]:
    """从消息中启发式提取标题。
    
    用于当 LLM 未能正确提取标题时的备用方案。
    
    Args:
        message: 用户消息
        
    Returns:
        提取到的标题，或 None
    """
    import re
    
    patterns = [
        r"(?:再|帮我|请)?创建一个?任务[：:]\s*(.+)",
        r"创建待办[：:]\s*(.+)",
        r"记一下[：:]\s*(.+)"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, message)
        if match:
            return match.group(1).strip()
    
    return None


def get_progressive_strategy(round_count: int, user_confirmed: bool, quick_mode: bool) -> str:
    """根据对话轮数获取渐进式策略注入。
    
    Args:
        round_count: 当前对话轮数
        user_confirmed: 用户是否已确认
        quick_mode: 是否为快速模式
        
    Returns:
        策略注入字符串
    """
    from app.ai.prompts.todo_prompts import (
        PROGRESSIVE_STRATEGY_DECISIVE,
        PROGRESSIVE_STRATEGY_RESET,
    )
    
    if round_count > todo_config.progressive_reset_threshold:
        logger.info(f"轮次 {round_count} > {todo_config.progressive_reset_threshold}，注入重置策略")
        return PROGRESSIVE_STRATEGY_RESET
    elif round_count > todo_config.progressive_round_threshold and not user_confirmed and not quick_mode:
        logger.info(f"轮次 {round_count} > {todo_config.progressive_round_threshold} 且未确认，注入果断策略")
        return PROGRESSIVE_STRATEGY_DECISIVE
    
    return ""


def apply_goal_defaults(
    intent: str,
    extracted_info: Dict,
    round_count: int
) -> Dict:
    """应用 Goal 模板的默认值（用于渐进式策略第3轮+）。
    
    当对话轮次超过阈值时，使用 Goal 模板中定义的默认值
    填充缺失字段，避免无限追问用户。
    
    借鉴自 Temporal AI Agent 的 AgentGoal.default_values 设计。
    
    Args:
        intent: 意图类型
        extracted_info: 已提取的信息
        round_count: 当前对话轮数
        
    Returns:
        填充默认值后的 extracted_info
    """
    from app.ai.config.goal_templates import get_goal_template
    
    # 只有在轮次超过阈值时才应用默认值
    if round_count <= todo_config.progressive_round_threshold:
        return extracted_info
    
    template = get_goal_template(intent)
    if not template or not template.default_values:
        return extracted_info
    
    # 复制一份避免修改原对象
    result = dict(extracted_info) if extracted_info else {}
    
    # 填充缺失的默认值
    for key, default_value in template.default_values.items():
        if not result.get(key):
            result[key] = default_value
            logger.info(f"渐进式策略: 应用默认值 {key}='{default_value}' (轮次={round_count})")
    
    return result


def determine_confirmation_need(
    intent: str, 
    quick_mode: bool,
    extracted_info: Optional[Dict] = None
) -> Tuple[bool, bool]:
    """判断是否需要确认和是否需要先澄清。
    
    优化策略：
    - 如果标题已明确，直接确认，不再追问补充信息
    - 仅当标题缺失或过于模糊时才要求澄清
    
    Args:
        intent: 意图类型
        quick_mode: 是否快速模式
        extracted_info: 提取的信息（用于判断信息完整度）
        
    Returns:
        (needs_confirmation, needs_clarification)
    """
    if quick_mode:
        logger.info("快速模式:跳过确认")
        return False, False
    
    if intent == "create":
        # 检查标题是否明确
        if extracted_info:
            title = (extracted_info.get("title") or "").strip()
           
            # 使用配置检查标题是否模糊
            if todo_config.is_vague_title(title):
                logger.info(f"创建操作: 标题模糊 (title='{title}')，需要澄清")
                return True, True
            else:
                logger.info(f"创建操作: 标题明确 (title='{title}')，只需确认")
                return True, False
        
        # 没有 extracted_info，默认需要澄清
        logger.info("创建操作: 无信息，需要澄清")
        return True, True
    
    if intent in ["delete", "update"]:
        return True, False
    
    if intent in ["query", "complete"]:
        return False, False
    
    return False, False
