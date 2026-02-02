"""AI Schema 模块

包含:
- Agent 能力声明 (AgentSchema)
- 多 Agent 路由增强
"""

from app.ai.schema.agent_schema import (
    AgentSchema,
    AGENT_CAPABILITIES,
    route_by_schema,
    get_enabled_agents,
)

__all__ = [
    'AgentSchema',
    'AGENT_CAPABILITIES',
    'route_by_schema',
    'get_enabled_agents',
]
