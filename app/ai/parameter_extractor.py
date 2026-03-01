"""参数提取器模块（中文注释）。

借鉴 Flock parameter_extractor_node.py。
从用户自然语言中提取结构化参数，提升 Agent 理解准确度。

使用方式：
    from app.ai.parameter_extractor import extract_todo_params, extract_query_params
    
    # 提取待办参数
    params = await extract_todo_params("明天下午3点开会，提醒我准备PPT")
    # -> TodoParams(title="开会", due_date=datetime(...), reminder="准备PPT")
"""
import logging
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ==================== 参数模型定义 ====================

class TodoParams(BaseModel):
    """待办事项参数。"""
    title: str = Field(description="待办事项标题")
    due_date: Optional[datetime] = Field(None, description="截止时间")
    priority: Optional[str] = Field("medium", description="优先级: low/medium/high")
    category: Optional[str] = Field(None, description="分类")
    reminder: Optional[str] = Field(None, description="提醒内容")
    description: Optional[str] = Field(None, description="详细描述")


class QueryParams(BaseModel):
    """数据库查询参数。"""
    table_name: Optional[str] = Field(None, description="表名")
    columns: Optional[list[str]] = Field(None, description="查询字段")
    conditions: Optional[dict[str, Any]] = Field(None, description="查询条件")
    limit: Optional[int] = Field(10, description="结果数量限制")
    order_by: Optional[str] = Field(None, description="排序字段")


class ChartParams(BaseModel):
    """图表绘制参数。"""
    chart_type: str = Field(description="图表类型: line/bar/pie/scatter/circle/rectangle")
    title: Optional[str] = Field(None, description="图表标题")
    x_label: Optional[str] = Field(None, description="X轴标签")
    y_label: Optional[str] = Field(None, description="Y轴标签")
    data: Optional[dict] = Field(None, description="数据")
    style: Optional[dict] = Field(None, description="样式参数")


# ==================== 提取 Prompt ====================

from app.ai.prompts.common_prompts import (
    TODO_PARAM_EXTRACT_PROMPT,
    QUERY_PARAM_EXTRACT_PROMPT,
    CHART_PARAM_EXTRACT_PROMPT
)


# ==================== 提取函数 ====================

async def extract_todo_params(message: str, model_id: str = None) -> TodoParams:
    """从用户消息中提取待办事项参数。
    
    Args:
        message: 用户消息
        model_id: 可选的模型 ID
        
    Returns:
        TodoParams 结构化参数
        
    Example:
        >>> params = await extract_todo_params("明天下午3点开会")
        >>> print(params.title)  # "开会"
        >>> print(params.due_date)  # datetime(2026, 1, 15, 15, 0)
    """
    from app.ai.llm_util import get_scene_llm
    from app.ai.scene_registry import SCENE_KEY_PARAM_TODO

    llm = get_scene_llm(
        scene_key=SCENE_KEY_PARAM_TODO,
        model_id=model_id,
    )
    
    try:
        # 使用 with_structured_output 确保返回结构化数据
        structured_llm = llm.with_structured_output(TodoParams)
        
        result = await structured_llm.ainvoke(
            TODO_PARAM_EXTRACT_PROMPT.format(
                message=message[:1000],
                now=datetime.now().isoformat()
            )
        )
        
        logger.info("待办参数提取完成: title=%s, due_date=%s", 
                   result.title, result.due_date)
        
        return result
        
    except Exception as e:
        logger.warning("待办参数提取失败: %s，使用原始消息作为标题", e)
        # 降级：使用原始消息作为标题
        return TodoParams(title=message[:100])


async def extract_query_params(message: str, model_id: str = None) -> QueryParams:
    """从用户消息中提取数据库查询参数。"""
    from app.ai.llm_util import get_scene_llm
    from app.ai.scene_registry import SCENE_KEY_PARAM_QUERY

    llm = get_scene_llm(
        scene_key=SCENE_KEY_PARAM_QUERY,
        model_id=model_id,
    )

    try:
        structured_llm = llm.with_structured_output(QueryParams)
        
        result = await structured_llm.ainvoke(
            QUERY_PARAM_EXTRACT_PROMPT.format(message=message[:1000])
        )
        
        logger.info("查询参数提取完成: table=%s", result.table_name)
        return result
        
    except Exception as e:
        logger.warning("查询参数提取失败: %s", e)
        return QueryParams()


async def extract_chart_params(message: str, model_id: str = None) -> ChartParams:
    """从用户消息中提取图表绘制参数。"""
    from app.ai.llm_util import get_scene_llm
    from app.ai.scene_registry import SCENE_KEY_PARAM_CHART

    llm = get_scene_llm(
        scene_key=SCENE_KEY_PARAM_CHART,
        model_id=model_id,
    )

    try:
        structured_llm = llm.with_structured_output(ChartParams)
        
        result = await structured_llm.ainvoke(
            CHART_PARAM_EXTRACT_PROMPT.format(message=message[:1000])
        )
        
        logger.info("图表参数提取完成: type=%s", result.chart_type)
        return result
        
    except Exception as e:
        logger.warning("图表参数提取失败: %s", e)
        # 降级：尝试推断类型
        chart_type = "circle" if "圆" in message else "line"
        return ChartParams(chart_type=chart_type)
