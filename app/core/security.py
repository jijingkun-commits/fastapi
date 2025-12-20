"""安全相关：密码校验与JWT令牌（中文注释）。"""
import time
from typing import Any, Dict, Optional

import jwt
from passlib.context import CryptContext

from .config import JWT_SECRET, JWT_ALGORITHM, access_token_expires


# 配置密码哈希上下文，默认使用 bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def is_bcrypt_hash(value: str) -> bool:
    """判断存储的密码是否为bcrypt哈希。"""
    return isinstance(value, str) and value.startswith("$2")


def verify_password(plain_password: str, stored_password: Optional[str]) -> bool:
    """验证密码：支持明文或bcrypt哈希。"""
    if stored_password is None:
        return False
    if is_bcrypt_hash(stored_password):
        try:
            return pwd_context.verify(plain_password, stored_password)
        except Exception:
            return False
    return plain_password == stored_password


def create_access_token(subject: str, extra: Optional[Dict[str, Any]] = None) -> str:
    """创建JWT访问令牌，包含主题、签发与过期时间。"""
    now = int(time.time())
    exp_seconds = int(access_token_expires().total_seconds())
    payload: Dict[str, Any] = {"sub": subject, "iat": now, "exp": now + exp_seconds}
    if extra:
        payload.update(extra)
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    """解析并验证JWT令牌。"""
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])


def hash_password(plain_password: str) -> str:
    """生成bcrypt哈希。"""
    return pwd_context.hash(plain_password)
