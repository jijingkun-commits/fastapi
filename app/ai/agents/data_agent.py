"""问数 Agent - 数据分析专家（中文注释）。

专注于数据库查询、Python 数据处理和可视化图表生成。
"""
import logging
from langchain.agents import create_agent

from app.ai.llm_util import get_llm

logger = logging.getLogger(__name__)

# 问数 Agent 系统提示词
DATA_AGENT_PROMPT = """你是一位专业的数据分析师，擅长：
- SQL 数据库查询和数据提取
- Python 数据处理与分析
- 数据可视化和图表生成

## 你的核心能力
1. **SQL 查询**: 使用 `sql_inter` 工具执行 SQL 语句查询数据
2. **数据提取**: 使用 `extract_data` 工具将查询结果保存为 DataFrame
3. **Python 分析**: 使用 `python_inter` 工具执行数据分析代码
4. **图表生成**: 使用 `fig_inter` 工具生成可视化图表

## 工作流程
1. 理解用户的数据需求
2. 编写并执行 SQL 查询获取数据
3. 如需要，使用 Python 进行进一步处理
4. 根据需求生成图表或统计报告

## 注意事项
- 先解释你的分析计划，再执行操作
- 确保 SQL 语法正确，先验证再执行复杂查询
- 图表中的文字使用英文以避免乱码
"""


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
    
    agent = create_agent(
        model=model,
        tools=tools,
        system_prompt=DATA_AGENT_PROMPT,
        name="data_agent",
    )
    
    logger.info("问数 Agent 创建完成，工具数量: %d", len(tools))
    return agent
