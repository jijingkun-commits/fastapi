from contextlib import asynccontextmanager
from fastapi import FastAPI


from app.core.logging import setup_logging
from app.core.middleware import setup_middlewares
from app.api.v1.router import api_router
from app.core.config import INIT_DB_ON_STARTUP
from app.db.init_db import init_db
from app.db.postgres_checkpoint import get_checkpointer, close_checkpointer
from app.core.memory_intent_runtime import start_memory_intent_runtime, stop_memory_intent_runtime


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时初始化
    setup_logging()

    # 3.1配置校验 (Fail Fast)
    try:
        from app.core.settings import Settings
        Settings() # 实例化即校验，失败会抛出 ValidationError
        import logging
        logging.info("配置校验通过")
    except Exception as e:
        import logging
        logging.critical(f"配置校验失败: {e}")
        raise e
    
    # PostgreSQL 数据库初始化
    if INIT_DB_ON_STARTUP:
        try:
            init_db(seed_admin=True)
        except Exception as e:
            import logging
            logging.exception("数据库初始化失败")
            raise e
    
    
    # PostgreSQL Checkpointer 初始化（用于 LangGraph 状态持久化）
    try:
        await get_checkpointer()
    except Exception as e:
        import logging
        logging.exception("PostgreSQL Checkpointer 初始化失败")
        raise e
        
    # 初始化 LLM/系统/场景配置服务（Fail Fast）
    try:
        from app.services.llm_config_service import LLMConfigService
        from app.services.llm_scene_service import LLMSceneService
        from app.services.system_config_service import SystemConfigService
        from app.db.session import SessionLocal

        with SessionLocal() as db:
            LLMConfigService.load_from_db(db)
            SystemConfigService.load_from_db(db)
            LLMSceneService.load_from_db(db)
            LLMSceneService.validate_startup_integrity()
    except Exception as e:
        import logging

        logging.critical("配置服务初始化失败，终止启动: %s", e)
        raise

    # 结果增强规则缓存（失败不阻断启动）
    try:
        from app.services.result_enrichment_rule_service import get_result_enrichment_rule_service

        rule_service = get_result_enrichment_rule_service()
        rule_service.refresh_rules()
    except Exception:
        import logging

        logging.exception("结果增强规则初始化失败，将跳过并继续启动")

    # Skill 运行时以数据库 definition/version 为唯一来源；启动阶段不再扫描本地 SKILL.md。
    try:
        import logging

        logging.info("技能运行时已切换为 DB-only，跳过本地技能文件同步")
    except Exception:
        pass

    start_memory_intent_runtime(app)

    yield

    await stop_memory_intent_runtime(app)

    # 关闭时清理资源
    await close_checkpointer()


app = FastAPI(title="FastAPI Skeleton", version="0.1.0", lifespan=lifespan)

from app.core.handlers import (
    global_exception_handler,
    http_exception_handler,
    validation_exception_handler
)
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

app.add_exception_handler(Exception, global_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)

# 挂载静态文件目录 (用于显示生成的图片)
from fastapi.staticfiles import StaticFiles
from app.core.config import PUBLIC_DIR
import os

# 确保图片目录存在
images_dir = os.path.join(PUBLIC_DIR, "images")
os.makedirs(images_dir, exist_ok=True)

# 挂载 /images 路径
app.mount("/images", StaticFiles(directory=images_dir), name="images")

setup_middlewares(app)
app.include_router(api_router)
"""应用入口（中文注释）。

架构要点：
- 使用 FastAPI `lifespan` 管理启动/关闭逻辑，避免使用 `@app.on_event`。
- 中间件统一在 `setup_middlewares` 中配置（请求ID、CORS 等）。
- 业务路由通过 `api_router` 按模块集中注册，并在路由层统一控制认证策略。
- 可选的初始化逻辑（如建库与种子数据）通过环境变量控制。
"""
