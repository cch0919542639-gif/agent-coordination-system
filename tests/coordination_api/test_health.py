from fastapi.testclient import TestClient

from services.coordination_api.main import app

client = TestClient(app)


class TestHealthEndpoint:
    def test_health_returns_ok(self) -> None:
        response = client.get("/health")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert body["version"] == "0.1.0"

    def test_health_without_api_key(self) -> None:
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_accepts_unknown_api_key_when_disabled(self) -> None:
        response = client.get("/health", headers={"X-API-Key": "anything"})
        assert response.status_code == 200
