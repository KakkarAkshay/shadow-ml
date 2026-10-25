from fastapi.testclient import TestClient

from app.main import app


def test_health():
    with TestClient(app) as client:
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


def test_classify_returns_label():
    with TestClient(app) as client:
        r = client.post("/api/classify", json={"text": "What's a good recipe for pasta tonight?"})
        assert r.status_code == 200
        body = r.json()
        assert "label" in body and "confidence" in body


def test_classify_rejects_empty_text():
    with TestClient(app) as client:
        r = client.post("/api/classify", json={"text": "   "})
        assert r.status_code == 400
