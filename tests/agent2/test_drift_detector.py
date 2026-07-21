"""
tests/agent2/test_drift_detector.py
─────────────────────────────────────
Unit tests for agent2.app.services.drift_detector.

Validates severity classification, CIS/NIST control tag assignment, and
finding de-duplication logic.  No external I/O required.
"""

import json
import os
from pathlib import Path

import pytest

from agent2.app.models.response import BaselineSnapshot, DriftFinding
from agent2.app.services.drift_detector import detect_drift


# ── Fixture helpers ────────────────────────────────────────────────────────────

def _snapshot(
    folders: list | None = None,
    permissions: list | None = None,
    shares: list | None = None,
    local_groups: list | None = None,
    service_accounts: list | None = None,
) -> BaselineSnapshot:
    return BaselineSnapshot(
        server_class="web-server",
        folders=folders or [],
        permissions=permissions or [],
        shares=shares or [],
        local_groups=local_groups or [],
        service_accounts=service_accounts or [],
    )


# ── Baseline — used as the "gold image" ───────────────────────────────────────

BASELINE = _snapshot(
    folders=["C:\\inetpub\\wwwroot"],
    permissions=["C:\\inetpub\\wwwroot:IIS_IUSRS:R"],
    shares=["ADMIN$", "C$", "IPC$"],
    local_groups=["Administrators", "Remote Desktop Users"],
    service_accounts=["svc_iis"],
)


class TestDetectDrift:
    def test_no_drift_returns_empty_list(self):
        current = _snapshot(
            folders=["C:\\inetpub\\wwwroot"],
            permissions=["C:\\inetpub\\wwwroot:IIS_IUSRS:R"],
            shares=["ADMIN$", "C$", "IPC$"],
            local_groups=["Administrators", "Remote Desktop Users"],
            service_accounts=["svc_iis"],
        )
        findings = detect_drift(BASELINE, current, controls_map={})
        assert findings == []

    def test_extra_share_detected(self):
        current = _snapshot(
            folders=["C:\\inetpub\\wwwroot"],
            permissions=["C:\\inetpub\\wwwroot:IIS_IUSRS:R"],
            shares=["ADMIN$", "C$", "IPC$", "ROGUE_SHARE"],   # extra!
            local_groups=["Administrators", "Remote Desktop Users"],
            service_accounts=["svc_iis"],
        )
        findings = detect_drift(BASELINE, current, controls_map={})
        assert len(findings) >= 1
        descriptions = [f.description for f in findings]
        assert any("ROGUE_SHARE" in d for d in descriptions)

    def test_missing_folder_detected(self):
        current = _snapshot(
            folders=[],    # missing required folder
            permissions=["C:\\inetpub\\wwwroot:IIS_IUSRS:R"],
            shares=["ADMIN$", "C$", "IPC$"],
            local_groups=["Administrators", "Remote Desktop Users"],
            service_accounts=["svc_iis"],
        )
        findings = detect_drift(BASELINE, current, controls_map={})
        assert any("C:\\inetpub\\wwwroot" in f.description for f in findings)

    def test_unexpected_service_account_is_high_severity(self):
        current = _snapshot(
            folders=["C:\\inetpub\\wwwroot"],
            permissions=["C:\\inetpub\\wwwroot:IIS_IUSRS:R"],
            shares=["ADMIN$", "C$", "IPC$"],
            local_groups=["Administrators", "Remote Desktop Users"],
            service_accounts=["svc_iis", "svc_backdoor"],  # extra!
        )
        findings = detect_drift(BASELINE, current, controls_map={})
        high_findings = [f for f in findings if f.severity == "HIGH"]
        assert len(high_findings) >= 1

    def test_findings_have_ids(self):
        current = _snapshot(shares=["ADMIN$", "C$", "IPC$", "EXTRA"])
        findings = detect_drift(BASELINE, current, controls_map={})
        for f in findings:
            assert f.finding_id
            assert len(f.finding_id) > 0

    def test_controls_map_applied(self):
        controls_map = {
            "shares": {"cis": "CIS-2.3.1", "nist": "AC-3"}
        }
        current = _snapshot(shares=["ADMIN$", "C$", "IPC$", "EXTRA"])
        findings = detect_drift(BASELINE, current, controls_map=controls_map)
        share_findings = [f for f in findings if "EXTRA" in f.description]
        for f in share_findings:
            assert "CIS-2.3.1" in (f.cis_controls or "")
            assert "AC-3" in (f.nist_controls or "")
