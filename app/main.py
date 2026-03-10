from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.router import api_router
from app.core.config import PUBLIC_DIR
from app.core.handlers import (
    global_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from app.core.memory_intent_runtime import start_memory_intent_runtime, stop_memory_intent_runtime
from app.core.middleware import setup_middlewares
from app.core.runtime import build_runtime


@asynccontextmanager
async def lifespan(app: FastAPI):
    runtime = await build_runtime()
    app.state.runtime = runtime
    start_memory_intent_runtime(app)
    try:
        yield
    finally:
        await stop_memory_intent_runtime(app)
        await runtime.aclose()


app = FastAPI(title="FastAPI Skeleton", version="0.1.0", lifespan=lifespan)

app.add_exception_handler(Exception, global_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)

images_dir = Path(PUBLIC_DIR) / "images"
app.mount("/images", StaticFiles(directory=str(images_dir), check_dir=False), name="images")

setup_middlewares(app)
app.include_router(api_router)
"""应用入口（中文注释）。

架构要点：
- 使用 FastAPI `lifespan` 管理启动/关闭逻辑，避免使用 `@app.on_event`。
- 应用级共享资源统一收口到 `app.state.runtime`，由 `lifespan` 编排创建与释放。
- 中间件统一在 `setup_middlewares` 中配置（请求ID、CORS 等）。
- 业务路由通过 `api_router` 按模块集中注册，并在路由层统一控制认证策略。
"""
