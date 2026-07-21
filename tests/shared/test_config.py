"""
tests/shared/test_config.py
────────────────────────────
Unit tests for shared.config — settings loading and lru_cache behaviour.
"""

import os
from unittest.mock import patch

import pytest

# Provide minimum required env vars before importing settings
_BASE_ENV = {
    "IBM_CLOUD_API_KEY": "test-key",
    "WATSONX_PROJECT_ID": "test-project",
    "WXDATA_PRESTO_URL": "https://presto.test",
    "WXDATA_AUTH_TOKEN": "wxdata-token",
    "WXGOV_URL": "https://gov.test",
    "WXGOV_SPACE_ID": "space-1",
    "COS_API_KEY": "cos-key",
    "COS_INSTANCE_ID": "cos-instance",
    "SECRETS_MANAGER_URL": "https://sm.test",
    "SECRETS_MANAGER_INSTANCE_ID": "sm-instance",
}


def _make_settings():
    # Import inside function to avoid module-level lru_cache poisoning
    from shared.config import Settings
    return Settings(**{k.lower(): v for k, v in _BASE_ENV.items()})


def test_defaults_applied():
    s = _make_settings()
    assert s.ibm_cloud_region == "us-south"
    assert s.watsonx_model_chat == "ibm/granite-13b-chat-v2"
    assert s.watsonx_model_code == "ibm/granite-34b-code-instruct-v1"
    assert s.log_level == "INFO"
    assert s.environment == "production"


def test_required_fields_present():
    s = _make_settings()
    assert s.ibm_cloud_api_key == "test-key"
    assert s.watsonx_project_id == "test-project"
    assert s.wxdata_presto_url == "https://presto.test"
    assert s.wxgov_url == "https://gov.test"


def test_missing_required_field_raises():
    from pydantic_settings import BaseSettings
    from shared.config import Settings
    env = {k.lower(): v for k, v in _BASE_ENV.items()}
    del env["watsonx_project_id"]
    with pytest.raises(Exception):
        Settings(**env)


def test_agent2_defaults():
    s = _make_settings()
    assert s.winrm_transport == "ntlm"
    assert s.winrm_port == 5985
    assert s.ps_syntax_check is True


def test_get_settings_returns_singleton():
    """get_settings() must return the same object on repeated calls."""
    from shared.config import get_settings
    # Clear the lru_cache from any previous test run
    get_settings.cache_clear()
    with patch.dict(os.environ, _BASE_ENV, clear=False):
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2
    get_settings.cache_clear()
