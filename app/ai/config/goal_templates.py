"""Goal 模板系统 - 借鉴自 Temporal AI Agent

为每种意图定义槽位和 Few-shot 示例，提升 LLM 提取准确率。

设计来源：
- Temporal AI Agent 的 AgentGoal.example_conversation_history
- 参考 https://github.com/temporal-community/temporal-ai-agent/blob/main/goals/travel.py
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class GoalTemplate:
    """意图模板定义
    
    Attributes:
        required_slots: 必填槽位列表
        optional_slots: 选填槽位列表
        default_values: 默认值（用于渐进式策略第3轮）
        few_shot_examples: Few-shot 示例列表 (输入, 期望输出)
        prompt_hint: Prompt 提示（简短描述意图）
        requires_confirmation: 是否需要用户确认
    """
    
    required_slots: List[str]
    optional_slots: List[str] = field(default_factory=list)
    default_values: Dict[str, str] = field(default_factory=dict)
    few_shot_examples: List[Tuple[str, Dict]] = field(default_factory=list)
    prompt_hint: str = ""
    requires_confirmation: bool = True


# 所有意图的 Goal 模板定义
GOAL_TEMPLATES: Dict[str, GoalTemplate] = {
    
    # ==================== 创建意图 ====================
    "create": GoalTemplate(
        required_slots=["title"],
        optional_slots=["due_date", "priority", "category", "description", "location", "remind_before"],
        default_values={
            "priority": "中",
            "category": "工作",
        },
        few_shot_examples=[
            # 基础创建
            ("帮我记一下明天开会", {
                "intent": "create",
                "extracted_info": {"title": "开会", "due_date": "明天"}
            }),
            ("下周五前要完成报告", {
                "intent": "create",
                "extracted_info": {"title": "完成报告", "due_date": "下周五"}
            }),
            ("记录：和产品经理讨论需求", {
                "intent": "create",
                "extracted_info": {"title": "和产品经理讨论需求"}
            }),
            # 带优先级
            ("添加一个高优先级任务：紧急修复Bug", {
                "intent": "create",
                "extracted_info": {"title": "紧急修复Bug", "priority": "高"}
            }),
            # 带地点
            ("明天下午去上海开会", {
                "intent": "create",
                "extracted_info": {"title": "去上海开会", "due_date": "明天下午", "location": "上海"}
            }),
            # 带提醒
            ("后天的演示，提前2小时提醒我", {
                "intent": "create",
                "extracted_info": {"title": "演示", "due_date": "后天", "remind_before": 120}
            }),
        ],
        prompt_hint="用户想创建待办，优先提取标题和时间",
        requires_confirmation=True,
    ),
    
    # ==================== 查询意图 ====================
    "query": GoalTemplate(
        required_slots=[],
        optional_slots=["keyword", "date_range", "status", "category", "priority"],
        few_shot_examples=[
            ("列出今天的待办", {
                "intent": "query",
                "extracted_info": {"date_range": "今天"}
            }),
            ("有哪些高优先级的任务", {
                "intent": "query",
                "extracted_info": {"priority": "高"}
            }),
            ("查看上海相关的待办", {
                "intent": "query",
                "extracted_info": {"keyword": "上海"}
            }),
            ("这周还有什么没做完", {
                "intent": "query",
                "extracted_info": {"date_range": "本周", "status": "pending"}
            }),
            ("工作分类下有几个待办", {
                "intent": "query",
                "extracted_info": {"category": "工作"}
            }),
        ],
        prompt_hint="用户想查询待办列表",
        requires_confirmation=False,
    ),
    
    # ==================== 更新意图 ====================
    "update": GoalTemplate(
        required_slots=["target_ref"],
        optional_slots=["new_title", "new_due_date", "new_priority", "new_category", "new_description"],
        few_shot_examples=[
            ("把开会改到后天", {
                "intent": "update",
                "extracted_info": {"target_ref": "开会", "new_due_date": "后天"}
            }),
            ("修改买菜的优先级为高", {
                "intent": "update",
                "extracted_info": {"target_ref": "买菜", "new_priority": "高"}
            }),
            ("把 ID 5 的任务改成下周一截止", {
                "intent": "update",
                "extracted_info": {"todo_id": 5, "new_due_date": "下周一"}
            }),
            ("把报告的分类改成工作", {
                "intent": "update",
                "extracted_info": {"target_ref": "报告", "new_category": "工作"}
            }),
        ],
        prompt_hint="用户想修改已有待办",
        requires_confirmation=True,
    ),
    
    # ==================== 完成意图 ====================
    "complete": GoalTemplate(
        required_slots=["target_ref"],
        optional_slots=[],
        few_shot_examples=[
            ("完成买菜", {
                "intent": "complete",
                "extracted_info": {"target_ref": "买菜"}
            }),
            ("把 ID 12 的任务标记为完成", {
                "intent": "complete",
                "extracted_info": {"todo_id": 12}
            }),
            ("搞定了开会那个", {
                "intent": "complete",
                "extracted_info": {"target_ref": "开会"}
            }),
            ("刚才说的那个做完了", {
                "intent": "complete",
                "extracted_info": {"target_ref": "last_mentioned"}
            }),
            ("把演示文稿那个完成", {
                "intent": "complete",
                "extracted_info": {"target_ref": "演示文稿"}
            }),
        ],
        prompt_hint="用户想标记待办为完成",
        requires_confirmation=True,
    ),
    
    # ==================== 删除意图 ====================
    "delete": GoalTemplate(
        required_slots=["target_ref"],
        optional_slots=[],
        few_shot_examples=[
            ("删掉买菜", {
                "intent": "delete",
                "extracted_info": {"target_ref": "买菜"}
            }),
            ("取消明天的会议", {
                "intent": "delete",
                "extracted_info": {"target_ref": "明天的会议"}
            }),
            ("不需要那个任务了", {
                "intent": "delete",
                "extracted_info": {"target_ref": "last_mentioned"}
            }),
            ("删除 ID 45 的待办", {
                "intent": "delete",
                "extracted_info": {"todo_id": 45}
            }),
        ],
        prompt_hint="用户想删除待办",
        requires_confirmation=True,
    ),
    
    # ==================== 确认意图 ====================
    "confirm": GoalTemplate(
        required_slots=[],
        optional_slots=[],
        few_shot_examples=[
            ("好的", {"intent": "confirm"}),
            ("确认", {"intent": "confirm"}),
            ("可以", {"intent": "confirm"}),
            ("就这样", {"intent": "confirm"}),
            ("行", {"intent": "confirm"}),
            ("嗯", {"intent": "confirm"}),
            ("OK", {"intent": "confirm"}),
        ],
        prompt_hint="用户确认之前的操作",
        requires_confirmation=False,
    ),
    
    # ==================== 澄清意图 ====================
    "clarify": GoalTemplate(
        required_slots=[],
        optional_slots=[],
        few_shot_examples=[
            ("帮我理一理", {
                "intent": "clarify",
                "needs_clarification": True,
                "missing_info": ["具体任务", "时间范围"]
            }),
            ("太多了怎么办", {
                "intent": "clarify",
                "needs_clarification": True,
                "missing_info": ["优先级", "筛选条件"]
            }),
            ("优先级怎么排", {
                "intent": "clarify",
                "needs_clarification": True,
                "missing_info": ["排序依据"]
            }),
            ("有几个项目要做", {
                "intent": "clarify",
                "needs_clarification": True,
                "missing_info": ["项目细节", "截止时间"]
            }),
        ],
        prompt_hint="用户表达模糊，需要澄清或建议",
        requires_confirmation=False,
    ),
    
    # ==================== 闲聊意图 ====================
    "chat": GoalTemplate(
        required_slots=[],
        optional_slots=[],
        few_shot_examples=[
            ("你好", {"intent": "chat"}),
            ("今天天气怎么样", {"intent": "chat"}),
            ("谢谢", {"intent": "chat"}),
        ],
        prompt_hint="非待办相关的闲聊",
        requires_confirmation=False,
    ),
}


def get_goal_template(intent: str) -> Optional[GoalTemplate]:
    """获取指定意图的 Goal 模板
    
    Args:
        intent: 意图名称
        
    Returns:
        GoalTemplate 或 None
    """
    return GOAL_TEMPLATES.get(intent)


def get_few_shot_examples(intent: str, max_examples: int = 3) -> List[Tuple[str, Dict]]:
    """获取指定意图的 Few-shot 示例
    
    Args:
        intent: 意图名称
        max_examples: 最大示例数量（避免 Token 过多）
        
    Returns:
        Few-shot 示例列表
    """
    template = GOAL_TEMPLATES.get(intent)
    if template and template.few_shot_examples:
        return template.few_shot_examples[:max_examples]
    return []


def get_default_values(intent: str) -> Dict[str, str]:
    """获取指定意图的默认值（用于渐进式策略）
    
    Args:
        intent: 意图名称
        
    Returns:
        默认值字典
    """
    template = GOAL_TEMPLATES.get(intent)
    if template:
        return template.default_values.copy()
    return {}


def build_few_shot_prompt(intent: str, max_examples: int = 3) -> str:
    """构建 Few-shot 示例的 Prompt 文本
    
    Args:
        intent: 意图名称
        max_examples: 最大示例数量
        
    Returns:
        格式化的 Prompt 文本
    """
    import json
    
    template = GOAL_TEMPLATES.get(intent)
    if not template:
        return ""
    
    lines = []
    
    # 意图提示
    if template.prompt_hint:
        lines.append(f"**提示**: {template.prompt_hint}")
    
    # 槽位信息
    if template.required_slots:
        lines.append(f"**必填字段**: {', '.join(template.required_slots)}")
    if template.optional_slots:
        lines.append(f"**选填字段**: {', '.join(template.optional_slots)}")
    
    # Few-shot 示例
    examples = template.few_shot_examples[:max_examples]
    if examples:
        lines.append("\n**示例**:")
        for user_input, expected_output in examples:
            lines.append(f'输入: "{user_input}"')
            lines.append(f'输出: {json.dumps(expected_output, ensure_ascii=False)}')
            lines.append("")
    
    return "\n".join(lines)
