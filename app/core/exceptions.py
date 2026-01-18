"""自定义异常类（中文注释）。

待办助手相关的异常定义。
"""


class TodoException(Exception):
    """待办相关异常基类。"""
    pass


class TodoNotFoundException(TodoException):
    """待办不存在异常。"""
    def __init__(self, todo_id: int):
        self.todo_id = todo_id
        super().__init__(f"待办 {todo_id} 不存在")


class TodoPermissionDeniedException(TodoException):
    """无权限操作待办异常。"""
    def __init__(self, todo_id: int, user_id: int):
        self.todo_id = todo_id
        self.user_id = user_id
        super().__init__(f"用户 {user_id} 无权操作待办 {todo_id}")


class TodoValidationException(TodoException):
    """待办数据验证失败异常。"""
    def __init__(self, message: str):
        super().__init__(f"数据验证失败: {message}")


class RecurringTaskException(TodoException):
    """重复任务相关异常。"""
    pass
