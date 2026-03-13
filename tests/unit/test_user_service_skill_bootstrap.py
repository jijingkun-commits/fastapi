"""用户创建链路的 Skill 模板初始化测试。"""

from datetime import datetime
from typing import Any, Dict, List

from app.schemas.user import UserCreate
import app.services.user_service as user_service
import app.services.skill_bootstrap_service as skill_bootstrap_service


class _DummyUser:
    def __init__(self, user_id: int):
        self.id = user_id
        self.username = "alice"
        self.mobile = "13800000000"
        self.role = "user"
        self.data_role = "staff"
        self.org_code = None
        self.org_name = None
        self.dept_code = None
        self.dept_name = None
        self.is_active = True
        self.create_time = datetime.now()


class _DummySession:
    def __init__(self) -> None:
        self.rollback_count = 0

    def rollback(self) -> None:
        self.rollback_count += 1


def _build_create_payload() -> UserCreate:
    return UserCreate(
        username="alice",
        password="123456",
        mobile="13800000000",
    )


def _stub_user_repo(monkeypatch, user_id: int) -> None:  # noqa: ANN001
    monkeypatch.setattr(user_service.user_repo, "get_by_username", lambda db, username: None)
    monkeypatch.setattr(user_service.user_repo, "get_by_mobile", lambda db, mobile: None)
    monkeypatch.setattr("app.services.user_service.hash_password", lambda raw: "hashed")
    monkeypatch.setattr(
        user_service.user_repo,
        "create_user",
        lambda **kwargs: _DummyUser(user_id=user_id),
    )


def test_create_user_bootstraps_skill_template_when_enabled(monkeypatch) -> None:  # noqa: ANN001
    """总开关开启时，创建用户应触发 Skill 模板初始化。"""

    payload = _build_create_payload()
    bootstrap_calls: List[int] = []
    _stub_user_repo(monkeypatch, user_id=31)
    monkeypatch.setattr("app.services.user_service._is_document_memory_enabled", lambda: False)
    monkeypatch.setattr(
        "app.services.user_service.bootstrap_user_skills",
        lambda db, *, user_id: bootstrap_calls.append(user_id) or 2,
    )

    user_item, error = user_service.create_user(db=_DummySession(), data=payload)

    assert error is None
    assert user_item is not None
    assert user_item.id == 31
    assert bootstrap_calls == [31]


def test_create_user_bootstrap_skill_failure_should_not_block_creation(monkeypatch) -> None:  # noqa: ANN001
    """Skill 初始化失败时不应阻塞创建，且应执行回滚。"""

    payload = _build_create_payload()
    db = _DummySession()
    _stub_user_repo(monkeypatch, user_id=32)
    monkeypatch.setattr("app.services.user_service._is_document_memory_enabled", lambda: False)

    def _raise_bootstrap(db, *, user_id):  # noqa: ANN001
        raise RuntimeError("bootstrap failed")

    monkeypatch.setattr("app.services.user_service.bootstrap_user_skills", _raise_bootstrap)

    user_item, error = user_service.create_user(db=db, data=payload)

    assert error is None
    assert user_item is not None
    assert user_item.id == 32
    assert db.rollback_count == 1


def test_bootstrap_user_skills_should_return_zero_when_flag_resolution_fails(monkeypatch) -> None:  # noqa: ANN001
    """开关解析失败时，应由 bootstrap service 自行降级为不执行。"""

    monkeypatch.setattr(
        skill_bootstrap_service.ConfigResolver,
        "get_bool",
        classmethod(lambda cls, key, default=False: (_ for _ in ()).throw(RuntimeError("config down"))),
    )
    monkeypatch.setattr(
        skill_bootstrap_service.SkillService,
        "bind_user_skill",
        classmethod(lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("should not be called"))),
    )

    seeded = skill_bootstrap_service.bootstrap_user_skills(db=object(), user_id=33)

    assert seeded == 0


def test_bootstrap_user_skills_should_bind_template_entries(monkeypatch) -> None:  # noqa: ANN001
    """模板中的技能项应写入用户绑定。"""

    template_payload = {
        "default_version": "v3",
        "skills": [
            {
                "skill_id": "sql-expert",
                "enabled": True,
                "priority_override": 10,
                "config_override": {"trigger_phrases": ["SQL"]},
            },
            {
                "skill_id": "todo-master",
                "version": "v2",
                "enabled": False,
            },
        ],
    }
    bind_calls: List[Dict[str, Any]] = []

    monkeypatch.setattr(
        skill_bootstrap_service.ConfigResolver,
        "get_bool",
        classmethod(lambda cls, key, default=False: True),
    )
    monkeypatch.setattr(
        skill_bootstrap_service.ConfigResolver,
        "get_json_dict",
        classmethod(lambda cls, key, default=None: template_payload),
    )

    def _fake_bind(  # noqa: ANN001
        cls,
        db,
        user_id,
        skill_id,
        version,
        is_enabled=True,
        priority_override=None,
        config_override=None,
    ):
        bind_calls.append(
            {
                "user_id": user_id,
                "skill_id": skill_id,
                "version": version,
                "is_enabled": is_enabled,
                "priority_override": priority_override,
                "config_override": config_override,
            }
        )
        return {"skill_id": skill_id}

    monkeypatch.setattr(skill_bootstrap_service.SkillService, "bind_user_skill", classmethod(_fake_bind))

    seeded = skill_bootstrap_service.bootstrap_user_skills(db=object(), user_id=9)

    assert seeded == 2
    assert bind_calls[0]["skill_id"] == "sql-expert"
    assert bind_calls[0]["version"] == "v3"
    assert bind_calls[1]["skill_id"] == "todo-master"
    assert bind_calls[1]["version"] == "v2"
    assert bind_calls[1]["is_enabled"] is False


def test_bootstrap_user_skills_should_skip_invalid_template_items(monkeypatch) -> None:  # noqa: ANN001
    """模板项非法时应跳过且不中断后续项。"""

    template_payload = {
        "default_version": "v1",
        "skills": [
            {"skill_id": "   "},
            {"skill_id": "valid-skill", "priority_override": "oops"},
            {"skill_id": "another-skill", "priority_override": 7},
        ],
    }
    bind_calls: List[Dict[str, Any]] = []

    monkeypatch.setattr(
        skill_bootstrap_service.ConfigResolver,
        "get_bool",
        classmethod(lambda cls, key, default=False: True),
    )
    monkeypatch.setattr(
        skill_bootstrap_service.ConfigResolver,
        "get_json_dict",
        classmethod(lambda cls, key, default=None: template_payload),
    )

    def _fake_bind(  # noqa: ANN001
        cls,
        db,
        user_id,
        skill_id,
        version,
        is_enabled=True,
        priority_override=None,
        config_override=None,
    ):
        bind_calls.append(
            {
                "skill_id": skill_id,
                "priority_override": priority_override,
            }
        )
        return {"skill_id": skill_id}

    monkeypatch.setattr(skill_bootstrap_service.SkillService, "bind_user_skill", classmethod(_fake_bind))

    seeded = skill_bootstrap_service.bootstrap_user_skills(db=object(), user_id=10)

    assert seeded == 1
    assert bind_calls == [{"skill_id": "another-skill", "priority_override": 7}]
