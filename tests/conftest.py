"""
tests/conftest.py
──────────────────
Top-level pytest configuration.

Provides shared fixtures available to all test modules:
  - env_patch:  injects minimal environment variables so that Settings()
                can be constructed without a real .env file
"""

import os
import pytest

_MIN_ENV = {
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


@pytest.fixture(autouse=True)
def env_patch(monkeypatch):
    """
    Inject the minimum required environment variables into every test.
    Clears the lru_cache on shared.config.get_settings before and after.
    """
    from shared.config import get_settings
    get_settings.cache_clear()
    for k, v in _MIN_ENV.items():
        monkeypatch.setenv(k, v)
    yield
    get_settings.cache_clear()
