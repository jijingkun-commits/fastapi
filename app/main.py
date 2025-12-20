from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.core.logging import setup_logging
from app.core.middleware import setup_middlewares
from app.api.v1.router import api_router
from app.core.config import INIT_DB_ON_STARTUP
from app.db.init_db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    if INIT_DB_ON_STARTUP:
        init_db(seed_admin=True)
    yield


app = FastAPI(title="FastAPI Skeleton", version="0.1.0", lifespan=lifespan)

setup_middlewares(app)
app.include_router(api_router)
