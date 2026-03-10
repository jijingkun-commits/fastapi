"""知识库 Agent - 企业知识检索专家（中文注释）。

专注于从 RAGFlow 知识库中检索企业文档和规范。
"""
import logging

from langchain.agents import create_agent
from langgraph.graph.state import CompiledStateGraph

from app.ai.llm_util import get_scene_llm
from app.ai.scene_registry import SCENE_KEY_KNOWLEDGE_AGENT_FACTORY

logger = logging.getLogger(__name__)

# 知识库 Agent 系统提示词
from app.ai.prompts.knowledge_prompts import KNOWLEDGE_AGENT_SYSTEM_PROMPT


def create_knowledge_agent(
    model=None, 
    enable_thinking: bool = False, 
    model_id: str = None
) -> CompiledStateGraph:
    """创建知识库 Agent 实例。
    
    使用 LangChain 官方 create_agent 创建知识库检索 Agent。
    
    Args:
        model: 可选，指定 LLM 实例。如果为 None，则自动创建
        enable_thinking: 是否启用深度思考模式
        model_id: 模型标识
        
    Returns:
        编译后的 Agent StateGraph 实例
    """
    if model is None:
        model = get_scene_llm(
            scene_key=SCENE_KEY_KNOWLEDGE_AGENT_FACTORY,
            force_thinking=enable_thinking,
            model_id=model_id,
        )
    
    # 加载知识库检索工具
    tools = []
    try:
        from app.ai.tools.ragflow_tool import knowledge_search, is_ragflow_configured
        if is_ragflow_configured():
            tools.append(knowledge_search)
            logger.info("RAGFlow 知识库工具已加载")
        else:
            logger.warning("RAGFlow 未配置，知识库 Agent 功能受限")
    except ImportError as e:
        logger.error("RAGFlow 工具导入失败: %s", e)
    
    # 使用 LangChain 官方 create_agent
    agent = create_agent(
        model=model,
        tools=tools,
        system_prompt=KNOWLEDGE_AGENT_SYSTEM_PROMPT,
        name="knowledge_agent",
    )
    
    logger.info("知识库 Agent 创建完成，工具数量: %d", len(tools))
    return agent
