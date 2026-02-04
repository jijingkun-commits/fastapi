"""Token黑名单数据访问层（中文注释）。"""
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import delete

from app.models.token_blacklist import TokenBlacklist


def add_to_blacklist(
    db: Session,
    token_jti: str,
    user_id: int,
    expires_at: datetime
) -> TokenBlacklist:
    """将Token加入黑名单。"""
    record = TokenBlacklist(
        token_jti=token_jti,
        user_id=user_id,
        expires_at=expires_at
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def is_blacklisted(db: Session, token_jti: str) -> bool:
    """检查Token是否在黑名单中。"""
    record = db.query(TokenBlacklist).filter(
        TokenBlacklist.token_jti == token_jti
    ).first()
    return record is not None


def blacklist_user_tokens(db: Session, user_id: int, expires_at: datetime) -> int:
    """将用户的所有Token加入黑名单（用于强制踢出）。
    
    注意：由于我们不存储所有已发放的Token，这里只能标记用户被禁用。
    实际的Token验证会在 deps.py 中检查用户的 is_active 状态。
    
    Returns:
        受影响的行数（本实现中始终为0，因为不追踪所有Token）
    """
    return 0


def cleanup_expired(db: Session) -> int:
    """清理过期的黑名单记录。
    
    Returns:
        删除的记录数
    """
    result = db.execute(
        delete(TokenBlacklist).where(TokenBlacklist.expires_at < datetime.now())
    )
    db.commit()
    return result.rowcount
