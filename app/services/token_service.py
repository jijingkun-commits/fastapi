"""Token服务层（中文注释）。

提供Token黑名单管理功能，支持服务端登出。
"""
from datetime import datetime
from typing import Dict, Any
from sqlalchemy.orm import Session

from app.repositories import token_repo
from app.core.security import decode_token


def logout(db: Session, token: str) -> bool:
    """用户登出，将当前Token加入黑名单。
    
    Args:
        db: 数据库会话
        token: JWT Token字符串
    
    Returns:
        是否成功
    """
    try:
        payload = decode_token(token)
        jti = payload.get("jti")
        uid = int(payload.get("uid"))
        exp = payload.get("exp")
        
        if not jti:
            return False
        
        expires_at = datetime.fromtimestamp(exp)
        token_repo.add_to_blacklist(db, jti, uid, expires_at)
        return True
    except Exception:
        return False


def is_token_valid(db: Session, token: str) -> tuple[bool, Dict[str, Any]]:
    """验证Token是否有效（包括黑名单检查）。
    
    Args:
        db: 数据库会话
        token: JWT Token字符串
    
    Returns:
        (是否有效, payload字典)
    """
    try:
        payload = decode_token(token)
        jti = payload.get("jti")
        
        # 检查是否在黑名单中
        if jti and token_repo.is_blacklisted(db, jti):
            return False, {}
        
        return True, payload
    except Exception:
        return False, {}
