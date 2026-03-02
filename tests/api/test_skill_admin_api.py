"""Skill 管理 API 测试（用户绑定与回滚）。"""

from typing import Generator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.endpoints.skill_admin_api import router as skill_admin_router
from app.db.session import get_db
from app.repositories import config_repo
from app.services.skill_service import SkillService


@pytest.fixture
def skill_admin_client() -> Generator[TestClient, None, None]:
    """构造仅挂载 skill-admin 路由的测试客户端。"""

    app = FastAPI()
    app.include_router(skill_admin_router, prefix="/api/v1")

    class _FakeDB:
        def commit(self) -> None:
            return None

    def _override_get_db():
        yield _FakeDB()

    app.dependency_overrides[get_db] = _override_get_db

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


def test_binding_endpoint_should_bind_user_skill(skill_admin_client: TestClient, monkeypatch) -> None:  # noqa: ANN001
    """绑定接口应透传参数并返回绑定结果。"""

    captured: dict = {}

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
        }

    monkeypatch.setattr(SkillService, "bind_user_skill", classmethod(_fake_bind))

    response = skill_admin_client.post(
        "/api/v1/skill-admin/bindings",
        json={
            "user_id": 3101,
            "skill_id": "loan-advice",
            "version": "v2",
            "is_enabled": True,
            "priority_override": 20,
            "config_override": {"scope": "data"},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["binding_status"] == "enabled"
    assert captured["user_id"] == 3101
    assert captured["skill_id"] == "loan-advice"
    assert captured["version"] == "v2"


def test_binding_endpoint_should_return_409_when_binding_disabled(skill_admin_client: TestClient, monkeypatch) -> None:  # noqa: ANN001
    """绑定开关关闭时接口应返回 409。"""

    def _raise_disabled(cls, **kwargs):  # noqa: ANN001
        _ = kwargs
        raise RuntimeError("ENABLE_USER_SKILL_BINDING 未开启")

    monkeypatch.setattr(SkillService, "bind_user_skill", classmethod(_raise_disabled))

    response = skill_admin_client.post(
        "/api/v1/skill-admin/bindings",
        json={
            "user_id": 3102,
            "skill_id": "loan-advice",
            "version": "v1",
        },
    )

    assert response.status_code == 409
    assert "ENABLE_USER_SKILL_BINDING" in response.json()["detail"]


def test_binding_rollback_endpoint_should_return_payload(skill_admin_client: TestClient, monkeypatch) -> None:  # noqa: ANN001
    """绑定回滚接口应返回回滚结果。"""

    def _fake_rollback(cls, db, user_id: int, skill_id: str):  # noqa: ANN001
        _ = db
        return {
            "user_id": user_id,
            "skill_id": skill_id,
            "rolled_back_version": "v2",
            "binding_status": "rollbacked",
        }

    monkeypatch.setattr(SkillService, "rollback_user_skill_binding", classmethod(_fake_rollback))

    response = skill_admin_client.post(
        "/api/v1/skill-admin/bindings/rollback",
        json={"user_id": 3103, "skill_id": "loan-advice"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["binding_status"] == "rollbacked"
    assert payload["rolled_back_version"] == "v2"


def test_binding_rollback_endpoint_should_return_404_when_not_found(skill_admin_client: TestClient, monkeypatch) -> None:  # noqa: ANN001
    """绑定不存在时回滚接口应返回 404。"""

    def _raise_not_found(cls, **kwargs):  # noqa: ANN001
        _ = kwargs
        raise ValueError("用户绑定不存在")

    monkeypatch.setattr(SkillService, "rollback_user_skill_binding", classmethod(_raise_not_found))

    response = skill_admin_client.post(
        "/api/v1/skill-admin/bindings/rollback",
        json={"user_id": 3104, "skill_id": "loan-advice"},
    )

    assert response.status_code == 404
    assert "用户绑定不存在" in response.json()["detail"]


def test_version_rollback_endpoint_should_delegate_service(skill_admin_client: TestClient, monkeypatch) -> None:  # noqa: ANN001
    """版本回滚接口应透传 target_version 并返回结果。"""

    captured: dict = {}

    def _fake_version_rollback(cls, db, skill_id: str, target_version=None):  # noqa: ANN001
        captured["skill_id"] = skill_id
        captured["target_version"] = target_version
        _ = db
        return {
            "skill_id": skill_id,
            "active_version": "v1",
            "rolled_back_from": "v2",
        }

    monkeypatch.setattr(SkillService, "rollback_skill_version", classmethod(_fake_version_rollback))

    response = skill_admin_client.post(
        "/api/v1/skill-admin/skills/loan-advice/versions/rollback",
        json={"target_version": "v1"},
    )

    assert response.status_code == 200
    assert response.json()["active_version"] == "v1"
    assert captured["skill_id"] == "loan-advice"
    assert captured["target_version"] == "v1"


def test_version_rollback_endpoint_should_return_400_on_invalid_target(skill_admin_client: TestClient, monkeypatch) -> None:  # noqa: ANN001
    """版本回滚参数非法时接口应返回 400。"""

    def _raise_invalid(cls, **kwargs):  # noqa: ANN001
        _ = kwargs
        raise ValueError("target_version 非法")

    monkeypatch.setattr(SkillService, "rollback_skill_version", classmethod(_raise_invalid))

    response = skill_admin_client.post(
        "/api/v1/skill-admin/skills/loan-advice/versions/rollback",
        json={"target_version": ""},
    )

    assert response.status_code in {400, 422}


def test_bootstrap_template_get_should_return_template(skill_admin_client: TestClient, monkeypatch) -> None:  # noqa: ANN001
    """模板读取接口应返回当前归一化模板。"""

    monkeypatch.setattr(
        "app.api.v1.endpoints.skill_admin_api.load_bootstrap_template_from_config",
        lambda: {
            "default_version": "v1",
            "skills": [
                {
                    "skill_id": "loan-advice",
                    "version": "v2",
                    "enabled": True,
                    "priority_override": 10,
                    "config_override": {"scope": "data"},
                }
            ],
        },
    )

    response = skill_admin_client.get("/api/v1/skill-admin/bootstrap-template")

    assert response.status_code == 200
    payload = response.json()
    assert payload["default_version"] == "v1"
    assert payload["skills"][0]["skill_id"] == "loan-advice"


def test_bootstrap_template_put_should_persist_json(skill_admin_client: TestClient, monkeypatch) -> None:  # noqa: ANN001
    """模板更新接口应写入 system config。"""

    captured = {}

    monkeypatch.setattr(
        "app.api.v1.endpoints.skill_admin_api.normalize_bootstrap_template",
        lambda raw: {
            "default_version": "v3",
            "skills": [
                {"skill_id": "loan-advice", "version": "v3", "enabled": True, "priority_override": 9, "config_override": {}}
            ],
        },
    )

    def _fake_upsert(db, key, value, value_type="string", category=None, description=None):  # noqa: ANN001
        captured["db"] = db
        captured["key"] = key
        captured["value"] = value
        captured["value_type"] = value_type
        captured["category"] = category
        captured["description"] = description
        return object()

    monkeypatch.setattr(config_repo, "upsert_config", _fake_upsert)

    response = skill_admin_client.put(
        "/api/v1/skill-admin/bootstrap-template",
        json={
            "default_version": "v3",
            "skills": [{"skill_id": "loan-advice", "version": "v3"}],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["default_version"] == "v3"
    assert captured["key"] == SkillService.USER_BOOTSTRAP_TEMPLATE_KEY
    assert captured["value_type"] == "json"


def test_bootstrap_template_sync_should_skip_existing_bindings(skill_admin_client: TestClient, monkeypatch) -> None:  # noqa: ANN001
    """模板同步接口默认仅补齐缺失绑定。"""

    bind_calls = []

    monkeypatch.setattr(
        "app.api.v1.endpoints.skill_admin_api.load_bootstrap_template_from_config",
        lambda: {
            "default_version": "v1",
            "skills": [
                {"skill_id": "loan-advice", "version": "v2", "enabled": True, "priority_override": 8, "config_override": {}},
                {"skill_id": "risk-check", "version": "v1", "enabled": True, "priority_override": 12, "config_override": {}},
            ],
        },
    )
    monkeypatch.setattr(
        SkillService,
        "list_user_skill_bindings",
        classmethod(
            lambda cls, db, user_id=None, skill_id=None, binding_status=None: [
                {
                    "user_id": user_id,
                    "skill_id": "loan-advice",
                    "version": "v2",
                    "binding_status": "enabled",
                    "is_enabled": True,
                    "priority_override": 8,
                    "config_override": {},
                    "updated_at": None,
                }
            ]
        ),
    )

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
        _ = cls, db, user_id, skill_id, version, is_enabled, priority_override, config_override
        bind_calls.append(skill_id)
        return {"skill_id": skill_id}

    monkeypatch.setattr(SkillService, "bind_user_skill", classmethod(_fake_bind))

    response = skill_admin_client.post("/api/v1/skill-admin/users/3101/sync-template")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2
    assert payload["synced_count"] == 1
    assert payload["skipped_count"] == 1
    assert bind_calls == ["risk-check"]
