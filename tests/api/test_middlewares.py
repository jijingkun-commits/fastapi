"""中间件测试：验证请求ID生成与透传，以及耗时头。"""
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_correlation_id_generated():
    """未提供请求ID时，中间件应生成并回写到响应头。"""
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert "X-Request-ID" in r.headers
    assert r.headers["X-Request-ID"]


def test_correlation_id_propagates():
    """提供请求ID时，应透传并保持一致。"""
    r = client.get("/api/v1/health", headers={"X-Request-ID": "abc123"})
    assert r.status_code == 200
    assert r.headers.get("X-Request-ID") == "abc123"


def test_process_time_header_present():
    """响应头包含耗时信息，单位为毫秒。"""
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert "X-Process-Time" in r.headers
    assert r.headers["X-Process-Time"].endswith("ms")
