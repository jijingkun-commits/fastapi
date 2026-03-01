"""Token黑名单数据访问层（中文注释）。"""
from datetime import datetime
from sqlalchemy.orm import Session

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
