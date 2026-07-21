"""
tests/e2e/test_agent1_api.py
──────────────────────────────
End-to-end smoke tests for Agent 1.

These tests use FastAPI's TestClient (no external network calls) but verify
the full request/response cycle through real middleware and route handlers.
All external IBM Cloud calls (watsonx.ai, watsonx.data, governance) are
mocked at the service layer.

Run with:
    pytest tests/e2e/test_agent1_api.py -v
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Heavy mocks must be in place before the app module is imported
_SHARED_PATCHES = {
    "shared.watsonx_client.generate_text": MagicMock(return_value='{"tool":"IBM Redwood"}'),
    "shared.wxdata_client.execute_query": MagicMock(return_value=[]),
    "shared.governance_logger.check_tool_approval": MagicMock(return_value=True),
    "shared.governance_logger.log_model_usage": MagicMock(),
}


@pytest.fixture(scope="module")
def agent1_client():
    with (
        patch("shared.watsonx_client.generate_text", return_value='{}'),
        patch("shared.wxdata_client.execute_query", return_value=[]),
        patch("shared.governance_logger.check_tool_approval", return_value=True),
        patch("shared.governance_logger.log_model_usage"),
    ):
        from agent1.app.main import app
        client = TestClient(app, raise_server_exceptions=False)
        yield client


class TestAgent1HealthEndpoints:
    def test_health_returns_200(self, agent1_client):
        resp = agent1_client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
        assert resp.json()["service"] == "agent1"

    def test_health_no_auth_required(self, agent1_client):
        """Health endpoint must be accessible without Authorization header."""
        resp = agent1_client.get("/health")
        assert resp.status_code != 401

    def test_ready_endpoint_exists(self, agent1_client):
        resp = agent1_client.get("/ready")
        # May be 200 or 503 depending on probe results — just ensure it responds
        assert resp.status_code in (200, 503)


class TestAgent1DesignEndpoint:
    def test_design_missing_body_returns_422(self, agent1_client):
        resp = agent1_client.post("/design", json={})
        assert resp.status_code == 422

    def test_correlation_id_echoed(self, agent1_client):
        resp = agent1_client.get(
            "/health",
            headers={"X-Correlation-ID": "test-cid-999"},
        )
        assert resp.headers.get("X-Correlation-ID") == "test-cid-999"

    def test_correlation_id_generated_when_absent(self, agent1_client):
        resp = agent1_client.get("/health")
        assert "X-Correlation-ID" in resp.headers
        assert len(resp.headers["X-Correlation-ID"]) > 0
