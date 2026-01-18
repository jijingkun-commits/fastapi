"""Prompt 加载器模块（中文注释）。

借鉴 Anthropic Skills 的渐进披露设计。
实现按需加载详细参考文档，节省 Token。

使用方式：
    from app.ai.prompts.prompt_loader import load_reference, enrich_prompt
    
    # 加载 SQL 指南
    sql_guide = load_reference("sql_guide")
    
    # 为 Prompt 添加工具参考
    enriched = enrich_prompt(base_prompt, tool_name="sql_inter")
"""
import logging
from pathlib import Path
from functools import lru_cache
from typing import Optional

logger = logging.getLogger(__name__)

# 参考文档目录
REFERENCES_DIR = Path(__file__).parent / "references"


@lru_cache(maxsize=20)
def load_reference(name: str) -> Optional[str]:
    """按需加载参考文档。
    
    Args:
        name: 参考文档名称（不含扩展名）
        
    Returns:
        文档内容，不存在则返回 None
        
    Example:
        >>> content = load_reference("sql_guide")
        >>> if content:
        ...     print(content[:100])
    """
    path = REFERENCES_DIR / f"{name}.md"
    
    if path.exists():
        try:
            content = path.read_text(encoding="utf-8")
            logger.debug("加载参考文档: %s (%d 字符)", name, len(content))
            return content
        except Exception as e:
            logger.warning("读取参考文档失败: %s - %s", name, e)
            return None
    
    logger.debug("参考文档不存在: %s", name)
    return None


# 工具名称到参考文档的映射
TOOL_REFERENCE_MAPPING = {
    "sql_inter": "sql_guide",
    "fig_inter": "chart_guide",
    "knowledge_search": "knowledge_guide",
    "python_inter": "python_guide",
    "extract_data": "data_guide",
}


def get_reference_for_tool(tool_name: str) -> Optional[str]:
    """获取工具对应的参考文档。
    
    Args:
        tool_name: 工具函数名称
        
    Returns:
        参考文档内容，如果没有则返回 None
    """
    ref_name = TOOL_REFERENCE_MAPPING.get(tool_name)
    if ref_name:
        return load_reference(ref_name)
    return None


def enrich_prompt(base_prompt: str, tool_name: str) -> str:
    """为 Prompt 添加工具参考文档。
    
    借鉴 Anthropic Skills 的渐进披露设计：
    - 核心指令保持精简
    - 详细参考按需加载
    
    Args:
        base_prompt: 基础 Prompt
        tool_name: 要添加参考的工具名称
        
    Returns:
        增强后的 Prompt
    """
    ref_content = get_reference_for_tool(tool_name)
    
    if ref_content:
        return f"{base_prompt}\n\n## 详细指南\n\n{ref_content}"
    
    return base_prompt


def list_available_references() -> list[str]:
    """列出所有可用的参考文档。"""
    if not REFERENCES_DIR.exists():
        return []
    
    return [
        f.stem for f in REFERENCES_DIR.glob("*.md")
    ]


def clear_reference_cache():
    """清除参考文档缓存。"""
    load_reference.cache_clear()
    logger.info("参考文档缓存已清除")
