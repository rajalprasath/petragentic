"""
agent2/app/services/remediation_generator.py
──────────────────────────────────────────────
Generates PowerShell remediation scripts for each DriftFinding
using Granite-34b-code-instruct via watsonx.ai.

For each finding the engine:
  1. Builds a structured code-generation prompt
  2. Calls Granite-34b-code to generate a PS1 script
  3. Optionally validates PS1 syntax before returning
  4. Logs the inference to watsonx.governance AI Factsheets

Script types generated:
  folder_permission  → icacls / Set-Acl commands (NTFS ACLs)
  share              → Revoke-SmbShareAccess / Remove-SmbShare commands
  group_member       → Remove-LocalGroupMember commands
  service_account    → sc.exe config / Set-ServiceAccount commands

PS1 syntax validation: runs powershell.exe -NoProfile -NonInteractive
  -Command "& { [scriptblock]::Create($script) }" locally.
  Only available when settings.ps_syntax_check = True.
"""

import re
import subprocess
import tempfile
import os
import time

from shared.config import Settings
from shared.exceptions import PowerShellSyntaxError, RemediationGenerationError
from shared.governance_logger import log_inference
from shared.logging import get_logger
from shared.watsonx_client import generate_text
from agent2.app.models.response import DriftFinding, RemediationScript

logger = get_logger(__name__)

_CODE_FENCE_RE = re.compile(r"```(?:powershell|ps1|ps)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)

_PROMPT_TEMPLATE = """You are a Windows Server security engineer.
Generate a PowerShell script that remediates the following security finding.
The script must be safe, idempotent, and production-ready.
Respond with ONLY the PowerShell script — no explanations, no markdown fences.

FINDING:
  Category:      {category}
  Server:        {server}
  Resource:      {attribute_key}
  Title:         {title}
  Description:   {description}
  Expected:      {expected}
  Actual:        {actual}
  CIS Control:   {cis_control_id} — {cis_description}
  NIST Control:  {nist_control} ({nist_family}) — {nist_description}

REQUIREMENTS:
- Script must be idempotent (safe to run multiple times)
- Include a comment header with the finding ID and CIS control
- Include Write-Host progress messages
- Include error handling with try/catch
- For NTFS permissions: use icacls or Set-Acl
- For share access: use Revoke-SmbShareAccess or Remove-SmbShare
- For group membership: use Remove-LocalGroupMember
- For service accounts: use sc.exe config or Set-Service

PowerShell script:
""".strip()


def _build_remediation_prompt(finding: DriftFinding) -> str:
    return _PROMPT_TEMPLATE.format(
        category=finding.category,
        server=finding.server,
        attribute_key=finding.category,
        title=finding.title,
        description=finding.description.replace("\n", " | "),
        expected=finding.expected_value,
        actual=finding.actual_value,
        cis_control_id=finding.control.cis_control_id,
        cis_description=finding.control.cis_description,
        nist_control=finding.control.nist_control,
        nist_family=finding.control.nist_family,
        nist_description=finding.control.nist_description,
    )


def _extract_ps1(raw: str) -> str:
    """Extract PowerShell code from potential markdown fences."""
    match = _CODE_FENCE_RE.search(raw)
    if match:
        return match.group(1).strip()
    return raw.strip()


def _validate_ps1_syntax(script: str, finding_id: str) -> None:
    """
    Validate PS1 syntax by parsing with PowerShell's scriptblock parser.
    Raises PowerShellSyntaxError if syntax is invalid.
    Only runs when powershell.exe is available on the host.
    """
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".ps1", delete=False, encoding="utf-8"
        ) as tmp:
            tmp.write(script)
            tmp_path = tmp.name

        result = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                f"[scriptblock]::Create([System.IO.File]::ReadAllText('{tmp_path}')) | Out-Null; Write-Host 'OK'",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0 or "OK" not in result.stdout:
            raise PowerShellSyntaxError(script_preview=script[:200])

    except FileNotFoundError:
        # powershell.exe not available on Linux runners — skip validation
        logger.debug("powershell.exe not found; skipping PS1 syntax check")
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


def _classify_script_type(category: str) -> str:
    mapping = {
        "folder_permission": "ntfs_acl",
        "share":             "share_access",
        "group_member":      "group_membership",
        "service_account":   "service_account",
    }
    return mapping.get(category, "general")


def generate_remediation(
    settings: Settings,
    finding: DriftFinding,
) -> RemediationScript:
    """
    Generate a PowerShell remediation script for a single DriftFinding.

    Returns a populated RemediationScript.
    Raises RemediationGenerationError if generation fails.
    """
    prompt = _build_remediation_prompt(finding)
    t0 = time.monotonic()

    try:
        raw_output = generate_text(
            settings=settings,
            model_id=settings.watsonx_model_code,
            prompt=prompt,
        )
    except Exception as exc:
        raise RemediationGenerationError(finding_id=finding.finding_id, message=str(exc))

    latency_ms = int((time.monotonic() - t0) * 1000)
    ps1_script = _extract_ps1(raw_output)

    syntax_ok = False
    if settings.ps_syntax_check:
        try:
            _validate_ps1_syntax(ps1_script, finding.finding_id)
            syntax_ok = True
        except PowerShellSyntaxError:
            logger.warning(
                "PS1 syntax validation failed",
                extra={"finding_id": finding.finding_id},
            )
            raise

    # Log to watsonx.governance
    log_inference(
        settings=settings,
        agent_id="agent2-remediation",
        model_id=settings.watsonx_model_code,
        prompt_template_version=settings.agent2_prompt_template_version,
        input_tokens=len(prompt.split()),
        output_tokens=len(raw_output.split()),
        latency_ms=latency_ms,
        output_text=raw_output,
        metadata={
            "finding_id": finding.finding_id,
            "category": finding.category,
            "severity": finding.severity.value,
        },
    )

    logger.info(
        "Remediation script generated",
        extra={
            "finding_id": finding.finding_id,
            "category": finding.category,
            "latency_ms": latency_ms,
            "syntax_validated": syntax_ok,
        },
    )

    return RemediationScript(
        finding_id=finding.finding_id,
        script_type=_classify_script_type(finding.category),
        description=f"Remediate: {finding.title}",
        powershell_script=ps1_script,
        estimated_risk="Medium" if finding.severity in ("critical", "high") else "Low",
        requires_reboot=False,
        syntax_validated=syntax_ok,
    )


def generate_all_remediations(
    settings: Settings,
    findings: list[DriftFinding],
) -> list[DriftFinding]:
    """
    Generate remediation scripts for all findings and attach them to the
    DriftFinding objects in place.

    Failures on individual findings are logged as warnings and skipped.
    Returns the updated findings list.
    """
    for finding in findings:
        try:
            finding.remediation = generate_remediation(settings, finding)
        except Exception as exc:
            logger.warning(
                "Remediation generation skipped",
                extra={"finding_id": finding.finding_id, "error": str(exc)},
            )
    return findings
