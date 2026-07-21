"""
tests/agent2/test_baseline_comparator.py
──────────────────────────────────────────
Unit tests for agent2.app.services.baseline_comparator.

The Presto execute_query call is mocked so no IBM Cloud connectivity is needed.
"""

from unittest.mock import patch

import pytest

from agent2.app.models.response import BaselineSnapshot
from agent2.app.services.baseline_comparator import load_baseline
from shared.exceptions import BaselineNotFoundError


def _make_settings():
    from shared.config import Settings

    return Settings(
        ibm_cloud_api_key="test",
        watsonx_project_id="proj",
        wxdata_presto_url="https://presto.test",
        wxdata_auth_token="tok",
        wxgov_url="https://gov.test",
        wxgov_space_id="sp",
        cos_api_key="cosk",
        cos_instance_id="cosi",
        secrets_manager_url="https://sm.test",
        secrets_manager_instance_id="smi",
    )


_MOCK_BASELINE_ROWS = [
    {
        "category": "folders",
        "expected_value": "C:\\inetpub\\wwwroot",
        "control_ref": "CIS-1.1",
    },
    {
        "category": "service_accounts",
        "expected_value": "svc_iis",
        "control_ref": "CIS-4.1",
    },
    {
        "category": "local_groups",
        "expected_value": "Administrators",
        "control_ref": "CIS-2.1",
    },
]


class TestLoadBaseline:
    def test_returns_baseline_snapshot(self):
        settings = _make_settings()
        with patch(
            "agent2.app.services.baseline_comparator.execute_query",
            return_value=_MOCK_BASELINE_ROWS,
        ):
            snapshot = load_baseline(settings, server_class="web-server")

        assert isinstance(snapshot, BaselineSnapshot)
        assert snapshot.server_class == "web-server"

    def test_folders_populated(self):
        settings = _make_settings()
        with patch(
            "agent2.app.services.baseline_comparator.execute_query",
            return_value=_MOCK_BASELINE_ROWS,
        ):
            snapshot = load_baseline(settings, server_class="web-server")

        assert "C:\\inetpub\\wwwroot" in snapshot.folders

    def test_service_accounts_populated(self):
        settings = _make_settings()
        with patch(
            "agent2.app.services.baseline_comparator.execute_query",
            return_value=_MOCK_BASELINE_ROWS,
        ):
            snapshot = load_baseline(settings, server_class="web-server")

        assert "svc_iis" in snapshot.service_accounts

    def test_empty_result_raises_baseline_not_found(self):
        settings = _make_settings()
        with patch(
            "agent2.app.services.baseline_comparator.execute_query",
            return_value=[],
        ):
            with pytest.raises(BaselineNotFoundError):
                load_baseline(settings, server_class="nonexistent-class")
