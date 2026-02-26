"""技能管理 API 绑定/回滚测试骨架（中文注释）。

本文件用于 C03 红灯阶段，锁定多用户 Skill 绑定治理接口契约。
"""

from __future__ import annotations

from app.main import app


def test_skill_binding_api_should_exist() -> None:
    """应提供 Skill 用户绑定接口。"""

    found = False
    for route in app.routes:
        methods = getattr(route, "methods", set()) or set()
        path = getattr(route, "path", "")
        if "POST" in methods and path == "/api/v1/skill-admin/skills/{skill_id}/bind":
            found = True
            break

    assert found, "缺少 POST /api/v1/skill-admin/skills/{skill_id}/bind 接口"


def test_skill_rollback_api_should_exist() -> None:
    """应提供 Skill 绑定回滚接口。"""

    rollback_routes = []
    for route in app.routes:
        methods = getattr(route, "methods", set()) or set()
        path = getattr(route, "path", "")
        if "POST" in methods and path.startswith("/api/v1/skill-admin/skills/") and "rollback" in path:
            rollback_routes.append(path)

    assert rollback_routes, "缺少 Skill 绑定回滚接口（path 包含 rollback）"
