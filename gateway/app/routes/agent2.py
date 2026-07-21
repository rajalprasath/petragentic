"""
gateway/app/routes/agent2.py
──────────────────────────────
Proxy routes for Agent 2 — Security Compliance & Audit.

All routes require a valid IBM App ID JWT.
Scope requirements:
  POST /api/v1/validate          → audit:write
  GET  /api/v1/report/{scan_id}  → audit:read
  GET  /api/v1/report/{scan_id}/html → audit:read
"""

from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response

from gateway.app.auth import get_current_user, require_scope
from gateway.app.config import GatewaySettings, get_settings
from gateway.app.proxy import proxy_request

router = APIRouter(prefix="/api/v1", tags=["agent2"])


@router.post(
    "/validate",
    summary="Run a server security baseline validation",
    dependencies=[Depends(require_scope("audit:write"))],
)
async def proxy_validate(
    request: Request,
    settings: GatewaySettings = Depends(get_settings),
    user: dict[str, Any] = Depends(get_current_user),
) -> Response:
    return await proxy_request(request, settings.agent2_url, "/validate", user)


@router.get(
    "/report/{scan_id}",
    summary="Retrieve a compliance scan report (JSON)",
    dependencies=[Depends(require_scope("audit:read"))],
)
async def proxy_report_json(
    scan_id: str,
    request: Request,
    settings: GatewaySettings = Depends(get_settings),
    user: dict[str, Any] = Depends(get_current_user),
) -> Response:
    return await proxy_request(request, settings.agent2_url, f"/report/{scan_id}", user)


@router.get(
    "/report/{scan_id}/html",
    summary="Retrieve a compliance scan report (HTML)",
    dependencies=[Depends(require_scope("audit:read"))],
)
async def proxy_report_html(
    scan_id: str,
    request: Request,
    settings: GatewaySettings = Depends(get_settings),
    user: dict[str, Any] = Depends(get_current_user),
) -> Response:
    return await proxy_request(request, settings.agent2_url, f"/report/{scan_id}/html", user)
