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
import json
import logging
import re
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

from langchain_core.messages import BaseMessage, AIMessage, HumanMessage, SystemMessage
from app.ai.utils.message_factory import create_ai_message
from app.ai.config.todo_config import get_todo_config

logger = logging.getLogger(__name__)

# 获取配置实例
todo_config = get_todo_config()


# ==================== 指代归一化（Canonicalization） ====================

_REFERENCE_PREFIXES = ("这个", "那个", "这", "那")

_REFERENCE_SUFFIXES = (
    "这个任务", "那个任务", "这个待办", "那个待办", "这个项目", "那个项目",
    "这个事情", "那个事情", "这个", "那个", "该任务", "该待办", "该项目"
)

_GENERIC_REFERENCE_WORDS = {
    "这个", "那个", "这", "那", "它", "任务", "待办", "项目", "事情",
    "这个任务", "那个任务", "这个待办", "那个待办", "这个项目", "那个项目",
    "该任务", "该待办", "该项目"
}

_EXPLICIT_ACTION_HINTS = (
    "创建", "新建", "新增", "记录", "记一下", "查询", "查看", "列出",
    "完成", "做完", "标记", "删除", "删掉", "取消", "修改", "更新", "改到", "改成", "推迟"
)


def clean_reference_text(text: Optional[str]) -> str:
    """清洗待办指代文本。

    目标：将“项目汇报那个/这个任务”归一为“项目汇报”，
    同时过滤“这个/那个”这类纯指代词。
    """
    if not isinstance(text, str):
        return ""

    cleaned = text.strip()
    if not cleaned:
        return ""

    # 去掉句尾标点
    cleaned = re.sub(r"[，。！？,.!?]+$", "", cleaned).strip()

    # 去掉常见前缀（如“这个报告” -> “报告”）
    for prefix in _REFERENCE_PREFIXES:
        if cleaned.startswith(prefix) and len(cleaned) > len(prefix):
            cleaned = cleaned[len(prefix):].strip()
            break

    # 去掉常见后缀（如“项目汇报那个” -> “项目汇报”）
    for suffix in sorted(_REFERENCE_SUFFIXES, key=len, reverse=True):
        if cleaned.endswith(suffix) and len(cleaned) > len(suffix):
            cleaned = cleaned[:-len(suffix)].strip()
            break

    if cleaned in _GENERIC_REFERENCE_WORDS:
        return ""

    return cleaned


def canonicalize_extracted_info(extracted_info: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """将 LLM 提取结果归一化为执行链路的 canonical 字段。

    说明：
    - 保留原始别名字段用于兼容和排障
    - 优先填充 canonical 字段（title/due_date/priority/category/description）
    """
    if isinstance(extracted_info, dict):
        result = dict(extracted_info)
    else:
        result = {}

    alias_mapping = {
        "title": ["target_title", "target_ref"],
        "due_date": ["new_due_date"],
        "priority": ["new_priority"],
        "category": ["new_category"],
        "description": ["new_description"],
    }

    # 先用别名补齐 canonical 字段
    for canonical_key, alias_keys in alias_mapping.items():
        if result.get(canonical_key):
            continue
        for alias_key in alias_keys:
            alias_value = result.get(alias_key)
            if alias_value:
                result[canonical_key] = alias_value
                break

    # 对目标类文本字段做指代清洗
    for key in ("title", "target_title", "target_ref", "keyword"):
        value = result.get(key)
        if not isinstance(value, str):
            continue

        value = value.strip()
        if not value:
            continue

        normalized = clean_reference_text(value)
        # 纯指代词清洗后为空时，显式置空，避免误匹配
        if value in _GENERIC_REFERENCE_WORDS and not normalized:
            result[key] = ""
        elif normalized:
            result[key] = normalized

    return result


def extract_reference_keyword(
    extracted_info: Optional[Dict[str, Any]],
    fallback_message: str = ""
) -> str:
    """从 extracted_info 或消息中提取可用于实体解析的目标关键词。"""
    info = canonicalize_extracted_info(extracted_info)

    for key in ("title", "target_title", "target_ref", "keyword"):
        value = info.get(key)
        if isinstance(value, str):
            normalized = clean_reference_text(value)
            if normalized:
                return normalized

    normalized_message = clean_reference_text(fallback_message)
    if normalized_message and not any(hint in fallback_message for hint in _EXPLICIT_ACTION_HINTS):
        return normalized_message

    return ""


def is_implicit_reference_message(user_message: str, extracted_info: Optional[Dict[str, Any]] = None) -> bool:
    """判断用户是否在使用“无动作指代”表达。

    例如："项目汇报那个"、"这个任务"、"刚才那个"。
    """
    if not isinstance(user_message, str):
        return False

    text = user_message.strip()
    if not text:
        return False

    # 出现显式动作词时，不视为“无动作指代”
    if any(hint in text for hint in _EXPLICIT_ACTION_HINTS):
        return False

    info = canonicalize_extracted_info(extracted_info)
    if info.get("todo_id"):
        return False

    # 具备指代特征 + 能提取到有效目标关键词
    has_reference_pattern = (
        text.endswith(("这个", "那个", "这个任务", "那个任务", "这个待办", "那个待办", "这个项目", "那个项目"))
        or text.startswith(("这个", "那个"))
        or "刚才那个" in text
        or "之前那个" in text
    )

    keyword = extract_reference_keyword(info, text)
    return has_reference_pattern and bool(keyword)


def _extract_tool_observation_summary(handoff_frame: Optional[Dict[str, Any]]) -> str:
    """从 handoff.frame.tool_observations 中提炼简短摘要。"""
    if not isinstance(handoff_frame, dict):
        return ""

    observations = handoff_frame.get("tool_observations")
    if not isinstance(observations, list):
        return ""

    chunks: List[str] = []
    for obs in observations[:2]:
        if not isinstance(obs, dict):
            continue

        summary = str(obs.get("summary") or "").strip()
        if not summary:
            continue

        topic = str(obs.get("topic") or "").strip()
        if topic:
            chunks.append(f"{topic}: {summary}")
        else:
            chunks.append(summary)

    merged = "；".join(chunks)
    merged = re.sub(r"\s+", " ", merged).strip()
    return merged[:260] if merged else ""


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
        handoff_frame = pending_handoff.get("frame")

        if task_desc:
            handoff_context = f"\n\n## 任务来源 (Supervisor Handoff)\n用户意图已由 Supervisor 预识别：{task_desc}\n请基于此描述进行操作。"

        pre_extracted_info = {}

        # 优先消费结构化 frame（会话意图内核 V2）
        if isinstance(handoff_frame, dict):
            todo_fields = handoff_frame.get("todo_fields") if isinstance(handoff_frame.get("todo_fields"), dict) else {}
            for key in ("title", "time", "due_date", "priority", "category", "description", "progress_notes", "todo_id"):
                value = todo_fields.get(key) if key in todo_fields else handoff_frame.get(key)
                if value not in (None, "", [], {}):
                    pre_extracted_info[key] = value

            todo_action = str(handoff_frame.get("todo_action") or "").strip()
            if todo_action:
                pre_extracted_info["action"] = todo_action

            # Supervisor 工具观察结果：提炼摘要并并入描述
            raw_observations = handoff_frame.get("tool_observations")
            if isinstance(raw_observations, str):
                try:
                    raw_observations = json.loads(raw_observations)
                except json.JSONDecodeError:
                    raw_observations = None

            if isinstance(raw_observations, list):
                pre_extracted_info["tool_observations"] = raw_observations
                observation_summary = _extract_tool_observation_summary(
                    {"tool_observations": raw_observations}
                )
                if observation_summary:
                    existing_desc = str(pre_extracted_info.get("description") or "").strip()
                    observation_desc = f"外部信息补充：{observation_summary}"
                    if existing_desc and observation_desc not in existing_desc:
                        pre_extracted_info["description"] = f"{existing_desc}\n{observation_desc}"
                    elif not existing_desc:
                        pre_extracted_info["description"] = observation_desc

                    handoff_context += f"\n外部信息摘要：{observation_summary}"

        # 回退：从 task_description 中做轻量结构化解析
        if task_desc:
            title_match = re.search(r'标题[：:]\s*(.+?)(?:\n|$|-)', task_desc)
            if title_match and not pre_extracted_info.get("title"):
                pre_extracted_info["title"] = title_match.group(1).strip()

            time_match = re.search(r'时间[：:]\s*(.+?)(?:\n|$|-)', task_desc)
            if time_match and not pre_extracted_info.get("time"):
                pre_extracted_info["time"] = time_match.group(1).strip()

            location_match = re.search(r'地点[：:]\s*(.+?)(?:\n|$|-)', task_desc)
            if location_match and not pre_extracted_info.get("location"):
                pre_extracted_info["location"] = location_match.group(1).strip()

            participants_match = re.search(r'参与人员[：:]\s*(.+?)(?:\n|$|-)', task_desc)
            if participants_match and not pre_extracted_info.get("participants"):
                pre_extracted_info["participants"] = [p.strip() for p in participants_match.group(1).split('、')]

        if pre_extracted_info:
            logger.info(f"从 Handoff 预提取信息: {pre_extracted_info}")
        else:
            pre_extracted_info = None

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
