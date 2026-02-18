"""SQL 统一策略决策模块（中文注释）。

将 SQL 安全检查与用户权限检查收敛到一个入口，
并强制执行 deny_overrides_allow（任一阶段拒绝即拒绝）。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

from app.ai.utils.sql_safety import sanitize_sql
from app.ai.utils.sql_rewriter import check_and_rewrite_sql
from app.services.permission_service import get_permission_service

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SqlPolicyDecision:
    """SQL 策略决策结果。"""

    is_allowed: bool
    rewritten_sql: str
    reason: Optional[str] = None
    reason_code: str = "allowed"
    denied_stage: Optional[str] = None
    safety_rewritten: bool = False
    permission_rewritten: bool = False
    permission_scope_summary: Optional[Dict[str, Any]] = None


def _deny(
    *,
    sql: str,
    reason: str,
    reason_code: str,
    denied_stage: str,
    permission_scope_summary: Optional[Dict[str, Any]] = None,
) -> SqlPolicyDecision:
    """构造拒绝结果。"""

    return SqlPolicyDecision(
        is_allowed=False,
        rewritten_sql=sql,
        reason=reason,
        reason_code=reason_code,
        denied_stage=denied_stage,
        safety_rewritten=False,
        permission_rewritten=False,
        permission_scope_summary=permission_scope_summary,
    )


def _build_permission_scope_summary(user_id: Optional[int]) -> Optional[Dict[str, Any]]:
    """构建权限范围摘要，失败时降级为 None，不影响主链路。"""

    if not user_id:
        return None

    try:
        service = get_permission_service()
        ctx = service.get_user_permission_context(user_id)
        return service.summarize_permission_scope(ctx)
    except Exception as e:
        logger.warning("构建权限范围摘要失败: user_id=%s, error=%s", user_id, e)
        return None


def evaluate_sql_policy(
    sql: str,
    user_id: Optional[int],
    *,
    auto_limit: bool = True,
    limit: int = 1000,
) -> SqlPolicyDecision:
    """统一执行 SQL 安全与权限策略。

    决策顺序：
    1. 安全检查（只读、危险关键词、敏感表、Schema、多语句）
    2. 用户权限检查与重写（表级、行级、列级）
    3. deny_overrides_allow（任一阶段拒绝即拒绝）
    """

    normalized_sql = (sql or "").strip()
    if not normalized_sql:
        return _deny(
            sql=normalized_sql,
            reason="SQL 语句为空",
            reason_code="empty_sql",
            denied_stage="safety",
        )

    safe_sql, is_safe, safety_error = sanitize_sql(
        normalized_sql,
        auto_limit=auto_limit,
        limit=limit,
    )
    safety_rewritten = safe_sql != normalized_sql
    if not is_safe:
        logger.warning("SQL 安全策略拒绝: reason=%s", safety_error)
        return _deny(
            sql=safe_sql,
            reason=safety_error or "SQL 安全检查失败",
            reason_code="safety_rejected",
            denied_stage="safety",
        )

    if not user_id:
        return SqlPolicyDecision(
            is_allowed=True,
            rewritten_sql=safe_sql,
            reason=None,
            reason_code="allowed_without_user",
            denied_stage=None,
            safety_rewritten=safety_rewritten,
            permission_rewritten=False,
            permission_scope_summary=None,
        )

    rewritten_sql, is_allowed, permission_error = check_and_rewrite_sql(safe_sql, user_id)
    permission_rewritten = rewritten_sql != safe_sql
    permission_scope_summary = _build_permission_scope_summary(user_id)
    if not is_allowed:
        logger.warning(
            "SQL 权限策略拒绝: user_id=%s, reason=%s",
            user_id,
            permission_error,
        )
        return _deny(
            sql=rewritten_sql,
            reason=permission_error or "权限检查失败",
            reason_code="permission_rejected",
            denied_stage="permission",
            permission_scope_summary=permission_scope_summary,
        )

    return SqlPolicyDecision(
        is_allowed=True,
        rewritten_sql=rewritten_sql,
        reason=None,
        reason_code="allowed",
        denied_stage=None,
        safety_rewritten=safety_rewritten,
        permission_rewritten=permission_rewritten,
        permission_scope_summary=permission_scope_summary,
    )


__all__ = ["SqlPolicyDecision", "evaluate_sql_policy"]
