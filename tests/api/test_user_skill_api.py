"""用户 Skill 自维护 API 测试。"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Generator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.api.v1.endpoints.user_skill_api import router as user_skill_router
from app.db.session import get_db
from app.services.skill_service import SkillService


@pytest.fixture
def user_skill_client() -> Generator[TestClient, None, None]:
    """挂载用户 Skill 路由的测试客户端。"""

    app = FastAPI()
    app.include_router(user_skill_router, prefix="/api/v1")

    def _override_get_db():
        yield object()

    def _override_current_user():
        return SimpleNamespace(id=1901, role="user", is_active=True)

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_current_user

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


def test_user_skill_list_should_scope_to_current_user(user_skill_client: TestClient, monkeypatch) -> None:  # noqa: ANN001
    """列表接口应仅查询 current_user.id 的绑定数据。"""

    captured = {}

    def _fake_list(cls, db, user_id=None, skill_id=None, binding_status=None):  # noqa: ANN001
        captured["db"] = db
        captured["user_id"] = user_id
        captured["skill_id"] = skill_id
        captured["binding_status"] = binding_status
        return [
            {
                "user_id": user_id,
                "skill_id": "loan-advice",
                "version": "v2",
                "binding_status": "enabled",
                "is_enabled": True,
                "priority_override": 8,
                "config_override": {"scope": "data"},
                "updated_at": None,
            }
        ]

    monkeypatch.setattr(SkillService, "list_user_skill_bindings", classmethod(_fake_list))

    response = user_skill_client.get("/api/v1/user-skills")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["user_id"] == 1901
    assert payload[0]["effective_version"] == "v2"
    assert captured["user_id"] == 1901
    assert captured["skill_id"] is None


def test_user_skill_patch_should_bind_current_user(user_skill_client: TestClient, monkeypatch) -> None:  # noqa: ANN001
    """PATCH 应使用当前用户上下文并透传更新参数。"""

    captured = {}

    def _fake_list(cls, db, user_id=None, skill_id=None, binding_status=None):  # noqa: ANN001
        _ = cls, db, binding_status
        if user_id != 1901 or skill_id != "loan-advice":
            return []
        return [
            {
                "user_id": user_id,
                "skill_id": skill_id,
                "version": "v2",
                "binding_status": "enabled",
                "is_enabled": True,
                "priority_override": 12,
                "config_override": {"scope": "data"},
                "updated_at": None,
            }
        ]

    def _fake_bind(  # noqa: ANN001
        cls,
        db,
        user_id: int,
        skill_id: str,
        version: str,
        is_enabled: bool,
        priority_override,
        config_override,
    ):
        captured["db"] = db
        captured["user_id"] = user_id
        captured["skill_id"] = skill_id
        captured["version"] = version
        captured["is_enabled"] = is_enabled
        captured["priority_override"] = priority_override
        captured["config_override"] = config_override
        return {
            "user_id": user_id,
            "skill_id": skill_id,
            "version": version,
            "binding_status": "enabled",
            "is_enabled": is_enabled,
            "priority_override": priority_override,
            "config_override": config_override,
        }

    monkeypatch.setattr(SkillService, "list_user_skill_bindings", classmethod(_fake_list))
    monkeypatch.setattr(SkillService, "bind_user_skill", classmethod(_fake_bind))

    response = user_skill_client.patch(
        "/api/v1/user-skills/loan-advice",
        json={
            "is_enabled": False,
            "priority_override": 99,
            "config_override": {"scope": "todo"},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["user_id"] == 1901
    assert payload["version"] == "v2"
    assert payload["is_enabled"] is False
    assert captured["user_id"] == 1901
    assert captured["skill_id"] == "loan-advice"
    assert captured["version"] == "v2"
    assert captured["priority_override"] == 99
    assert captured["config_override"] == {"scope": "todo"}


def test_user_skill_patch_should_return_400_when_service_rejects(user_skill_client: TestClient, monkeypatch) -> None:  # noqa: ANN001
    """绑定服务校验失败时应返回 400。"""

    monkeypatch.setattr(SkillService, "list_user_skill_bindings", classmethod(lambda cls, db, **kwargs: []))

    def _raise_invalid(cls, **kwargs):  # noqa: ANN001
        _ = kwargs
        raise ValueError("版本不存在")

    monkeypatch.setattr(SkillService, "bind_user_skill", classmethod(_raise_invalid))

    response = user_skill_client.patch(
        "/api/v1/user-skills/loan-advice",
        json={"version": "v9", "is_enabled": True},
    )

    assert response.status_code == 400
    assert "版本不存在" in response.json()["detail"]


def test_user_skill_reset_should_scope_to_current_user(user_skill_client: TestClient, monkeypatch) -> None:  # noqa: ANN001
    """reset 接口应仅回滚当前用户绑定。"""

    captured = {}

    def _fake_reset(cls, db, user_id: int, skill_id: str):  # noqa: ANN001
        captured["db"] = db
        captured["user_id"] = user_id
        captured["skill_id"] = skill_id
        return {
            "user_id": user_id,
            "skill_id": skill_id,
            "rolled_back_version": "v2",
            "binding_status": "rollbacked",
        }

    monkeypatch.setattr(SkillService, "rollback_user_skill_binding", classmethod(_fake_reset))

    response = user_skill_client.post("/api/v1/user-skills/loan-advice/reset")

    assert response.status_code == 200
    payload = response.json()
    assert payload["user_id"] == 1901
    assert payload["binding_status"] == "rollbacked"
    assert captured["user_id"] == 1901
    assert captured["skill_id"] == "loan-advice"
