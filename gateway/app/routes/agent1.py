"""
gateway/app/routes/agent1.py
──────────────────────────────
Proxy routes for Agent 1 — Integration Design & Automation.

All routes require a valid IBM App ID JWT.
Scope requirements:
  POST /api/v1/design           → design:write
  GET  /api/v1/catalogue/stats  → design:read
"""

from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response

from gateway.app.auth import get_current_user, require_scope
from gateway.app.config import GatewaySettings, get_settings
from gateway.app.proxy import proxy_request

router = APIRouter(prefix="/api/v1", tags=["agent1"])


@router.post(
    "/design",
    summary="Generate an integration design document",
    dependencies=[Depends(require_scope("design:write"))],
)
async def proxy_design(
    request: Request,
    settings: GatewaySettings = Depends(get_settings),
    user: dict[str, Any] = Depends(get_current_user),
) -> Response:
    return await proxy_request(request, settings.agent1_url, "/design", user)


@router.get(
    "/catalogue/stats",
    summary="Integration catalogue usage statistics",
    dependencies=[Depends(require_scope("design:read"))],
)
async def proxy_catalogue_stats(
    request: Request,
    settings: GatewaySettings = Depends(get_settings),
    user: dict[str, Any] = Depends(get_current_user),
) -> Response:
    return await proxy_request(request, settings.agent1_url, "/catalogue/stats", user)
