from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_llm_stream_sse():
    r = client.post("/api/v1/llm/stream", json={"prompt": "a b c", "delay_ms": 1})
    assert r.status_code == 200
    text = r.text
    assert "data: a" in text
    assert "data: b" in text
    assert "data: c" in text
    assert "event: done" in text

