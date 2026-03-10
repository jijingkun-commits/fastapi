"""多智能体图运行时 provider（中文注释）。"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Optional, Tuple

from app.core.cache_registry import get_cache_registry
from app.ai.workflow.multi_agent_graph import create_multi_agent_graph

logger = logging.getLogger(__name__)

_MULTI_AGENT_GRAPH_CACHE_KEY = "multi_agent_graph.instances"
_CACHE_LOCKS: Dict[Tuple[bool, Optional[str]], asyncio.Lock] = {}


def _get_multi_agent_graph_cache() -> Dict[Tuple[bool, Optional[str]], Any]:
    """返回共享多智能体图缓存。"""

    return get_cache_registry().get_or_create(_MULTI_AGENT_GRAPH_CACHE_KEY, dict)



def reset_multi_agent_graph_runtime() -> None:
    """清理共享多智能体图缓存与并发锁。"""

    get_cache_registry().clear(_MULTI_AGENT_GRAPH_CACHE_KEY)
    _CACHE_LOCKS.clear()


async def get_multi_agent_graph(enable_thinking: bool = False, model_id: str = None):
    """获取共享多智能体图实例（缓存），线程安全。"""

    cache_key = (enable_thinking, model_id)
    if cache_key not in _CACHE_LOCKS:
        _CACHE_LOCKS[cache_key] = asyncio.Lock()

    async with _CACHE_LOCKS[cache_key]:
        graph_cache = _get_multi_agent_graph_cache()
        if cache_key not in graph_cache:
            logger.info(
                "创建新的多智能体图实例: enable_thinking=%s, model_id=%s",
                enable_thinking,
                model_id,
            )
            graph_cache[cache_key] = await create_multi_agent_graph(
                enable_thinking=enable_thinking,
                model_id=model_id,
            )

    return _get_multi_agent_graph_cache()[cache_key]
