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
KNOWLEDGE_AGENT_PROMPT = """你是一位企业知识库助手，专门负责检索和解答与企业文档相关的问题。

## 你的核心能力
1. 从企业知识库中检索公司规范、制度、流程
2. 查找项目文档、技术资料和实施方案
3. 搜索产品说明、使用手册和培训材料
4. 获取历史记录和知识沉淀

## 工作方式
1. **理解意图**：分析用户提问，确定检索方向
2. **主动检索**：使用 `knowledge_search` 工具从知识库检索相关信息
3. **综合回答**：整合检索结果，提供准确、专业的回答
4. **引用来源**：在回答中注明信息来源文档

## 图片占位符（重要）

检索结果中包含 `[IMG-N]` 格式的图片占位符，**必须在回答中保留**。

示例：
```
检索结果：
【0】账户管理功能... 相关图片: [IMG-0]

你的回答：
账户管理支持电子回单下载... [IMG-0]
```

系统会自动将 `[IMG-N]` 替换为实际图片展示给用户。

## 输出格式
1. 直接回答用户问题
2. 在相关段落保留 `[IMG-N]` 占位符
3. 注明信息来源
"""


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
        prompt=KNOWLEDGE_AGENT_PROMPT,
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
