"""Agent 能力声明模块

借鉴 Microsoft TypeAgent Dispatcher 的设计:
- Schema 声明式路由
- Agent 动态启用/禁用
- 优先级匹配

@see https://github.com/microsoft/TypeAgent/tree/main/ts/packages/dispatcher
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


@dataclass
class AgentSchema:
    """Agent 能力声明
    
    借鉴 TypeAgent 的 Agent 配置模式，
    通过 Schema 声明 Agent 支持的意图和实体。
    
    Attributes:
        agent_id: Agent 唯一标识
        display_name: 用户可见名称
        description: Agent 功能描述
        supported_intents: 能处理的意图集合
        supported_entities: 能处理的实体类型集合
        priority: 优先级（数字越小优先级越高）
        enabled: 是否启用
    """
    agent_id: str
    display_name: str
    description: str
    
    # 能处理的意图（类似 TypeAgent 的 Schemas）
    supported_intents: Set[str] = field(default_factory=set)
    
    # 能处理的实体类型（类似 TypeAgent 的 Actions）
    supported_entities: Set[str] = field(default_factory=set)
    
    # 优先级（数字越小优先级越高）
    priority: int = 100
    
    # 是否启用（借鉴 TypeAgent 的动态开关）
    enabled: bool = True


# ==================== Agent 能力注册表 ====================

AGENT_CAPABILITIES: Dict[str, AgentSchema] = {
    
    # 数据分析专家
    "data_expert": AgentSchema(
        agent_id="data_expert",
        display_name="数据分析专家",
        description="处理数据查询、分析、可视化相关请求",
        supported_intents={
            "data_analysis", 
            "sql_query", 
            "chart_generation", 
            "metric_query",
            "data_insight",
            "report_generation",
        },
        supported_entities={
            "Table", 
            "Column", 
            "Metric", 
            "Chart",
            "Dashboard",
            "Report",
        },
        priority=10,
    ),
    
    # 待办助手
    "todo_expert": AgentSchema(
        agent_id="todo_expert",
        display_name="待办助手",
        description="处理任务管理相关请求",
        supported_intents={
            "create_todo", 
            "query_todo", 
            "update_todo", 
            "delete_todo", 
            "complete_todo",
            "todo_reminder",
        },
        supported_entities={
            "Todo", 
            "Reminder", 
            "Task",
            "Deadline",
        },
        priority=10,
    ),
    
    # 知识助手
    "knowledge_expert": AgentSchema(
        agent_id="knowledge_expert",
        display_name="知识助手",
        description="处理知识库检索和问答",
        supported_intents={
            "knowledge_search",
            "document_qa",
            "faq",
        },
        supported_entities={
            "Document",
            "Knowledge",
            "FAQ",
        },
        priority=20,
    ),
    
    # 通用助手（Supervisor 兜底）
    "supervisor": AgentSchema(
        agent_id="supervisor",
        display_name="通用助手",
        description="处理闲聊和无法分类的请求",
        supported_intents={
            "chat", 
            "unknown", 
            "greeting",
            "help",
        },
        priority=100,  # 最低优先级，兜底
    ),
}


# ==================== 路由函数 ====================

def route_by_schema(
    detected_intent: str, 
    detected_entities: Optional[Set[str]] = None
) -> str:
    """基于 Schema 匹配最佳 Agent
    
    借鉴 TypeAgent Dispatcher 的路由逻辑：
    1. 首先按 intent 匹配
    2. 如果有多个候选，按 entity 匹配加权
    3. 最后按优先级排序
    
    Args:
        detected_intent: 检测到的意图
        detected_entities: 检测到的实体类型集合
        
    Returns:
        匹配的 agent_id
    """
    detected_entities = detected_entities or set()
    candidates: List[Tuple[str, int, int]] = []
    
    for agent_id, schema in AGENT_CAPABILITIES.items():
        if not schema.enabled:
            continue
            
        # Intent 匹配
        if detected_intent in schema.supported_intents:
            # 计算 Entity 匹配度
            entity_score = len(detected_entities & schema.supported_entities)
            candidates.append((agent_id, schema.priority, entity_score))
    
    if not candidates:
        logger.info(f"无匹配 Agent，使用 supervisor 兜底 (intent={detected_intent})")
        return "supervisor"
    
    # 按优先级（升序）、Entity 匹配度（降序）排序
    candidates.sort(key=lambda x: (x[1], -x[2]))
    
    best_agent = candidates[0][0]
    logger.info(f"Schema 路由: intent={detected_intent} -> {best_agent}")
    
    return best_agent


def get_enabled_agents() -> List[str]:
    """获取所有启用的 Agent
    
    类似 TypeAgent 的 @config agent 列表
    """
    return [
        agent_id 
        for agent_id, schema in AGENT_CAPABILITIES.items()
        if schema.enabled
    ]
