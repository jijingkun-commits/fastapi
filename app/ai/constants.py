"""AI 模块常量定义（中文注释）。

本模块定义 AI 系统中使用的枚举类型和常量，避免魔法字符串。
"""
from typing import Literal


class GraphType:
    """Graph 类型常量。"""
    SINGLE_AGENT = "single_agent"
    MULTI_AGENT = "multi_agent"


# 类型别名
GraphTypeLiteral = Literal["single_agent", "multi_agent"]
