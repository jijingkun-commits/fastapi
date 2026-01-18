"""中间件配置：例如CORS（中文注释）。"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import ENV, CORS_ALLOW_ORIGINS
from app.core.middlewares.correlation import CorrelationIdMiddleware


def setup_middlewares(app: FastAPI) -> None:
    # 请求ID与耗时观测
    app.add_middleware(CorrelationIdMiddleware)

    # CORS：dev/test 默认全放开；prod 需在 CORS_ALLOW_ORIGINS 中设置允许域（逗号分隔）
    origins = ["*"] if ENV != "prod" else [o.strip() for o in CORS_ALLOW_ORIGINS.split(",") if o.strip()]
    if not origins:
        origins = ["*"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
