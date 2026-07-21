"""
tests/shared/test_exceptions.py
────────────────────────────────
Unit tests for shared.exceptions — hierarchy, status codes, and detail dicts.
"""

import pytest

from shared.exceptions import (
    BaselineNotFoundError,
    CatalogueStoreError,
    COSUploadError,
    DesignGenerationError,
    GovernanceCheckError,
    PetragenticError,
    PowerShellSyntaxError,
    RemediationGenerationError,
    ReportRenderError,
    WatsonxInferenceError,
    WatsonxParseError,
    WatsonxQuotaError,
    WinRMCommandError,
    WinRMConnectionError,
    WxDataInsertError,
    WxDataQueryError,
)


class TestBaseException:
    def test_is_exception(self):
        err = PetragenticError("boom")
        assert isinstance(err, Exception)

    def test_defaults(self):
        err = PetragenticError("msg")
        assert err.status_code == 500
        assert err.detail == {}
        assert err.message == "msg"

    def test_custom_status_and_detail(self):
        err = PetragenticError("x", status_code=404, detail={"k": "v"})
        assert err.status_code == 404
        assert err.detail == {"k": "v"}


class TestWatsonxErrors:
    def test_inference_error(self):
        err = WatsonxInferenceError("failed", model_id="granite-13b")
        assert err.status_code == 502
        assert err.detail["model_id"] == "granite-13b"

    def test_quota_error(self):
        err = WatsonxQuotaError()
        assert err.status_code == 429

    def test_parse_error_preview(self):
        err = WatsonxParseError("bad json", raw_output="x" * 500)
        assert err.status_code == 502
        assert len(err.detail["raw_output_preview"]) <= 300


class TestWxDataErrors:
    def test_query_error(self):
        err = WxDataQueryError("select failed", query="SELECT * FROM foo")
        assert err.status_code == 502
        assert "SELECT" in err.detail["query_preview"]

    def test_insert_error(self):
        err = WxDataInsertError("my_table", "constraint violation")
        assert err.status_code == 502
        assert err.detail["table"] == "my_table"
        assert "my_table" in err.message


class TestGovernanceError:
    def test_governance_check(self):
        err = GovernanceCheckError("IBM Redwood", "pending")
        assert err.status_code == 422
        assert err.detail["tool"] == "IBM Redwood"
        assert err.detail["governance_status"] == "pending"


class TestCOSError:
    def test_cos_upload_error(self):
        err = COSUploadError("my-bucket", "reports/r1.json")
        assert err.status_code == 502
        assert "my-bucket" in err.message


class TestWinRMErrors:
    def test_connection_error(self):
        err = WinRMConnectionError("10.0.0.1", reason="timeout")
        assert err.status_code == 502
        assert err.detail["host"] == "10.0.0.1"
        assert err.detail["reason"] == "timeout"

    def test_command_error(self):
        err = WinRMCommandError("srv01", "Get-LocalGroup")
        assert err.status_code == 502
        assert err.detail["host"] == "srv01"

    def test_powershell_syntax_error(self):
        err = PowerShellSyntaxError("Invoke-Bad")
        assert err.status_code == 500
        assert "Invoke-Bad" in err.detail["script_preview"]


class TestAgent1Errors:
    def test_design_generation_error(self):
        err = DesignGenerationError("LLM returned empty")
        assert err.status_code == 500

    def test_catalogue_store_error(self):
        err = CatalogueStoreError("DB unreachable")
        assert err.status_code == 500


class TestAgent2Errors:
    def test_baseline_not_found(self):
        err = BaselineNotFoundError("web-server")
        assert err.status_code == 404
        assert err.detail["server_class"] == "web-server"

    def test_report_render_error(self):
        err = ReportRenderError("template not found")
        assert err.status_code == 500

    def test_remediation_generation_error(self):
        err = RemediationGenerationError("finding-001", "timeout")
        assert err.status_code == 500
        assert err.detail["finding_id"] == "finding-001"
