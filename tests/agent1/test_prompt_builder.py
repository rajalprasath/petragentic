"""
tests/agent1/test_prompt_builder.py
─────────────────────────────────────
Unit tests for agent1.app.services.prompt_builder.

Validates that the built prompt contains all required sections and that
key request parameters are embedded in the output.
"""

import pytest

from agent1.app.models.request import DesignRequest, IntegrationPattern
from agent1.app.models.response import ApprovedTool
from agent1.app.services.prompt_builder import build_design_prompt


def _make_request(**kwargs) -> DesignRequest:
    defaults = dict(
        requirements="Send daily sales CSV from ERP to data warehouse",
        source_system="SAP ECC",
        target_system="IBM Db2 Warehouse",
        integration_pattern=IntegrationPattern.BATCH,
        data_volume_gb=2.5,
        sla_minutes=60,
    )
    defaults.update(kwargs)
    return DesignRequest(**defaults)


class TestBuildDesignPrompt:
    def test_prompt_is_non_empty_string(self):
        req = _make_request()
        candidates = [ApprovedTool.IBM_REDWOOD, ApprovedTool.WEBMETHODS]
        prompt = build_design_prompt(req, candidates, template_version="v1.0")
        assert isinstance(prompt, str)
        assert len(prompt) > 100

    def test_requirements_included_in_prompt(self):
        req = _make_request()
        candidates = [ApprovedTool.IBM_REDWOOD]
        prompt = build_design_prompt(req, candidates, template_version="v1.0")
        assert "daily sales CSV" in prompt

    def test_source_and_target_systems_included(self):
        req = _make_request()
        candidates = [ApprovedTool.IBM_REDWOOD]
        prompt = build_design_prompt(req, candidates, template_version="v1.0")
        assert "SAP ECC" in prompt
        assert "IBM Db2 Warehouse" in prompt

    def test_candidate_tools_listed_in_prompt(self):
        req = _make_request()
        candidates = [ApprovedTool.IBM_REDWOOD, ApprovedTool.WEBMETHODS]
        prompt = build_design_prompt(req, candidates, template_version="v1.0")
        assert "IBM Redwood" in prompt or ApprovedTool.IBM_REDWOOD.value in prompt

    def test_json_output_schema_section_present(self):
        req = _make_request()
        candidates = [ApprovedTool.IBM_REDWOOD]
        prompt = build_design_prompt(req, candidates, template_version="v1.0")
        # The prompt must instruct the LLM to output JSON
        assert "JSON" in prompt or "json" in prompt.lower()

    def test_batch_pattern_reflected(self):
        req = _make_request(integration_pattern=IntegrationPattern.BATCH)
        candidates = [ApprovedTool.IBM_REDWOOD]
        prompt = build_design_prompt(req, candidates, template_version="v1.0")
        assert "batch" in prompt.lower()
