"""问数 Agent - 数据分析专家（中文注释）。

专注于数据库查询、Python 数据处理和可视化图表生成。
"""
import logging
from langgraph.prebuilt import create_react_agent

from app.ai.llm_util import get_llm
from app.ai.prompts.agent_prompts import DATA_AGENT_PROMPT

logger = logging.getLogger(__name__)

# DATA_AGENT_PROMPT 已迁移到 app/ai/prompts/agent_prompts.py


def create_data_agent(model=None, enable_thinking: bool = False, model_id: str = None):
    """创建问数 Agent 实例。
    
    Args:
        model: 可选，指定 LLM 实例。如果为 None，则自动创建
        enable_thinking: 是否启用深度思考模式
        model_id: 模型标识
        
    Returns:
        编译后的 Agent 实例
    """
    if model is None:
        model = get_llm(force_thinking=enable_thinking, model_id=model_id)
    
    # 加载数据分析工具
    from app.ai.tools.chatTools import sql_inter, extract_data, python_inter, fig_inter
    
    tools = [sql_inter, extract_data, python_inter, fig_inter]
    
    # 加载共享工具（图片分析、文件读取）
    try:
        from app.ai.tools.vision_tool import analyze_image, is_vision_configured
        if is_vision_configured():
            tools.append(analyze_image)
            logger.debug("data_agent: 已加载 analyze_image 工具")
    except Exception as e:
        logger.warning("data_agent: Vision 工具加载失败: %s", e)
    
    try:
        from app.ai.tools.file_tools import read_uploaded_file
        tools.append(read_uploaded_file)
        logger.debug("data_agent: 已加载 read_uploaded_file 工具")
    except Exception as e:
        logger.warning("data_agent: 文件读取工具加载失败: %s", e)
    
    agent = create_react_agent(
        model,
        tools,
        prompt=DATA_AGENT_PROMPT,
        name="data_agent",
    )
    
    logger.info("问数 Agent 创建完成，工具数量: %d", len(tools))
    return agent
