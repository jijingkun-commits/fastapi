"""中间件配置：例如CORS（中文注释）。"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def setup_middlewares(app: FastAPI) -> None:
    """注册中间件（目前仅启用CORS）。"""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
