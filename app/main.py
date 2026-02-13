from contextlib import asynccontextmanager
from fastapi import FastAPI
from pathlib import Path


from app.core.logging import setup_logging
from app.core.middleware import setup_middlewares
from app.api.v1.router import api_router
from app.core.config import INIT_DB_ON_STARTUP
from app.db.init_db import init_db
from app.db.postgres_checkpoint import get_checkpointer, close_checkpointer


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
        
    # 初始化 LLM 配置服务（加载模型配置到缓存）
    try:
        from app.services.llm_config_service import LLMConfigService
        from app.services.system_config_service import SystemConfigService
        from app.db.session import SessionLocal
        with SessionLocal() as db:
            LLMConfigService.load_from_db(db)
            SystemConfigService.load_from_db(db)

            from app.services.result_enrichment_rule_service import get_result_enrichment_rule_service
            rule_service = get_result_enrichment_rule_service()
            rule_service.refresh_rules()
    except Exception as e:
        import logging
        logging.exception("配置服务初始化失败，将使用环境变量降级")

    # 启动时自动同步技能文件到数据库（失败可观测且不阻断启动）
    try:
        import logging
        import os

        from app.core.config import PROJECT_ROOT
        from app.services.skill_service import SkillService

        skills_dir = os.path.join(PROJECT_ROOT, "app/ai/skills")
        count = SkillService.sync_changed_skills(Path(skills_dir))
        logging.info("技能同步完成: path=%s, updated=%d", skills_dir, count)
    except Exception:
        import logging

        logging.exception("技能启动同步失败，将跳过并继续启动")

    yield
    
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
