"""知识库 Agent - 企业知识检索专家（中文注释）。

专注于从 RAGFlow 知识库中检索企业文档和规范。
"""
import logging
from typing import Literal

from langgraph.prebuilt import create_react_agent
from langgraph.graph.state import CompiledStateGraph

from app.ai.llm_util import get_llm

logger = logging.getLogger(__name__)

# 知识库 Agent 系统提示词
from app.ai.prompts.knowledge_prompts import KNOWLEDGE_AGENT_SYSTEM_PROMPT


def create_knowledge_agent(
    model=None, 
    enable_thinking: bool = False, 
    model_id: str = None
) -> CompiledStateGraph:
    """创建知识库 Agent 实例。
    
    使用 LangGraph 预构建的 create_react_agent 创建知识库检索 Agent。
    
    Args:
        model: 可选，指定 LLM 实例。如果为 None，则自动创建
        enable_thinking: 是否启用深度思考模式
        model_id: 模型标识
        
    Returns:
        编译后的 Agent StateGraph 实例
    """
    if model is None:
        model = get_llm(force_thinking=enable_thinking, model_id=model_id)
    
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
    
    # 使用 LangGraph 预构建的 create_react_agent
    agent = create_react_agent(
        model=model,
        tools=tools,
        prompt=KNOWLEDGE_AGENT_SYSTEM_PROMPT,
        name="knowledge_agent",
    )
    
    logger.info("知识库 Agent 创建完成，工具数量: %d", len(tools))
    return agent


def get_knowledge_agent_info() -> dict:
    """获取知识库 Agent 的状态信息。
    
    Returns:
        包含 Agent 配置和状态的字典
    """
    from app.core import config
    from app.ai.tools.ragflow_tool import is_ragflow_configured
    
    return {
        "name": "knowledge_agent",
        "description": "企业知识库检索专家",
        "configured": is_ragflow_configured(),
        "ragflow_url": config.RAGFLOW_API_URL,
        "dataset_id": config.RAGFLOW_DATASET_ID if config.RAGFLOW_API_KEY else None,
        "top_k": config.RAGFLOW_TOP_K,
        "similarity_threshold": config.RAGFLOW_SIMILARITY_THRESHOLD,
    }
