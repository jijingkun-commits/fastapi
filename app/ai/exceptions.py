"""AI 模块自定义异常（中文注释）。

定义 AI Agent 相关的异常类型，用于细化错误处理。

设计原则：
1. 异常类型层次化，便于捕获特定类型错误
2. 包含足够的上下文信息用于调试
3. 区分可恢复和不可恢复错误
"""


class TodoAgentError(Exception):
    """Todo Agent 基础异常类。"""
    
    def __init__(self, message: str, details: dict = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}
    
    def __str__(self):
        if self.details:
            return f"{self.message} | 详情: {self.details}"
        return self.message


# ==================== LLM 相关异常 ====================

class LLMError(TodoAgentError):
    """LLM 调用相关错误的基类。"""
    pass


class LLMInvocationError(LLMError):
    """LLM 调用失败（网络、超时等）。"""
    pass


class LLMParseError(LLMError):
    """LLM 响应解析失败（JSON 格式错误等）。
    
    这是可恢复错误，通常可以通过降级处理。
    """
    
    def __init__(self, message: str, raw_content: str = None, details: dict = None):
        super().__init__(message, details)
        self.raw_content = raw_content


class LLMRateLimitError(LLMError):
    """LLM 速率限制错误。"""
    pass


# ==================== 数据库相关异常 ====================

class DatabaseError(TodoAgentError):
    """数据库操作相关错误的基类。"""
    pass


class EntityNotFoundError(DatabaseError):
    """实体未找到错误。"""
    
    def __init__(self, entity_type: str, identifier: str = None, details: dict = None):
        message = f"{entity_type} 未找到"
        if identifier:
            message += f": {identifier}"
        super().__init__(message, details)
        self.entity_type = entity_type
        self.identifier = identifier


class DuplicateEntityError(DatabaseError):
    """重复实体错误。"""
    
    def __init__(self, entity_type: str, identifier: str = None, details: dict = None):
        message = f"{entity_type} 已存在"
        if identifier:
            message += f": {identifier}"
        super().__init__(message, details)
        self.entity_type = entity_type
        self.identifier = identifier


class DatabaseConnectionError(DatabaseError):
    """数据库连接错误。"""
    pass


# ==================== 用户输入相关异常 ====================

class UserInputError(TodoAgentError):
    """用户输入相关错误的基类。
    
    这类错误通常需要向用户反馈，而不是静默处理。
    """
    pass


class MissingRequiredFieldError(UserInputError):
    """缺少必填字段错误。"""
    
    def __init__(self, field_name: str, details: dict = None):
        message = f"缺少必填信息: {field_name}"
        super().__init__(message, details)
        self.field_name = field_name


class InvalidFieldValueError(UserInputError):
    """字段值无效错误。"""
    
    def __init__(self, field_name: str, value: str = None, details: dict = None):
        message = f"无效的 {field_name}"
        if value:
            message += f": {value}"
        super().__init__(message, details)
        self.field_name = field_name
        self.value = value


class AmbiguousEntityError(UserInputError):
    """实体歧义错误（找到多个匹配）。"""
    
    def __init__(self, query: str, candidates: list = None, details: dict = None):
        message = f"找到多个匹配项: {query}"
        super().__init__(message, details)
        self.query = query
        self.candidates = candidates or []


# ==================== 工作流相关异常 ====================

class WorkflowError(TodoAgentError):
    """工作流执行相关错误的基类。"""
    pass


class NodeExecutionError(WorkflowError):
    """节点执行错误。"""
    
    def __init__(self, node_name: str, original_error: Exception = None, details: dict = None):
        message = f"节点 '{node_name}' 执行失败"
        if original_error:
            message += f": {str(original_error)}"
        super().__init__(message, details)
        self.node_name = node_name
        self.original_error = original_error


class StateTransitionError(WorkflowError):
    """状态转换错误。"""
    pass


class TimeoutError(WorkflowError):
    """操作超时错误。"""
    pass


class HandoffValidationError(WorkflowError):
    """Handoff 校验错误（无效的目标 Agent）。"""
    
    def __init__(self, message: str, invalid_target: str = None, details: dict = None):
        super().__init__(message, details)
        self.invalid_target = invalid_target


# ==================== 权限相关异常 ====================

class PermissionError(TodoAgentError):
    """权限相关错误。"""
    pass


class UnauthorizedError(PermissionError):
    """未授权错误。"""
    pass


class ForbiddenError(PermissionError):
    """禁止访问错误。"""
    pass
