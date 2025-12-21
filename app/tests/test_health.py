from fastapi.testclient import TestClient

from app.main import app
from app.db.session import get_db


client = TestClient(app)


def test_health_db_ok(monkeypatch):
    class DummySession:
        def execute(self, stmt):
            return [1]

    def override_get_db():
        yield DummySession()

    app.dependency_overrides[get_db] = override_get_db
    r = client.get("/api/v1/health/db")
    app.dependency_overrides.clear()
    assert r.status_code == 200
    assert r.json()["db"] is True


def test_health_pool_structure():
    r = client.get("/api/v1/health/pool")
    assert r.status_code == 200
    data = r.json()
    assert "pool" in data
    pool = data["pool"]
    assert "size" in pool and "checked_out" in pool and "overflow" in pool
