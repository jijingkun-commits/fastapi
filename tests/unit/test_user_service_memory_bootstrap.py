"""用户创建时文档记忆初始化测试。"""

from datetime import datetime

from app.schemas.user import UserCreate
from app.services import user_service


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


def _build_create_payload() -> UserCreate:
    return UserCreate(
        username="alice",
        password="123456",
        mobile="13800000000",
    )


def test_create_user_seeds_document_memory_when_feature_enabled(monkeypatch):
    """总开关开启时，新用户应执行文档记忆模板初始化。"""

    payload = _build_create_payload()
    seed_calls = []

    monkeypatch.setattr(user_service.user_repo, "get_by_username", lambda db, username: None)
    monkeypatch.setattr(user_service.user_repo, "get_by_mobile", lambda db, mobile: None)
    monkeypatch.setattr("app.services.user_service.hash_password", lambda raw: "hashed")
    monkeypatch.setattr(
        user_service.user_repo,
        "create_user",
        lambda **kwargs: _DummyUser(user_id=21),
    )
    monkeypatch.setattr("app.services.user_service._is_document_memory_enabled", lambda: True)

    def _fake_bootstrap(db, *, user_id):
        seed_calls.append(user_id)
        return 1

    monkeypatch.setattr("app.services.user_service.bootstrap_preference_documents", _fake_bootstrap)

    user_item, error = user_service.create_user(db=object(), data=payload)

    assert error is None
    assert user_item is not None
    assert user_item.id == 21
    assert seed_calls == [21]


def test_create_user_skips_document_memory_when_feature_disabled(monkeypatch):
    """总开关关闭时，新用户不应触发文档记忆模板初始化。"""

    payload = _build_create_payload()

    monkeypatch.setattr(user_service.user_repo, "get_by_username", lambda db, username: None)
    monkeypatch.setattr(user_service.user_repo, "get_by_mobile", lambda db, mobile: None)
    monkeypatch.setattr("app.services.user_service.hash_password", lambda raw: "hashed")
    monkeypatch.setattr(
        user_service.user_repo,
        "create_user",
        lambda **kwargs: _DummyUser(user_id=22),
    )
    monkeypatch.setattr("app.services.user_service._is_document_memory_enabled", lambda: False)
    monkeypatch.setattr(
        "app.services.user_service.bootstrap_preference_documents",
        lambda db, *, user_id: (_ for _ in ()).throw(AssertionError("should not be called")),
    )

    user_item, error = user_service.create_user(db=object(), data=payload)

    assert error is None
    assert user_item is not None
    assert user_item.id == 22
