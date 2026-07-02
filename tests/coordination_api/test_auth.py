import os
import tempfile

import pytest
from fastapi.testclient import TestClient

from services.coordination_api.config import Settings
from services.coordination_api.main import app
from services.coordination_api.database import run_migrations


@pytest.fixture(autouse=True)
def _db():
    tmp = tempfile.mktemp(suffix=".db")
    os.environ["COORDINATION_DB_PATH"] = tmp
    run_migrations(tmp)
    yield
    del os.environ["COORDINATION_DB_PATH"]
    try:
        os.remove(tmp)
    except PermissionError:
        pass


@pytest.fixture
def client():
    return TestClient(app)


class TestAuthRequiredMode:
    @pytest.fixture(autouse=True)
    def _enable_auth(self):
        import services.coordination_api.main as m

        original = m.settings
        m.settings = Settings(
            host="127.0.0.1",
            port=8000,
            api_keys=["test-key-1", "test-key-2"],
            db_path=os.environ.get("COORDINATION_DB_PATH", "coordination.db"),
        )
        yield
        m.settings = original

    def test_health_requires_valid_key(self, client):
        resp = client.get("/health")
        assert resp.status_code == 401

    def test_health_accepted_with_valid_key(self, client):
        resp = client.get("/health", headers={"X-API-Key": "test-key-1"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_health_rejected_with_invalid_key(self, client):
        resp = client.get("/health", headers={"X-API-Key": "wrong-key"})
        assert resp.status_code == 401

    def test_health_accepted_with_any_valid_key(self, client):
        resp = client.get("/health", headers={"X-API-Key": "test-key-2"})
        assert resp.status_code == 200

    def test_api_endpoint_requires_valid_key(self, client):
        resp = client.post("/tasks/nonexistent/claim", json={"agent_id": "agent-01"})
        assert resp.status_code == 401


class TestAuthDisabledMode:
    @pytest.fixture(autouse=True)
    def _disable_auth(self):
        import services.coordination_api.main as m

        original = m.settings
        m.settings = Settings(
            host="127.0.0.1",
            port=8000,
            api_keys=[],
            db_path=os.environ.get("COORDINATION_DB_PATH", "coordination.db"),
        )
        yield
        m.settings = original

    def test_health_without_key_when_disabled(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_health_with_any_key_when_disabled(self, client):
        resp = client.get("/health", headers={"X-API-Key": "anything"})
        assert resp.status_code == 200

    def test_api_endpoint_without_key_when_disabled(self, client):
        resp = client.post("/tasks/nonexistent/claim", json={"agent_id": "agent-01"})
        assert resp.status_code != 401


class TestSettingsDefaultValues:
    def test_default_db_path(self, monkeypatch):
        monkeypatch.delenv("COORDINATION_DB_PATH", raising=False)
        s = Settings()
        assert s.db_path == "coordination.db"

    def test_default_host(self):
        s = Settings()
        assert s.host == "127.0.0.1"

    def test_default_port(self):
        s = Settings()
        assert s.port == 8000

    def test_default_base_url(self):
        s = Settings()
        assert s.base_url == "http://127.0.0.1:8000"

    def test_auth_disabled_by_default(self):
        s = Settings()
        assert s.is_api_key_required is False

    def test_auth_required_when_keys_set(self):
        s = Settings(api_keys=["key-1"])
        assert s.is_api_key_required is True
