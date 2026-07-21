"""
agent2/app/routes/validate.py
───────────────────────────────
POST /validate — Security compliance audit endpoint.

Full pipeline per server:
  1. Open WinRM session and collect server state (winrm_collector)
  2. Load Gold Image baseline from watsonx.data (baseline_comparator)
  3. Diff collected state vs baseline (baseline_comparator)
  4. Classify diffs into DriftFindings with CIS/NIST mapping (drift_detector)
  5. Generate PowerShell remediation scripts (remediation_generator)
  6. Aggregate results into ScanReport
  7. Render + upload JSON + HTML report to IBM COS (report_writer)
  8. Store scan metadata in watsonx.data (audit_store — background)
  9. Return ValidateResponse
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends

from shared.config import Settings
from shared.logging import get_logger

from agent2.app.config import get_settings
from agent2.app.models.request import ValidateRequest
from agent2.app.models.response import (
    ComplianceStatus,
    ScanReport,
    ScanSummary,
    ServerScanResult,
    Severity,
    ValidateResponse,
)
from agent2.app.services.audit_store import store_scan_result
from agent2.app.services.baseline_comparator import compare_snapshot, fetch_baseline
from agent2.app.services.drift_detector import classify_diffs
from agent2.app.services.remediation_generator import generate_all_remediations
from agent2.app.services.report_writer import write_and_upload_report
from agent2.app.services.winrm_collector import collect_server_state

logger = get_logger(__name__)
router = APIRouter(prefix="/validate", tags=["compliance"])


def _count_by_severity(findings, severity: Severity) -> int:
    return sum(1 for f in findings if f.severity == severity)


def _determine_compliance_status(findings, collection_errors) -> ComplianceStatus:
    if collection_errors:
        return ComplianceStatus.PARTIAL
    if not findings:
        return ComplianceStatus.COMPLIANT
    if any(f.severity == Severity.CRITICAL for f in findings):
        return ComplianceStatus.NON_COMPLIANT
    return ComplianceStatus.NON_COMPLIANT


def _audit_one_server(
    settings: Settings,
    scan_id: str,
    server: str,
    request: ValidateRequest,
    baseline: dict,
) -> ServerScanResult:
    """Run the full audit pipeline for a single server."""
    started_at = datetime.now(timezone.utc)

    # Step 1: Collect server state via WinRM
    snapshot = collect_server_state(
        settings=settings,
        host=server,
        username=request.winrm_username,
        password=request.winrm_password,
    )

    # Step 2+3: Diff against baseline
    diffs = compare_snapshot(snapshot, baseline)

    # Step 4: Classify into DriftFindings
    findings = classify_diffs(server=server, diffs=diffs)

    # Step 5: Generate remediation scripts
    findings = generate_all_remediations(settings, findings)

    status = _determine_compliance_status(findings, snapshot.collection_errors)

    return ServerScanResult(
        server=server,
        scan_id=scan_id,
        scanned_at=started_at,
        compliance_status=status,
        snapshot=snapshot,
        findings=findings,
        critical_count=_count_by_severity(findings, Severity.CRITICAL),
        high_count=_count_by_severity(findings, Severity.HIGH),
        medium_count=_count_by_severity(findings, Severity.MEDIUM),
        low_count=_count_by_severity(findings, Severity.LOW),
    )


@router.post("", response_model=ValidateResponse, status_code=200)
async def validate(
    request: ValidateRequest,
    background_tasks: BackgroundTasks,
    settings: Settings = Depends(get_settings),
) -> ValidateResponse:
    """
    Run a security compliance audit against one or more Windows servers.

    - Collects server state via WinRM
    - Compares against Gold Image baseline from watsonx.data
    - Generates CIS/NIST-mapped findings and PowerShell remediation scripts
    - Produces HTML + JSON compliance report stored in IBM COS
    """
    scan_id = str(uuid.uuid4())
    started_at = datetime.now(timezone.utc)
    logger.info("Audit scan started", extra={"scan_id": scan_id, "servers": request.servers})

    # Load baseline once — shared across all servers in this request
    baseline = fetch_baseline(settings, request.server_class)

    server_results: list[ServerScanResult] = []
    for server in request.servers:
        try:
            result = _audit_one_server(settings, scan_id, server, request, baseline)
            server_results.append(result)
        except Exception as exc:
            logger.error(
                "Server audit failed",
                extra={"scan_id": scan_id, "server": server, "error": str(exc)},
            )
            server_results.append(ServerScanResult(
                server=server,
                scan_id=scan_id,
                scanned_at=datetime.now(timezone.utc),
                compliance_status=ComplianceStatus.SCAN_FAILED,
                snapshot=None,
                findings=[],
                error=str(exc),
            ))

    # ── Aggregate summary ─────────────────────────────────────────────────────
    all_findings = [f for r in server_results if r.findings for f in r.findings]
    total_critical = sum(r.critical_count for r in server_results)
    total_high     = sum(r.high_count for r in server_results)
    total_medium   = sum(r.medium_count for r in server_results)
    total_low      = sum(r.low_count for r in server_results)

    from collections import Counter
    cis_counts = Counter(f.control.cis_control_id for f in all_findings)
    top_cis = [cid for cid, _ in cis_counts.most_common(5)]

    compliant = sum(1 for r in server_results if r.compliance_status == ComplianceStatus.COMPLIANT)
    failed    = sum(1 for r in server_results if r.compliance_status == ComplianceStatus.SCAN_FAILED)

    summary = ScanSummary(
        total_servers=len(server_results),
        compliant_servers=compliant,
        non_compliant_servers=len(server_results) - compliant - failed,
        failed_servers=failed,
        total_findings=len(all_findings),
        critical_findings=total_critical,
        high_findings=total_high,
        medium_findings=total_medium,
        low_findings=total_low,
        top_cis_violations=top_cis,
    )

    completed_at = datetime.now(timezone.utc)
    scan_status = "failed" if failed == len(server_results) else (
        "partial" if failed > 0 else "complete"
    )

    # ── Write reports to COS ──────────────────────────────────────────────────
    report = ScanReport(
        scan_id=scan_id,
        scan_type=request.scan_type.value,
        server_class=request.server_class,
        triggered_by=request.triggered_by,
        started_at=started_at,
        completed_at=completed_at,
        status=scan_status,
        summary=summary,
        server_results=server_results,
        cos_json_uri="",   # populated after upload
        cos_html_uri="",
        prompt_template_version=settings.agent2_prompt_template_version,
    )

    cos_json_uri, cos_html_uri = write_and_upload_report(settings, report)
    report.cos_json_uri = cos_json_uri
    report.cos_html_uri = cos_html_uri

    # ── Persist to watsonx.data (background — non-blocking) ──────────────────
    for result in server_results:
        if result.compliance_status != ComplianceStatus.SCAN_FAILED:
            background_tasks.add_task(
                store_scan_result,
                settings, result, scan_id,
                request.server_class, request.scan_type.value, request.triggered_by,
            )

    logger.info(
        "Audit scan complete",
        extra={
            "scan_id": scan_id,
            "servers": len(server_results),
            "total_findings": len(all_findings),
            "critical": total_critical,
        },
    )

    return ValidateResponse(
        scan_id=scan_id,
        status=scan_status,
        report=report,
        message=f"Audit complete: {len(all_findings)} findings across {len(server_results)} servers",
    )
