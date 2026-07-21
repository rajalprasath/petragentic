"""
agent2/app/models/response.py
──────────────────────────────
Pydantic response schemas for Agent 2 — Security Compliance & Audit.

Hierarchy:
  ValidateResponse
    └── ScanReport
          ├── ServerScanResult (one per server)
          │     ├── BaselineSnapshot       — collected state
          │     └── DriftFinding[]         — deviations from Gold Image
          │           └── RemediationScript
          └── ScanSummary                  — aggregate counts

Every DriftFinding is mapped to a CIS Benchmark control ID
and a NIST 800-53 control family.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ── Severity ──────────────────────────────────────────────────────────────────

class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH     = "high"
    MEDIUM   = "medium"
    LOW      = "low"
    INFO     = "info"


# ── Baseline sub-schemas ──────────────────────────────────────────────────────

class FolderPermission(BaseModel):
    path: str
    owner: str
    permissions: str                 # e.g. "NT AUTHORITY\\SYSTEM:(F)"
    inherited: bool = False


class ShareAccess(BaseModel):
    share_name: str
    path: str
    access_rights: list[str]         # e.g. ["Everyone:READ", "Admins:FULL"]
    max_connections: int | None = None


class LocalGroupMember(BaseModel):
    group_name: str
    member: str
    member_type: str                 # "User" | "Group" | "Computer"
    is_domain: bool = False


class ServiceAccountEntry(BaseModel):
    service_name: str
    account: str
    startup_type: str                # "Automatic" | "Manual" | "Disabled"
    is_privileged: bool              # True if running as SYSTEM or domain admin


class BaselineSnapshot(BaseModel):
    """
    Point-in-time snapshot of a server's security-relevant state,
    collected via WinRM.
    """
    server: str = ""
    collected_at: datetime
    os_version: str
    hostname: str
    domain: str | None

    folder_permissions: list[FolderPermission] = Field(default_factory=list)
    shares: list[ShareAccess] = Field(default_factory=list)
    local_groups: list[LocalGroupMember] = Field(default_factory=list)
    service_accounts: list[ServiceAccountEntry] = Field(default_factory=list)

    # Raw PowerShell collection errors (non-fatal — partial data returned)
    collection_errors: list[str] = Field(default_factory=list)


# ── Drift finding ─────────────────────────────────────────────────────────────

class ControlMapping(BaseModel):
    """Regulatory framework control mapping for a drift finding."""
    cis_control_id: str              # e.g. "CIS 5.1"
    cis_description: str
    nist_family: str                 # e.g. "AC" (Access Control)
    nist_control: str                # e.g. "AC-3"
    nist_description: str


class RemediationScript(BaseModel):
    """Generated PowerShell remediation script for a single finding."""
    finding_id: str
    script_type: str                 # "ntfs_acl" | "share_access" | "group_membership" | "service_account"
    description: str
    powershell_script: str           # Full PS1 content
    estimated_risk: str              # "Low" | "Medium" | "High" — risk of running the script
    requires_reboot: bool = False
    syntax_validated: bool = False


class DriftFinding(BaseModel):
    """
    A single security deviation detected between the collected server state
    and the Gold Image baseline.
    """
    finding_id: str
    server: str
    category: str                    # "folder_permission" | "share_access" | "local_group" | "service_account"
    severity: Severity
    title: str
    description: str

    # What was expected (from baseline) vs what was found
    expected_value: Any
    actual_value: Any

    # Regulatory mapping
    control: ControlMapping

    # Generated remediation
    remediation: RemediationScript | None = None

    # Whether the finding is new since last scan
    is_new: bool = True


# ── Per-server result ─────────────────────────────────────────────────────────

class ComplianceStatus(str, Enum):
    COMPLIANT     = "compliant"
    NON_COMPLIANT = "non_compliant"
    PARTIAL       = "partial"          # Some checks passed, some failed
    SCAN_FAILED   = "scan_failed"      # WinRM or collection error


class ServerScanResult(BaseModel):
    """Audit result for a single Windows server."""
    server: str
    scan_id: str
    scanned_at: datetime
    compliance_status: ComplianceStatus
    snapshot: BaselineSnapshot | None = None
    findings: list[DriftFinding] = Field(default_factory=list)
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    error: str | None = None          # Set if WinRM connection failed


# ── Report summary ────────────────────────────────────────────────────────────

class ScanSummary(BaseModel):
    total_servers: int
    compliant_servers: int
    non_compliant_servers: int
    failed_servers: int
    total_findings: int
    critical_findings: int
    high_findings: int
    medium_findings: int
    low_findings: int
    top_cis_violations: list[str]     # CIS control IDs with most findings


class ScanReport(BaseModel):
    """Full compliance report for a scan run."""
    scan_id: str
    scan_type: str
    server_class: str
    triggered_by: str
    started_at: datetime
    completed_at: datetime
    status: str                       # "complete" | "partial" | "failed"
    summary: ScanSummary
    server_results: list[ServerScanResult]
    cos_json_uri: str
    cos_html_uri: str
    prompt_template_version: str


class ValidateResponse(BaseModel):
    """Response from POST /validate."""
    scan_id: str
    status: str                       # "complete" | "partial" | "failed"
    report: ScanReport
    message: str = ""
