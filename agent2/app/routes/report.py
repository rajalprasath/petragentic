"""
agent2/app/routes/report.py
────────────────────────────
GET /report/{scan_id} — retrieve a completed compliance report from COS.
"""

import json

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from shared.config import Settings
from shared.cos_client import download_object, object_exists
from shared.exceptions import PetragenticError
from shared.logging import get_logger

from agent2.app.config import get_settings

logger = get_logger(__name__)
router = APIRouter(prefix="/report", tags=["compliance"])


@router.get("/{scan_id}", response_class=JSONResponse)
async def get_report(
    scan_id: str,
    settings: Settings = Depends(get_settings),
) -> JSONResponse:
    """
    Retrieve a completed compliance scan report from IBM COS.
    Returns the JSON report. For the HTML version, use /report/{scan_id}/html.
    """
    key = f"compliance/{scan_id}/report.json"
    if not object_exists(settings, settings.cos_bucket_artefacts, key):
        raise PetragenticError(
            message=f"Report not found for scan_id: {scan_id}",
            status_code=404,
        )
    raw = download_object(settings, settings.cos_bucket_artefacts, key)
    return JSONResponse(content=json.loads(raw))


@router.get("/{scan_id}/html")
async def get_report_html(
    scan_id: str,
    settings: Settings = Depends(get_settings),
):
    """Return the HTML compliance report for browser rendering."""
    from fastapi.responses import HTMLResponse
    key = f"compliance/{scan_id}/report.html"
    if not object_exists(settings, settings.cos_bucket_artefacts, key):
        raise PetragenticError(
            message=f"HTML report not found for scan_id: {scan_id}",
            status_code=404,
        )
    raw = download_object(settings, settings.cos_bucket_artefacts, key)
    return HTMLResponse(content=raw.decode("utf-8"))
