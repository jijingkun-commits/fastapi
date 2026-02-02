"""通用工具函数模块。"""

import hashlib


def content_hash(content: str) -> str:
    """计算内容的短 hash，用于日志对比和去重。

    Args:
        content: 要计算 hash 的字符串内容

    Returns:
        8 位 MD5 hash 字符串，空内容返回 "empty"
    """
    if not content:
        return "empty"
    normalized = content.strip()
    return hashlib.md5(normalized.encode()).hexdigest()[:8]
