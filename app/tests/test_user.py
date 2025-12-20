import types
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import get_db


client = TestClient(app)


def test_health():
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_login_requires_identifier():
    r = client.post("/api/v1/login", json={"password": "x"})
    assert r.status_code == 400


def test_login_success_with_mock(monkeypatch):
    # 模拟认证通过
    from app.api.v1.endpoints import auth as auth_module

    class DummyUser:
        id = 1

    monkeypatch.setattr(auth_module, "authenticate", lambda db, u, m, p: DummyUser())
    # 覆盖数据库依赖，避免实际连接
    app.dependency_overrides[get_db] = lambda: iter([None])
    r = client.post("/api/v1/login", json={"username": "admin", "password": "secret"})
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
