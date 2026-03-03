"""记忆管理审计仓储（中文注释）。"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.memory_admin_audit import UserMemoryAdminAudit


def create_audit_log(
    db: Session,
    *,
    operator_user_id: int,
    target_user_id: int | None,
    memory_id: int | None,
    action: str,
    action_payload: dict[str, Any] | None,
    result_status: str,
    error_message: str | None = None,
) -> UserMemoryAdminAudit:
    """创建一条记忆管理动作审计记录。"""

    audit = UserMemoryAdminAudit(
        operator_user_id=int(operator_user_id),
        target_user_id=target_user_id,
        memory_id=memory_id,
        action=str(action),
        action_payload=action_payload,
        result_status=str(result_status),
        error_message=error_message,
    )
    db.add(audit)
    db.flush()
    return audit
