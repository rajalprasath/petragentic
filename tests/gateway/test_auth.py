"""
tests/gateway/test_auth.py
───────────────────────────
Unit tests for gateway.app.auth — JWT validation and scope enforcement.

All JWKS HTTP calls are mocked; tests do not touch IBM App ID.
"""

from unittest.mock import patch

import pytest
from fastapi import HTTPException
from jose import jwt

from gateway.app.auth import _decode_token, require_scope
from gateway.app.config import GatewaySettings


def _make_gateway_settings(**overrides) -> GatewaySettings:
    base = dict(
        appid_issuer_url="https://us-south.appid.cloud.ibm.com/oauth/v4/test-tenant",
        appid_jwks_url="https://us-south.appid.cloud.ibm.com/oauth/v4/test-tenant/publickeys",
        appid_audience="test-client-id",
    )
    base.update(overrides)
    return GatewaySettings(**base)


class TestDecodeToken:
    def test_invalid_token_raises_401(self):
        settings = _make_gateway_settings()
        fake_keys = [{"kty": "RSA", "kid": "1", "n": "abc", "e": "AQAB"}]
        with patch("gateway.app.auth._get_jwks", return_value=fake_keys):
            with pytest.raises(HTTPException) as exc_info:
                _decode_token("not.a.valid.jwt", settings)
            assert exc_info.value.status_code == 401

    def test_jwks_fetch_failure_raises_503(self):
        settings = _make_gateway_settings()
        with patch("gateway.app.auth._get_jwks", side_effect=ConnectionError("no network")):
            with pytest.raises(HTTPException) as exc_info:
                _decode_token("any.token.here", settings)
            assert exc_info.value.status_code == 503


class TestRequireScope:
    def test_missing_scope_raises_403(self):
        """A token that carries only 'design:read' should fail when 'design:write' is needed."""
        user_claims = {"sub": "user123", "scope": "design:read"}
        checker = require_scope("design:write")

        with pytest.raises(HTTPException) as exc_info:
            checker(user=user_claims)
        assert exc_info.value.status_code == 403

    def test_present_scope_passes(self):
        user_claims = {"sub": "user123", "scope": "design:read design:write"}
        checker = require_scope("design:write")
        result = checker(user=user_claims)
        assert result == user_claims

    def test_empty_scope_raises_403(self):
        user_claims = {"sub": "user123", "scope": ""}
        checker = require_scope("audit:read")
        with pytest.raises(HTTPException) as exc_info:
            checker(user=user_claims)
        assert exc_info.value.status_code == 403
