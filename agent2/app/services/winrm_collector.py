"""
agent2/app/services/winrm_collector.py
────────────────────────────────────────
Collects Windows server security state via WinRM / PowerShell Remoting.

Each collection function runs a specific PowerShell command over the
WinRM connection and returns structured Python data.

Security:
  - WinRM credentials come from IBM Secrets Manager (never hardcoded)
  - Transport is NTLM by default; Kerberos supported for domain environments
  - Port 5985 (HTTP) or 5986 (HTTPS/SSL) configured in Settings
  - Each command times out at settings.winrm_timeout_sec

Collected attributes:
  - Folder permissions (sensitive paths: C:\\, Program Files, Windows, custom)
  - SMB share access rights
  - Local group memberships (Administrators, Remote Desktop Users, etc.)
  - Service accounts (services running as domain/local admin)

Errors on individual collections are non-fatal: the error is recorded
in BaselineSnapshot.collection_errors and collection continues.
"""

import json
from datetime import datetime, timezone

import winrm
from winrm.exceptions import InvalidCredentialsError, WinRMTransportError

from shared.config import Settings
from shared.exceptions import WinRMConnectionError, WinRMCommandError
from shared.logging import get_logger
from agent2.app.models.response import (
    BaselineSnapshot,
    FolderPermission,
    LocalGroupMember,
    ServiceAccountEntry,
    ShareAccess,
)

logger = get_logger(__name__)

# Sensitive folder paths to audit
_AUDIT_PATHS = [
    "C:\\",
    "C:\\Windows",
    "C:\\Program Files",
    "C:\\Program Files (x86)",
    "C:\\Users",
    "C:\\inetpub",
    "C:\\Scripts",
]

# Local groups to enumerate members of
_AUDIT_GROUPS = [
    "Administrators",
    "Remote Desktop Users",
    "Backup Operators",
    "Network Configuration Operators",
    "Power Users",
]

# PowerShell commands — structured as JSON output for reliable parsing
_PS_OS_INFO = r"""
$os = Get-CimInstance Win32_OperatingSystem
$cs = Get-CimInstance Win32_ComputerSystem
@{
  os_version = $os.Caption + " " + $os.Version
  hostname   = $env:COMPUTERNAME
  domain     = $cs.Domain
} | ConvertTo-Json -Compress
""".strip()

_PS_FOLDER_PERMS = r"""
param([string[]]$Paths)
$results = @()
foreach ($p in $Paths) {
  if (Test-Path $p) {
    $acl = Get-Acl $p
    foreach ($ace in $acl.Access) {
      $results += @{
        path        = $p
        owner       = $acl.Owner
        permissions = "$($ace.IdentityReference):$($ace.FileSystemRights)"
        inherited   = $ace.IsInherited
      }
    }
  }
}
$results | ConvertTo-Json -Depth 3 -Compress
""".strip()

_PS_SHARES = r"""
$shares = Get-SmbShare | Where-Object { $_.Name -notmatch '^\w+\$$' } |
  ForEach-Object {
    $perms = Get-SmbShareAccess -Name $_.Name |
      ForEach-Object { "$($_.AccountName):$($_.AccessRight)" }
    @{
      share_name      = $_.Name
      path            = $_.Path
      access_rights   = @($perms)
      max_connections = $_.MaximumAllowed
    }
  }
if ($shares) { $shares | ConvertTo-Json -Depth 3 -Compress }
else { '[]' }
""".strip()

_PS_LOCAL_GROUPS = r"""
param([string[]]$Groups)
$results = @()
foreach ($g in $Groups) {
  try {
    $members = Get-LocalGroupMember -Group $g -ErrorAction Stop |
      ForEach-Object {
        @{
          group_name  = $g
          member      = $_.Name
          member_type = $_.ObjectClass
          is_domain   = ($_.PrincipalSource -eq 'ActiveDirectory')
        }
      }
    if ($members) { $results += $members }
  } catch { }
}
if ($results) { $results | ConvertTo-Json -Depth 3 -Compress }
else { '[]' }
""".strip()

_PS_SERVICE_ACCOUNTS = r"""
$services = Get-WmiObject Win32_Service |
  Where-Object { $_.StartName -notin @('LocalSystem','NT AUTHORITY\\LocalService',
    'NT AUTHORITY\\NetworkService','NT AUTHORITY\\LocalSystem') } |
  ForEach-Object {
    $privileged = $_.StartName -match 'SYSTEM|Administrator|Domain Admin' -or
                  ($_.StartName -match '\\\\' -and $_.StartName -notmatch 'NT AUTHORITY')
    @{
      service_name  = $_.Name
      account       = $_.StartName
      startup_type  = $_.StartMode
      is_privileged = [bool]$privileged
    }
  }
if ($services) { $services | ConvertTo-Json -Depth 3 -Compress }
else { '[]' }
""".strip()


def _run_ps(session: winrm.Session, script: str, host: str) -> str:
    """Execute a PowerShell script and return stdout. Raises WinRMCommandError on failure."""
    result = session.run_ps(script)
    if result.status_code != 0:
        stderr = result.std_err.decode("utf-8", errors="replace").strip()
        raise WinRMCommandError(host=host, command_preview=script[:80])
    return result.std_out.decode("utf-8", errors="replace").strip()


def _open_session(settings: Settings, host: str, username: str, password: str) -> winrm.Session:
    """Open a WinRM session. Raises WinRMConnectionError on auth/transport failure."""
    try:
        session = winrm.Session(
            target=f"http://{host}:{settings.winrm_port}/wsman",
            auth=(username, password),
            transport=settings.winrm_transport,
            read_timeout_sec=settings.winrm_timeout_sec,
            operation_timeout_sec=settings.winrm_timeout_sec,
        )
        return session
    except (InvalidCredentialsError, WinRMTransportError) as exc:
        raise WinRMConnectionError(host=host, reason=str(exc))


def collect_server_state(
    settings: Settings,
    host: str,
    username: str,
    password: str,
) -> BaselineSnapshot:
    """
    Collect the full security baseline state from a Windows server via WinRM.

    Errors on individual collection steps are captured in collection_errors
    and do not abort the overall collection.

    Raises:
        WinRMConnectionError — if the session cannot be established
    """
    session = _open_session(settings, host, username, password)
    logger.info("WinRM session opened", extra={"host": host})
    errors: list[str] = []

    # ── OS info ───────────────────────────────────────────────────────────────
    os_version = "unknown"
    hostname = host
    domain = None
    try:
        info = json.loads(_run_ps(session, _PS_OS_INFO, host))
        os_version = info.get("os_version", "unknown")
        hostname = info.get("hostname", host)
        domain = info.get("domain")
    except Exception as exc:
        errors.append(f"OS info collection failed: {exc}")

    # ── Folder permissions ────────────────────────────────────────────────────
    folder_permissions: list[FolderPermission] = []
    try:
        paths_arg = ", ".join(f'"{p}"' for p in _AUDIT_PATHS)
        script = _PS_FOLDER_PERMS + f"\n$Paths = @({paths_arg})\n"
        raw = _run_ps(session, script, host)
        items = json.loads(raw) if raw and raw != "null" else []
        if isinstance(items, dict):
            items = [items]
        for item in items:
            folder_permissions.append(FolderPermission(**item))
    except Exception as exc:
        errors.append(f"Folder permission collection failed: {exc}")

    # ── SMB shares ────────────────────────────────────────────────────────────
    shares: list[ShareAccess] = []
    try:
        raw = _run_ps(session, _PS_SHARES, host)
        items = json.loads(raw) if raw and raw != "null" else []
        if isinstance(items, dict):
            items = [items]
        for item in items:
            item["access_rights"] = item.get("access_rights") or []
            shares.append(ShareAccess(**item))
    except Exception as exc:
        errors.append(f"Share collection failed: {exc}")

    # ── Local groups ──────────────────────────────────────────────────────────
    local_groups: list[LocalGroupMember] = []
    try:
        groups_arg = ", ".join(f'"{g}"' for g in _AUDIT_GROUPS)
        script = _PS_LOCAL_GROUPS + f"\n$Groups = @({groups_arg})\n"
        raw = _run_ps(session, script, host)
        items = json.loads(raw) if raw and raw != "null" else []
        if isinstance(items, dict):
            items = [items]
        for item in items:
            local_groups.append(LocalGroupMember(**item))
    except Exception as exc:
        errors.append(f"Local group collection failed: {exc}")

    # ── Service accounts ──────────────────────────────────────────────────────
    service_accounts: list[ServiceAccountEntry] = []
    try:
        raw = _run_ps(session, _PS_SERVICE_ACCOUNTS, host)
        items = json.loads(raw) if raw and raw != "null" else []
        if isinstance(items, dict):
            items = [items]
        for item in items:
            service_accounts.append(ServiceAccountEntry(**item))
    except Exception as exc:
        errors.append(f"Service account collection failed: {exc}")

    logger.info(
        "WinRM collection complete",
        extra={"host": host, "errors": len(errors)},
    )

    return BaselineSnapshot(
        server=host,
        collected_at=datetime.now(timezone.utc),
        os_version=os_version,
        hostname=hostname,
        domain=domain,
        folder_permissions=folder_permissions,
        shares=shares,
        local_groups=local_groups,
        service_accounts=service_accounts,
        collection_errors=errors,
    )
