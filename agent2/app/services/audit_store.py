"""
agent2/app/services/audit_store.py
────────────────────────────────────
Persists scan metadata and drift findings to watsonx.data Iceberg tables.

Tables (Iceberg, created by infra DDL):
  audit_scans (
    scan_id           VARCHAR,
    server            VARCHAR,
    server_class      VARCHAR,
    scan_type         VARCHAR,
    started_at        TIMESTAMP,
    completed_at      TIMESTAMP,
    compliance_status VARCHAR,
    total_findings    BIGINT,
    critical_count    BIGINT,
    triggered_by      VARCHAR
  )

  drift_findings (
    finding_id        VARCHAR,
    scan_id           VARCHAR,
    server            VARCHAR,
    category          VARCHAR,
    severity          VARCHAR,
    title             VARCHAR,
    cis_control_id    VARCHAR,
    nist_control      VARCHAR,
    is_new            BOOLEAN,
    created_at        TIMESTAMP
  )

Writes are best-effort: failures are logged as WARNING.
"""

from datetime import datetime, timezone

from shared.config import Settings
from shared.logging import get_logger
from shared.wxdata_client import execute_query, insert_row
from agent2.app.models.response import ServerScanResult

logger = get_logger(__name__)

_SCAN_TABLE    = "{catalog}.{schema}.audit_scans"
_FINDING_TABLE = "{catalog}.{schema}.drift_findings"


def _tbl(settings: Settings, name: str) -> str:
    return name.format(catalog=settings.wxdata_catalog, schema=settings.wxdata_schema)


def _check_previous_findings(
    settings: Settings,
    scan_id: str,
    server: str,
    finding_ids_current: set[str],
) -> set[str]:
    """
    Query the last scan's finding titles to identify which findings are new
    vs recurring. Returns the set of finding titles seen in the previous scan.
    """
    sql = f"""
        SELECT title
        FROM {_tbl(settings, _FINDING_TABLE)}
        WHERE server = '{server}'
          AND scan_id != '{scan_id}'
        ORDER BY created_at DESC
        LIMIT 500
    """
    try:
        rows = execute_query(settings, sql)
        return {row["title"] for row in rows}
    except Exception:
        return set()


def store_scan_result(
    settings: Settings,
    result: ServerScanResult,
    scan_id: str,
    server_class: str,
    scan_type: str,
    triggered_by: str,
) -> None:
    """
    Persist a ServerScanResult to watsonx.data audit_scans + drift_findings tables.
    Marks findings as new/recurring by comparing to the previous scan.
    """
    # Check which findings are recurring
    current_titles = {f.title for f in result.findings}
    previous_titles = _check_previous_findings(settings, scan_id, result.server, current_titles)

    # Mark recurring findings
    for finding in result.findings:
        if finding.title in previous_titles:
            finding.is_new = False

    # ── audit_scans row ───────────────────────────────────────────────────────
    scan_row = {
        "scan_id":          scan_id,
        "server":           result.server,
        "server_class":     server_class,
        "scan_type":        scan_type,
        "started_at":       result.scanned_at.isoformat(),
        "completed_at":     datetime.now(timezone.utc).isoformat(),
        "compliance_status": result.compliance_status.value,
        "total_findings":   len(result.findings),
        "critical_count":   result.critical_count,
        "triggered_by":     triggered_by,
    }
    try:
        insert_row(settings, _tbl(settings, _SCAN_TABLE), scan_row)
    except Exception as exc:
        logger.warning("audit_scans write failed", extra={"server": result.server, "error": str(exc)})

    # ── drift_findings rows ───────────────────────────────────────────────────
    for finding in result.findings:
        finding_row = {
            "finding_id":    finding.finding_id,
            "scan_id":       scan_id,
            "server":        result.server,
            "category":      finding.category,
            "severity":      finding.severity.value,
            "title":         finding.title[:500],
            "cis_control_id": finding.control.cis_control_id,
            "nist_control":  finding.control.nist_control,
            "is_new":        str(finding.is_new).lower(),
            "created_at":    datetime.now(timezone.utc).isoformat(),
        }
        try:
            insert_row(settings, _tbl(settings, _FINDING_TABLE), finding_row)
        except Exception as exc:
            logger.warning(
                "drift_findings write failed",
                extra={"finding_id": finding.finding_id, "error": str(exc)},
            )

    logger.info(
        "Scan result stored",
        extra={
            "scan_id": scan_id,
            "server": result.server,
            "findings": len(result.findings),
        },
    )
