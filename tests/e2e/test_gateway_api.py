"""
tests/e2e/test_gateway_api.py
────────────────────────────────
End-to-end smoke tests for the API Gateway.

Uses FastAPI TestClient.  IBM App ID JWKS fetch and JWT decode are mocked
so no real App ID tenant is needed.  The httpx proxy client is also mocked
to avoid needing live agent services.

Run with:
    pytest tests/e2e/test_gateway_api.py -v
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def gateway_client():
    env_overrides = {
        "APPID_ISSUER_URL": "https://us-south.appid.cloud.ibm.com/oauth/v4/test",
        "APPID_JWKS_URL": "https://us-south.appid.cloud.ibm.com/oauth/v4/test/publickeys",
        "APPID_AUDIENCE": "test-client",
    }
    import os
    for k, v in env_overrides.items():
        os.environ[k] = v

    from gateway.app.config import get_settings
    get_settings.cache_clear()

    from gateway.app.main import app
    client = TestClient(app, raise_server_exceptions=False)
    yield client

    get_settings.cache_clear()
    for k in env_overrides:
        os.environ.pop(k, None)


class TestGatewayHealthEndpoints:
    def test_health_unauthenticated(self, gateway_client):
        """Health must respond 200 without any Authorization header."""
        resp = gateway_client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["service"] == "gateway"

    def test_ready_endpoint_exists(self, gateway_client):
        resp = gateway_client.get("/ready")
        assert resp.status_code in (200, 503)


class TestGatewayProtectedRoutes:
    def test_design_without_token_returns_403(self, gateway_client):
        """Routes without Bearer token should get 403 from HTTPBearer."""
        resp = gateway_client.post("/api/v1/design", json={"requirements": "test"})
        assert resp.status_code == 403

    def test_validate_without_token_returns_403(self, gateway_client):
        resp = gateway_client.post("/api/v1/validate", json={"host": "srv01"})
        assert resp.status_code == 403

    def test_catalogue_without_token_returns_403(self, gateway_client):
        resp = gateway_client.get("/api/v1/catalogue/stats")
        assert resp.status_code == 403

    def test_report_without_token_returns_403(self, gateway_client):
        resp = gateway_client.get("/api/v1/report/scan-001")
        assert resp.status_code == 403
