"""
tests/agent1/test_recommender.py
──────────────────────────────────
Unit tests for agent1.app.services.recommender.

All external I/O (watsonx.data, governance) is mocked so the suite runs
without any IBM Cloud connectivity.
"""

from unittest.mock import MagicMock, patch

import pytest

from agent1.app.models.response import ApprovedTool
from agent1.app.services.recommender import recommend_tools


def _make_settings():
    """Return a minimal Settings object for Agent 1 tests."""
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


# ── Helpers ────────────────────────────────────────────────────────────────────

_MOCK_CATALOGUE_ROWS = [
    {"tool": "IBM Redwood", "usage_count": 10},
    {"tool": "webMethods", "usage_count": 5},
]


class TestRecommendTools:
    def test_returns_list_of_approved_tools(self):
        settings = _make_settings()
        with (
            patch(
                "agent1.app.services.recommender.execute_query",
                return_value=_MOCK_CATALOGUE_ROWS,
            ),
            patch(
                "agent1.app.services.recommender.check_tool_approval",
                return_value=True,
            ),
        ):
            result = recommend_tools(settings, "batch file transfer")

        assert isinstance(result, list)
        assert len(result) > 0
        # Every entry must be a valid ApprovedTool
        for item in result:
            assert item in ApprovedTool.__members__.values()

    def test_governance_block_removes_tool(self):
        """A tool that fails governance check must be excluded from results."""
        settings = _make_settings()

        def _fake_approval(settings, tool_name):
            # Block IBM Redwood
            return tool_name != "IBM Redwood"

        with (
            patch(
                "agent1.app.services.recommender.execute_query",
                return_value=_MOCK_CATALOGUE_ROWS,
            ),
            patch(
                "agent1.app.services.recommender.check_tool_approval",
                side_effect=_fake_approval,
            ),
        ):
            result = recommend_tools(settings, "batch file transfer")

        tool_names = [t.value for t in result]
        assert "IBM Redwood" not in tool_names

    def test_empty_catalogue_returns_defaults(self):
        """When no usage data exists, all approved tools should be returned."""
        settings = _make_settings()
        with (
            patch(
                "agent1.app.services.recommender.execute_query",
                return_value=[],
            ),
            patch(
                "agent1.app.services.recommender.check_tool_approval",
                return_value=True,
            ),
        ):
            result = recommend_tools(settings, "REST API integration")

        assert len(result) > 0
