"""
agent2/app/models/request.py
──────────────────────────────
Pydantic request schemas for Agent 2 — Security Compliance & Audit.
"""

from enum import Enum
from pydantic import BaseModel, Field, field_validator


class ScanType(str, Enum):
    NEW_VALIDATION = "new_validation"       # First-time audit of a new server
    PERIODIC_AUDIT = "periodic_audit"       # Routine scheduled audit
    DRIFT_CHECK    = "drift_check"          # On-demand drift detection only


class AuditScope(str, Enum):
    """Which server attributes to include in the scan."""
    FULL           = "full"
    FOLDERS        = "folders"
    SHARES         = "shares"
    LOCAL_GROUPS   = "local_groups"
    SERVICE_ACCOUNTS = "service_accounts"


class ValidateRequest(BaseModel):
    """
    Request schema for POST /validate.

    Specifies which Windows servers to audit, what to scan, and
    which Gold Image baseline class to compare against.
    """
    servers: list[str] = Field(
        ...,
        min_length=1,
        description="List of server hostnames or IP addresses to audit",
        examples=[["WIN-SRV-001", "WIN-SRV-002"]],
    )
    server_class: str = Field(
        default="standard-windows-server",
        description="The baseline class (matches a row in server_baselines table)",
        examples=["standard-windows-server", "domain-controller", "sql-server"],
    )
    scan_type: ScanType = ScanType.PERIODIC_AUDIT
    scope: list[AuditScope] = Field(
        default=[AuditScope.FULL],
        description="Which attributes to scan — defaults to full audit",
    )
    winrm_username: str = Field(
        ..., description="Windows domain or local admin account for WinRM"
    )
    winrm_password: str = Field(
        ..., description="Credential — fetched from Secrets Manager at runtime"
    )
    triggered_by: str = Field(
        default="manual",
        description="Who or what triggered this audit (e.g. github_actions_scheduled)",
    )

    @field_validator("servers")
    @classmethod
    def servers_not_empty(cls, v: list[str]) -> list[str]:
        cleaned = [s.strip() for s in v if s.strip()]
        if not cleaned:
            raise ValueError("servers list must contain at least one non-empty hostname")
        return cleaned
