"""意图分类器模块（中文注释）。

借鉴 Flock Intent Recognition Node 和 OpenAI Agents SDK routing.py。
使用轻量级模型快速识别用户意图，减少主模型 Token 消耗。
"""
import json
import logging
from typing import Literal, Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# 定义意图类型
IntentType = Literal[
    "greeting",           # 问候/闲聊
    "web_search",         # 需要联网
    "knowledge_query",    # 知识库查询
    "data_query",         # 数据库查询
    "data_analysis",      # 复杂数据分析
    "todo_management",    # 待办事项
    "chart_drawing",      # 绘图
    "image_analysis",     # 图片分析
    "file_processing",    # 文件处理
    "unknown"             # 未知
]


class IntentResult(BaseModel):
    """意图识别结果。"""
    intent: IntentType
    confidence: float = 0.8
    route_to: str = "supervisor"  # supervisor / data_expert / todo_expert


# 意图分类 Prompt（精简版，节省 Token）
from app.ai.prompts.common_prompts import INTENT_CLASSIFY_PROMPT


async def classify_intent(message: str, model_id: str = None) -> IntentResult:
    """分类用户意图。
    
    使用轻量级模型快速分类，节省 Token。
    
    Args:
        message: 用户消息内容
        model_id: 可选的模型 ID，默认使用配置的意图分类器模型
        
    Returns:
        IntentResult 包含意图类型、置信度和路由目标
    """
    from app.ai.llm_util import get_llm, _normalize_text_content
    from app.core.config import (
        INTENT_CLASSIFIER_MODEL, MODEL_ROUTING_INTENT_CLASSIFIER, get_routing_model
    )
    
    # 使用配置的意图分类器模型，添加降级策略
    # 优先级：用户指定 model_id → t_system_config 配置 → 环境变量回退 → 默认模型
    llm = None
    
    # 尝试 1: 使用用户指定的模型或配置的意图分类器模型
    target_model = model_id or get_routing_model(MODEL_ROUTING_INTENT_CLASSIFIER, INTENT_CLASSIFIER_MODEL)
    if target_model:
        try:
            llm = get_llm(model_id=target_model)
            logger.debug("意图分类器使用模型: %s", target_model)
        except Exception as e:
            logger.warning("意图分类器模型 %s 不可用: %s，尝试降级", target_model, e)
    
    # 尝试 2: 降级使用默认模型
    if llm is None:
        try:
            llm = get_llm()
            logger.info("意图分类器降级使用默认模型")
        except Exception as e:
            logger.error("意图分类器无法获取任何可用模型: %s", e)
            # 直接返回 unknown，避免系统崩溃
            return IntentResult(intent="unknown", confidence=0.0, route_to="supervisor")
    
    try:
        response = await llm.ainvoke(
            INTENT_CLASSIFY_PROMPT.format(message=message[:500])  # 截断过长消息
        )
        
        content = _normalize_text_content(
            response.content if hasattr(response, "content") else response
        ).strip()
        
        # 提取 JSON（处理可能的 markdown 代码块）
        if "```" in content:
            # 从代码块中提取 JSON
            import re
            json_match = re.search(r'```(?:json)?\s*(\{[^`]+\})\s*```', content)
            if json_match:
                content = json_match.group(1)
        
        data = json.loads(content)
        result = IntentResult(**data)
        
        logger.info(
            "意图识别完成: intent=%s, confidence=%.2f, route_to=%s",
            result.intent, result.confidence, result.route_to
        )
        if result.intent == "web_search":
            logger.info("意图识别为联网搜索: message=%s", message[:100] if message else "(空)")
        
        return result
        
    except json.JSONDecodeError as e:
        logger.warning("意图分类 JSON 解析失败: %s, 原始内容: %s", e, content[:100])
        return IntentResult(intent="unknown", confidence=0.5, route_to="supervisor")
    except Exception as e:
        logger.warning("意图分类失败: %s", e)
        return IntentResult(intent="unknown", confidence=0.5, route_to="supervisor")


def classify_intent_sync(message: str, model_id: str = None) -> IntentResult:
    """同步版本的意图分类（用于非异步上下文）。"""
    import asyncio
    
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # 如果已在异步上下文中，使用 nest_asyncio 或返回默认值
            return IntentResult(intent="unknown", confidence=0.5, route_to="supervisor")
        return loop.run_until_complete(classify_intent(message, model_id))
    except Exception:
        return IntentResult(intent="unknown", confidence=0.5, route_to="supervisor")
