"""应用级 runtime 资源 owner 与启动编排。"""

from __future__ import annotations

from dataclasses import dataclass, field
import inspect
import logging
from pathlib import Path
from typing import Any, Awaitable, Callable, Optional, TypeAlias

from app.ai.utils.observability import flush_tracer, get_tracer
from app.core.cache_registry import CacheRegistry, get_cache_registry, reset_cache_registry
from app.ai.workflow import get_multi_agent_graph
from app.ai.workflow.runtime_graph_provider import reset_multi_agent_graph_runtime
from app.core.config import INIT_DB_ON_STARTUP, PUBLIC_DIR
from app.core.logging import setup_logging
from app.core.settings import Settings
from app.db.init_db import init_db
from app.db.postgres_checkpoint import close_checkpointer, get_checkpointer
from app.db.session import SessionLocal, close_database_runtime, get_database_runtime
from app.services.asset_service import get_asset_service
from app.services.llm_config_service import LLMConfigService
from app.services.llm_scene_service import LLMSceneService
from app.services.result_enrichment_rule_service import get_result_enrichment_rule_service
from app.services.run_control_service import get_run_control_service, reset_run_control_service
from app.services.system_config_service import SystemConfigService

logger = logging.getLogger(__name__)

CleanupCallback: TypeAlias = Callable[[], Awaitable[None] | None]


@dataclass(slots=True)
class GraphRuntime:
    """图运行时资源。"""

    default_multi_agent_graph: Optional[Any] = None


@dataclass(slots=True)
class AppRuntime:
    """应用级共享资源唯一 owner。"""

    db: Any
    checkpointer: Any
    tracer: Any
    asset_service: Any
    graphs: GraphRuntime
    cache_registry: CacheRegistry
    cleanup_callbacks: list[CleanupCallback] = field(default_factory=list)

    async def aclose(self) -> None:
        """按逆序执行清理回调，单个清理失败不阻断后续释放。"""

        for callback in reversed(self.cleanup_callbacks):
            try:
                result = callback()
                if inspect.isawaitable(result):
                    await result
            except Exception:
                logger.exception("关闭 AppRuntime 资源失败: %s", getattr(callback, "__name__", repr(callback)))


async def build_runtime() -> AppRuntime:
    """构建应用级 runtime。"""

    setup_logging()

    cleanup_callbacks: list[CleanupCallback] = []
    cache_registry = None
    db_runtime = None
    checkpointer = None
    tracer = None
    asset_service = None
    default_graph = None

    try:
        Settings()
        logger.info("配置校验通过")

        cache_registry = get_cache_registry()
        reset_run_control_service()
        reset_cache_registry()
        cleanup_callbacks.append(reset_cache_registry)
        cleanup_callbacks.append(reset_run_control_service)
        reset_multi_agent_graph_runtime()
        cleanup_callbacks.append(reset_multi_agent_graph_runtime)

        db_runtime = get_database_runtime()
        cleanup_callbacks.append(close_database_runtime)

        if INIT_DB_ON_STARTUP:
            init_db(seed_admin=True)

        images_dir = Path(PUBLIC_DIR) / "images"
        images_dir.mkdir(parents=True, exist_ok=True)

        checkpointer = await get_checkpointer()
        cleanup_callbacks.append(close_checkpointer)

        with SessionLocal() as db:
            LLMConfigService.load_from_db(db)
            SystemConfigService.load_from_db(db)
            LLMSceneService.load_from_db(db)
            LLMSceneService.validate_startup_integrity()

        tracer = get_tracer()
        cleanup_callbacks.append(flush_tracer)

        try:
            get_result_enrichment_rule_service().refresh_rules()
            cache_registry.set_status("result_enrichment_rules", "warmed")
        except Exception:
            cache_registry.set_status("result_enrichment_rules", "degraded")
            logger.exception("结果增强规则初始化失败，将跳过并继续启动")

        try:
            asset_service = get_asset_service()
            cache_registry.set_status("asset_service", "warmed")
        except Exception:
            cache_registry.set_status("asset_service", "degraded")
            logger.exception("资产服务初始化失败，将跳过并继续启动")

        try:
            get_run_control_service()
            cache_registry.set_status("run_control_service", "warmed")
        except Exception:
            cache_registry.set_status("run_control_service", "degraded")
            logger.exception("运行控制服务初始化失败，将跳过并继续启动")

        try:
            default_graph = await get_multi_agent_graph(enable_thinking=False, model_id=None)
            cache_registry.set_status("default_multi_agent_graph", "warmed")
        except Exception:
            cache_registry.set_status("default_multi_agent_graph", "degraded")
            logger.exception("默认多智能体图预热失败，将跳过并继续启动")

        logger.info("技能运行时已切换为 DB-only，跳过本地技能文件同步")

        return AppRuntime(
            db=db_runtime,
            checkpointer=checkpointer,
            tracer=tracer,
            asset_service=asset_service,
            graphs=GraphRuntime(default_multi_agent_graph=default_graph),
            cache_registry=cache_registry,
            cleanup_callbacks=cleanup_callbacks,
        )
    except Exception:
        await AppRuntime(
            db=db_runtime,
            checkpointer=checkpointer,
            tracer=tracer,
            asset_service=asset_service,
            graphs=GraphRuntime(default_multi_agent_graph=default_graph),
            cache_registry=cache_registry,
            cleanup_callbacks=cleanup_callbacks,
        ).aclose()
        raise
