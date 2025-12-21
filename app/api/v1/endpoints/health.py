"""健康检查接口：通用健康、数据库可用性、连接池状态。"""
import logging
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.db.session import get_db, engine


router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    """返回服务健康状态。"""
    return {"status": "ok"}


@router.get("/health/db")
def health_db(db: Session = Depends(get_db)):
    """验证数据库连接是否可用。"""
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "db": True}
    except Exception as e:
        logging.getLogger("app.health").error(f"db health failed: {e}")
        return {"status": "error", "db": False}


@router.get("/health/pool")
def health_pool():
    """返回连接池状态信息。"""
    pool = engine.pool
    status = getattr(pool, "status", lambda: "unknown")()
    size = getattr(pool, "size", lambda: None)()
    checkedout = getattr(pool, "checkedout", lambda: None)()
    overflow = getattr(pool, "overflow", lambda: None)()
    logging.getLogger("app.health").info(
        f"pool size={size} checkedout={checkedout} overflow={overflow}"
    )
    return {
        "status": "ok",
        "pool": {
            "size": size,
            "checked_out": checkedout,
            "overflow": overflow,
            "status": status,
        },
    }
