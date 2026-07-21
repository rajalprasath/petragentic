"""
agent2/app/services/report_writer.py
──────────────────────────────────────
Renders the compliance report (JSON + HTML) and uploads both to IBM COS.

The HTML report is produced from a Jinja2 template and includes:
  - Executive summary with finding counts per severity
  - Per-server findings table with CIS/NIST columns
  - Per-finding PowerShell remediation script (collapsible)

Both JSON and HTML artefacts are stored under:
  cos://petragentic-artefacts/compliance/{scan_id}/report.json
  cos://petragentic-artefacts/compliance/{scan_id}/report.html
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from shared.config import Settings
from shared.cos_client import upload_object
from shared.exceptions import ReportRenderError
from shared.logging import get_logger
from agent2.app.models.response import ScanReport

logger = get_logger(__name__)

_TEMPLATE_DIR = Path(__file__).parent.parent / "templates"


def _get_jinja_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=select_autoescape(["html", "j2"]),
    )


def _render_html(report: ScanReport) -> str:
    """Render the compliance report to HTML via Jinja2 template."""
    env = _get_jinja_env()
    try:
        template = env.get_template("compliance_report.html.j2")
        return template.render(
            report=report,
            generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        )
    except Exception as exc:
        raise ReportRenderError(message=str(exc))


def write_and_upload_report(settings: Settings, report: ScanReport) -> tuple[str, str]:
    """
    Render and upload the compliance report to IBM COS.

    Returns: (cos_json_uri, cos_html_uri)
    """
    base_key = f"compliance/{report.scan_id}"

    # ── JSON report ───────────────────────────────────────────────────────────
    json_key = f"{base_key}/report.json"
    json_body = report.model_dump_json(indent=2, mode="json")
    cos_json_uri = upload_object(
        settings=settings,
        bucket=settings.cos_bucket_artefacts,
        key=json_key,
        body=json_body,
        content_type="application/json",
    )

    # ── HTML report ───────────────────────────────────────────────────────────
    html_key = f"{base_key}/report.html"
    html_body = _render_html(report)
    cos_html_uri = upload_object(
        settings=settings,
        bucket=settings.cos_bucket_artefacts,
        key=html_key,
        body=html_body,
        content_type="text/html",
    )

    logger.info(
        "Compliance report uploaded",
        extra={
            "scan_id": report.scan_id,
            "json_uri": cos_json_uri,
            "html_uri": cos_html_uri,
        },
    )
    return cos_json_uri, cos_html_uri
