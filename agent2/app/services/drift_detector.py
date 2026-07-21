"""
agent2/app/services/drift_detector.py
───────────────────────────────────────
Classifies baseline diffs into typed DriftFindings with:
  - Severity (critical / high / medium / low)
  - CIS Benchmark control ID
  - NIST 800-53 control family and control reference
  - Human-readable title and description

CIS/NIST mappings come from agent2/app/data/controls_mapping.json,
which is loaded once at module import time.

Severity heuristics:
  folder_permission  + unexpected write/FULL   → critical
  folder_permission  + unexpected read         → high
  share              + Everyone:FULL           → critical
  share              + new unapproved share    → high
  group_member       + Administrators added    → critical
  group_member       + other privileged groups → high
  service_account    + running as Domain Admin → critical
  service_account    + changed account         → high
"""

import json
import uuid
from pathlib import Path

from shared.logging import get_logger
from agent2.app.models.response import (
    ControlMapping,
    DriftFinding,
    Severity,
)
from agent2.app.services.baseline_comparator import BaselineDiff

logger = get_logger(__name__)

# Load CIS/NIST mapping at module import time
_MAPPING_PATH = Path(__file__).parent.parent / "data" / "controls_mapping.json"
with open(_MAPPING_PATH, "r", encoding="utf-8") as _f:
    _CONTROLS_MAP: dict = json.load(_f)


def _get_control(category: str, attribute_key: str) -> ControlMapping:
    """
    Look up the CIS/NIST control for a (category, attribute_key) pair.
    Falls back to the category default if the specific key is not mapped.
    """
    cat_map = _CONTROLS_MAP.get(category, {})
    entry = cat_map.get(attribute_key) or cat_map.get("default") or {
        "cis_control_id": "CIS N/A",
        "cis_description": "No CIS mapping defined",
        "nist_family": "N/A",
        "nist_control": "N/A",
        "nist_description": "No NIST 800-53 mapping defined",
    }
    return ControlMapping(**entry)


def _classify_severity(diff: BaselineDiff) -> Severity:
    """Determine finding severity from the category and actual value."""
    cat = diff.category
    actual = str(diff.actual).upper()
    key = diff.attribute_key.upper()

    if cat == "folder_permission":
        if any(x in actual for x in ["(F)", "FULLCONTROL", "WRITE", "MODIFY"]):
            return Severity.CRITICAL
        if any(x in actual for x in ["(R)", "READ", "LIST"]):
            return Severity.HIGH
        return Severity.MEDIUM

    if cat == "share":
        if "EVERYONE" in actual and any(x in actual for x in ["FULL", "CHANGE"]):
            return Severity.CRITICAL
        if diff.expected == "<not in baseline>":  # new unapproved share
            return Severity.HIGH
        return Severity.MEDIUM

    if cat == "group_member":
        if "ADMINISTRATORS" in key:
            return Severity.CRITICAL
        if key in ("BACKUP OPERATORS", "NETWORK CONFIGURATION OPERATORS"):
            return Severity.HIGH
        return Severity.MEDIUM

    if cat == "service_account":
        if any(x in actual.upper() for x in ["DOMAIN ADMIN", "ADMINISTRATOR", "SYSTEM"]):
            return Severity.CRITICAL
        return Severity.HIGH

    return Severity.LOW


def _build_title(diff: BaselineDiff) -> str:
    titles = {
        "folder_permission": f"Unexpected NTFS permission on {diff.attribute_key}",
        "share":             f"Share access deviation: {diff.attribute_key}",
        "group_member":      f"Unauthorised member in {diff.attribute_key}",
        "service_account":   f"Service account drift: {diff.attribute_key}",
    }
    return titles.get(diff.category, f"Drift in {diff.category}: {diff.attribute_key}")


def _build_description(diff: BaselineDiff) -> str:
    return (
        f"Category: {diff.category} | Resource: {diff.attribute_key}\n"
        f"Expected: {diff.expected}\n"
        f"Actual:   {diff.actual}"
    )


def classify_diffs(
    server: str,
    diffs: list[BaselineDiff],
) -> list[DriftFinding]:
    """
    Convert a list of BaselineDiff objects into typed DriftFindings.

    Each finding gets a unique ID, severity, CIS/NIST mapping,
    and human-readable title/description.
    """
    findings: list[DriftFinding] = []

    for diff in diffs:
        severity = _classify_severity(diff)
        control = _get_control(diff.category, diff.attribute_key)

        finding = DriftFinding(
            finding_id=str(uuid.uuid4()),
            server=server,
            category=diff.category,
            severity=severity,
            title=_build_title(diff),
            description=_build_description(diff),
            expected_value=diff.expected,
            actual_value=diff.actual,
            control=control,
            remediation=None,       # populated by remediation_generator
            is_new=True,            # updated by audit_store on subsequent scans
        )
        findings.append(finding)

    logger.info(
        "Drift classification complete",
        extra={
            "server": server,
            "findings": len(findings),
            "critical": sum(1 for f in findings if f.severity == Severity.CRITICAL),
            "high": sum(1 for f in findings if f.severity == Severity.HIGH),
        },
    )
    return findings
