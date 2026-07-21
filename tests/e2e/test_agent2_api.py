"""
tests/e2e/test_agent2_api.py
──────────────────────────────
End-to-end smoke tests for Agent 2.

Uses FastAPI TestClient; all WinRM, watsonx.ai, and watsonx.data calls mocked.

Run with:
    pytest tests/e2e/test_agent2_api.py -v
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def agent2_client():
    with (
        patch("shared.watsonx_client.generate_text", return_value="# PS1 remediation"),
        patch("shared.wxdata_client.execute_query", return_value=[]),
        patch("shared.governance_logger.check_tool_approval", return_value=True),
        patch("shared.governance_logger.log_model_usage"),
    ):
        from agent2.app.main import app
        client = TestClient(app, raise_server_exceptions=False)
        yield client


class TestAgent2HealthEndpoints:
    def test_health_returns_200(self, agent2_client):
        resp = agent2_client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
        assert resp.json()["service"] == "agent2"

    def test_ready_endpoint_exists(self, agent2_client):
        resp = agent2_client.get("/ready")
        assert resp.status_code in (200, 503)


class TestAgent2ValidateEndpoint:
    def test_validate_missing_body_returns_422(self, agent2_client):
        resp = agent2_client.post("/validate", json={})
        assert resp.status_code == 422

    def test_correlation_id_echoed(self, agent2_client):
        resp = agent2_client.get(
            "/health",
            headers={"X-Correlation-ID": "e2e-cid-42"},
        )
        assert resp.headers.get("X-Correlation-ID") == "e2e-cid-42"


class TestAgent2ReportEndpoint:
    def test_report_not_found_returns_404_or_503(self, agent2_client):
        """A non-existent scan ID should return 404 or 503 — never 500."""
        resp = agent2_client.get("/report/nonexistent-scan-id")
        assert resp.status_code in (404, 503, 422)
