"""问数 Agent 意图分析辅助函数（中文注释）。

提供数据查询意图分析的工具函数，包括：
- 指标匹配
- 时间范围解析
- 维度提取
- SQL 安全校验
"""
import logging
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


# ==================== 指标匹配 ====================

# 预定义指标及其同义词（应与 semantic_model.yaml 保持同步）
METRIC_SYNONYMS = {
    "total_gmv": ["成交额", "销售额", "GMV", "总收入", "营收", "成交金额"],
    "order_count": ["订单数", "订单量", "成单量", "订单总数", "下单数"],
    "avg_order_value": ["客单价", "平均订单金额", "AOV", "单均价"],
    "new_user_count": ["新用户", "新增用户", "注册用户", "新注册"],
}


def match_metric(question: str) -> Optional[str]:
    """从问题中匹配预定义指标。
    
    Args:
        question: 用户问题
        
    Returns:
        匹配到的指标名称，或 None
    """
    question_lower = question.lower()
    
    for metric_name, synonyms in METRIC_SYNONYMS.items():
        for synonym in synonyms:
            if synonym.lower() in question_lower:
                logger.info(f"匹配到指标: {metric_name} (关键词: {synonym})")
                return metric_name
    
    return None


def get_metric_info(metric_name: str) -> Optional[Dict]:
    """获取指标的详细信息。
    
    Args:
        metric_name: 指标名称
        
    Returns:
        指标信息字典，包含 description, formula 等
    """
    # 简化版，生产环境应从数据库加载
    metrics_info = {
        "total_gmv": {
            "name": "total_gmv",
            "display_name": "成交总额 (GMV)",
            "description": "已支付及之后状态订单的金额总和",
            "formula": "SUM(amount) WHERE status IN ('paid', 'shipped', 'completed')",
            "model": "orders",
            "field": "amount",
            "aggregation": "sum"
        },
        "order_count": {
            "name": "order_count",
            "display_name": "订单数量",
            "description": "排除已取消订单的订单总数",
            "formula": "COUNT(*) WHERE status != 'cancelled'",
            "model": "orders",
            "aggregation": "count"
        },
        "avg_order_value": {
            "name": "avg_order_value",
            "display_name": "客单价 (AOV)",
            "description": "平均订单金额",
            "formula": "total_gmv / order_count",
            "derived": True
        },
        "new_user_count": {
            "name": "new_user_count",
            "display_name": "新增用户数",
            "description": "当天注册的新用户数量",
            "formula": "COUNT(*) WHERE DATE(createTime) = CURRENT_DATE",
            "model": "users",
            "aggregation": "count"
        }
    }
    
    return metrics_info.get(metric_name)


# ==================== 时间范围解析 ====================

TIME_PATTERNS = {
    r"今天|今日": ("today", 0),
    r"昨天|昨日": ("yesterday", 1),
    r"本周|这周": ("this_week", 7),
    r"上周": ("last_week", 14),
    r"本月|这个月": ("this_month", 30),
    r"上月|上个月": ("last_month", 60),
    r"本季度|这个季度": ("this_quarter", 90),
    r"上季度|上个季度": ("last_quarter", 180),
    r"今年|本年": ("this_year", 365),
    r"去年|上年": ("last_year", 730),
    r"过去(\d+)天|最近(\d+)天": ("last_n_days", None),
    r"过去(\d+)周|最近(\d+)周": ("last_n_weeks", None),
    r"过去(\d+)月|最近(\d+)个月": ("last_n_months", None),
}


def parse_time_range(question: str) -> Tuple[Optional[str], Optional[str]]:
    """从问题中解析时间范围。
    
    Args:
        question: 用户问题
        
    Returns:
        (time_type, time_value) 元组
        - time_type: 时间类型描述（如 "this_month"）
        - time_value: 原始匹配文本
    """
    for pattern, (time_type, _) in TIME_PATTERNS.items():
        match = re.search(pattern, question)
        if match:
            matched_text = match.group(0)
            
            # 处理动态数字
            if time_type in ["last_n_days", "last_n_weeks", "last_n_months"]:
                groups = match.groups()
                n = int(next(g for g in groups if g is not None))
                return (f"{time_type}_{n}", matched_text)
            
            return (time_type, matched_text)
    
    return (None, None)


def time_range_to_sql_filter(time_type: str, date_field: str = "created_at") -> str:
    """将时间类型转换为 SQL WHERE 子句。
    
    Args:
        time_type: 时间类型（如 "this_month", "last_n_days_7"）
        date_field: 日期字段名
        
    Returns:
        SQL WHERE 子句
    """
    if not time_type:
        return ""
    
    if time_type == "today":
        return f"AND DATE({date_field}) = CURRENT_DATE"
    elif time_type == "yesterday":
        return f"AND DATE({date_field}) = CURRENT_DATE - 1"
    elif time_type == "this_week":
        return f"AND {date_field} >= DATE_TRUNC('week', CURRENT_DATE)"
    elif time_type == "last_week":
        return f"AND {date_field} >= DATE_TRUNC('week', CURRENT_DATE - INTERVAL '1 week') AND {date_field} < DATE_TRUNC('week', CURRENT_DATE)"
    elif time_type == "this_month":
        return f"AND {date_field} >= DATE_TRUNC('month', CURRENT_DATE)"
    elif time_type == "last_month":
        return f"AND {date_field} >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month') AND {date_field} < DATE_TRUNC('month', CURRENT_DATE)"
    elif time_type == "this_quarter":
        return f"AND {date_field} >= DATE_TRUNC('quarter', CURRENT_DATE)"
    elif time_type == "this_year":
        return f"AND {date_field} >= DATE_TRUNC('year', CURRENT_DATE)"
    elif time_type.startswith("last_n_days_"):
        n = int(time_type.split("_")[-1])
        return f"AND {date_field} >= CURRENT_DATE - INTERVAL '{n} days'"
    elif time_type.startswith("last_n_weeks_"):
        n = int(time_type.split("_")[-1])
        return f"AND {date_field} >= CURRENT_DATE - INTERVAL '{n * 7} days'"
    elif time_type.startswith("last_n_months_"):
        n = int(time_type.split("_")[-1])
        return f"AND {date_field} >= CURRENT_DATE - INTERVAL '{n} months'"
    
    return ""


# ==================== 维度提取 ====================

DIMENSION_KEYWORDS = {
    "按地区": "region",
    "按区域": "region",
    "按省份": "province",
    "按城市": "city",
    "按日期": "DATE(created_at)",
    "按天": "DATE(created_at)",
    "按周": "DATE_TRUNC('week', created_at)",
    "按月": "DATE_TRUNC('month', created_at)",
    "按季度": "DATE_TRUNC('quarter', created_at)",
    "按年": "DATE_TRUNC('year', created_at)",
    "按类别": "category",
    "按分类": "category",
    "按状态": "status",
    "按用户": "user_id",
}


def extract_dimensions(question: str) -> List[str]:
    """从问题中提取聚合维度。
    
    Args:
        question: 用户问题
        
    Returns:
        维度列表
    """
    dimensions = []
    
    for keyword, dimension in DIMENSION_KEYWORDS.items():
        if keyword in question:
            dimensions.append(dimension)
            logger.info(f"提取维度: {dimension} (关键词: {keyword})")
    
    return dimensions


# ==================== SQL 安全校验 ====================
# 使用统一的安全检查工具（向后兼容导出）

from app.ai.utils.sql_safety import (
    check_sql_safety,
    add_limit_if_missing,
    DANGEROUS_KEYWORDS,
    DEFAULT_SENSITIVE_TABLES,
)


# ==================== 导出 ====================

__all__ = [
    "match_metric",
    "get_metric_info",
    "parse_time_range",
    "time_range_to_sql_filter",
    "extract_dimensions",
    "check_sql_safety",
    "add_limit_if_missing",
    "METRIC_SYNONYMS",
    "DIMENSION_KEYWORDS"
]
