"""Todo Agent 配置模块（中文注释）。

集中管理 Todo Agent 的所有配置项，避免硬编码。

设计原则：
1. 使用 Pydantic BaseSettings 支持环境变量覆盖
2. 所有魔法值集中在此处定义
3. 支持运行时配置注入

注意：关键词检测（取消、确认、快速模式、紧急）已迁移到 LLM 驱动模式，
不再使用硬编码关键词列表。相关方法已移除。
"""
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class TodoAgentConfig(BaseSettings):
    """Todo Agent 配置类。
    
    支持通过环境变量覆盖，环境变量前缀为 TODO_AGENT_。
    例如：TODO_AGENT_MAX_DAILY_HOURS=10
    """
    
    # ==================== 工作量配置 ====================
    default_hours_per_task: int = Field(
        default=2,
        description="默认每个任务预估工时"
    )
    max_daily_hours: int = Field(
        default=8,
        description="每日最大工作时长"
    )
    max_todos_per_query: int = Field(
        default=200,
        description="查询待办的最大数量"
    )
    context_todos_limit: int = Field(
        default=10,
        description="上下文中显示的待办数量上限"
    )
    
    # ==================== 渐进式策略配置 ====================
    progressive_round_threshold: int = Field(
        default=2,
        description="触发果断策略的对话轮数阈值"
    )
    progressive_reset_threshold: int = Field(
        default=5,
        description="触发重置策略的对话轮数阈值"
    )
    
    # ==================== 标题验证配置 ====================
    # 注意：取消、确认、快速模式、紧急等关键词检测已迁移到 LLM 驱动模式
    vague_title_keywords: List[str] = Field(
        default=["这个", "那个", "它", "东西", "事情"],
        description="模糊标题关键词（用于兜底验证）"
    )
    
    # ==================== 优先级映射 ====================
    priority_map_cn: dict = Field(
        default={"高": 1, "中": 2, "低": 3},
        description="中文优先级映射"
    )
    priority_map_en: dict = Field(
        default={"high": 1, "medium": 2, "low": 3},
        description="英文优先级映射"
    )
    priority_map_num: dict = Field(
        default={"1": 1, "2": 2, "3": 3},
        description="数字优先级映射"
    )
    
    # ==================== 显示配置 ====================
    priority_display_map: dict = Field(
        default={1: "🔴 高", 2: "🟡 中", 3: "🟢 低"},
        description="优先级显示映射"
    )
    
    model_config = {
        "env_prefix": "TODO_AGENT_",
        "case_sensitive": False
    }
    
    def parse_priority(self, priority_str: Optional[str]) -> int:
        """解析优先级字符串为数字。
        
        Args:
            priority_str: 优先级字符串（中文/英文/数字）
            
        Returns:
            优先级数字（1=高, 2=中, 3=低），默认返回 2
        """
        if not priority_str:
            return 2
        
        priority_lower = str(priority_str).lower().strip()
        
        # 依次尝试各种映射
        if priority_lower in self.priority_map_cn:
            return self.priority_map_cn[priority_lower]
        if priority_lower in self.priority_map_en:
            return self.priority_map_en[priority_lower]
        if priority_lower in self.priority_map_num:
            return self.priority_map_num[priority_lower]
        
        return 2  # 默认中优先级
    
    # 注意：is_cancel, is_confirm, is_quick_mode, is_urgent 方法已移除
    # 这些检测现在由 LLM 在意图分析阶段完成
    
    def is_vague_title(self, title: str) -> bool:
        """检查标题是否模糊。"""
        if not title:
            return True
        title_stripped = title.strip()
        if len(title_stripped) < 2:
            return True
        return any(title_stripped == kw for kw in self.vague_title_keywords)
    
    def get_priority_display(self, priority: int) -> str:
        """获取优先级的显示文本。"""
        return self.priority_display_map.get(priority, "🟡 中")


# 全局配置实例（单例模式）
_config_instance: Optional[TodoAgentConfig] = None


def get_todo_config() -> TodoAgentConfig:
    """获取 Todo Agent 配置实例（单例）。
    
    Returns:
        TodoAgentConfig 实例
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = TodoAgentConfig()
    return _config_instance


def reset_todo_config():
    """重置配置实例（用于测试）。"""
    global _config_instance
    _config_instance = None


# ==================== 依赖注入支持 ====================

from typing import Callable, Any


class TodoDependencies:
    """Todo Agent 依赖容器。
    
    用于在测试中注入模拟依赖，或在生产环境中使用真实依赖。
    
    使用方法:
    ```python
    # 获取依赖（优先使用 config 中的，其次使用默认）
    deps = get_todo_dependencies(config)
    repo = deps.get_repository()
    db = deps.get_db_session()
    ```
    """
    
    def __init__(
        self,
        repository_factory: Optional[Callable[[], Any]] = None,
        db_session_factory: Optional[Callable[[], Any]] = None,
        llm_factory: Optional[Callable[[], Any]] = None,
    ):
        """初始化依赖容器。
        
        Args:
            repository_factory: 仓库工厂函数
            db_session_factory: 数据库会话工厂函数
            llm_factory: LLM 工厂函数
        """
        self._repository_factory = repository_factory
        self._db_session_factory = db_session_factory
        self._llm_factory = llm_factory
        
        # 缓存的实例
        self._repository_instance = None
    
    def get_repository(self):
        """获取待办仓库实例。
        
        如果设置了工厂函数，使用工厂创建；否则使用默认仓库。
        """
        if self._repository_factory:
            return self._repository_factory()
        
        # 延迟导入避免循环依赖
        if self._repository_instance is None:
            from app.repositories.todo_repository import TodoRepository
            self._repository_instance = TodoRepository()
        return self._repository_instance
    
    def get_db_context(self):
        """获取数据库上下文管理器。
        
        如果设置了工厂函数，使用工厂创建；否则使用默认上下文。
        """
        if self._db_session_factory:
            return self._db_session_factory()
        
        # 使用默认的数据库上下文
        from app.db.session import get_db_context
        return get_db_context()
    
    def get_llm(self, **kwargs):
        """获取 LLM 实例。
        
        如果设置了工厂函数，使用工厂创建；否则使用默认 LLM。
        """
        if self._llm_factory:
            return self._llm_factory(**kwargs)
        
        # 使用默认的 LLM
        from app.ai.llm_util import get_llm
        return get_llm(**kwargs)


# 默认依赖实例
_default_dependencies: Optional[TodoDependencies] = None


def get_todo_dependencies(config: Optional[dict] = None) -> TodoDependencies:
    """获取 Todo Agent 依赖容器。
    
    优先从 config["configurable"]["dependencies"] 获取，
    如果没有则返回默认依赖。
    
    Args:
        config: LangGraph 运行配置
        
    Returns:
        TodoDependencies 实例
    """
    global _default_dependencies
    
    # 尝试从 config 中获取
    if config:
        configurable = config.get("configurable", {})
        if "dependencies" in configurable:
            return configurable["dependencies"]
    
    # 使用默认依赖
    if _default_dependencies is None:
        _default_dependencies = TodoDependencies()
    return _default_dependencies


def set_todo_dependencies(deps: TodoDependencies):
    """设置默认依赖实例（用于测试）。
    
    Args:
        deps: TodoDependencies 实例
    """
    global _default_dependencies
    _default_dependencies = deps


def reset_todo_dependencies():
    """重置依赖实例（用于测试）。"""
    global _default_dependencies
    _default_dependencies = None
