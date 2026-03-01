"""核心类型定义模块（中文注释）。

定义项目中通用的 TypedDict 和类型别名，确保类型安全和代码可读性。
"""
from typing import TypedDict, Optional


class ToolResult(TypedDict):
    """工具调用统一返回类型。
    
    所有 AI 工具函数（@tool 装饰的函数）都应返回此类型，确保：
    1. 调用方可以统一处理成功/失败
    2. 前端可以根据 data_type 渲染不同 UI 组件
    3. 错误信息结构化，便于日志分析
    
    字段说明：
        success: 操作是否成功
        message: 用户可见消息（支持 Markdown 格式）
        data: 结构化数据，如待办列表、图表 URL 等（可选）
        data_type: 数据类型标识，前端据此选择渲染组件（可选）
        error: 错误详情，失败时提供调试信息（可选）
    
    示例：
        >>> ToolResultBuilder.success("✅ 待办已创建", data={"id": 123}, data_type="todo_item")
        {'success': True, 'message': '✅ 待办已创建', 'data': {'id': 123}, 'data_type': 'todo_item', 'error': None}
    """
    success: bool
    message: str
    data: Optional[dict]
    data_type: Optional[str]
    error: Optional[str]


class ToolResultBuilder:
    """工具结果构建器，简化 ToolResult 的创建。
    
    使用示例：
        # 成功场景
        return ToolResultBuilder.success("操作成功", data={"key": "value"})
        
        # 失败场景
        return ToolResultBuilder.error("操作失败", error=str(e))
    """
    
    @staticmethod
    def success(
        message: str, 
        data: Optional[dict] = None, 
        data_type: Optional[str] = None
    ) -> ToolResult:
        """构建成功结果。
        
        Args:
            message: 用户可见的成功消息
            data: 可选的结构化数据
            data_type: 数据类型标识（如 "todo_list", "chart_url"）
            
        Returns:
            ToolResult 字典
        """
        return {
            "success": True,
            "message": message,
            "data": data,
            "data_type": data_type,
            "error": None
        }
    
    @staticmethod
    def error(message: str, error: Optional[str] = None) -> ToolResult:
        """构建失败结果。
        
        Args:
            message: 用户可见的错误消息
            error: 可选的错误详情（用于日志和调试）
            
        Returns:
            ToolResult 字典
        """
        return {
            "success": False,
            "message": message,
            "data": None,
            "data_type": None,
            "error": error or message
        }
