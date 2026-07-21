"""
gateway/app/routes/orchestrate.py
────────────────────────────────────
Proxy routes for the Orchestrate service — multi-turn ReAct agent.

All routes require a valid IBM App ID JWT.
Scope requirements:
  POST /api/v1/agent/chat              → agent:chat
  GET  /api/v1/agent/session/{id}      → agent:read
  DELETE /api/v1/agent/session/{id}    → agent:admin
  GET  /api/v1/agent/info              → agent:read (unauthenticated fallback for health)
"""

from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response

from gateway.app.auth import get_current_user, require_scope
from gateway.app.config import GatewaySettings, get_settings
from gateway.app.proxy import proxy_request

router = APIRouter(prefix="/api/v1", tags=["orchestrate"])


@router.post(
    "/agent/chat",
    summary="Send a message to the Petragentic Orchestrate agent",
    dependencies=[Depends(require_scope("agent:chat"))],
)
async def proxy_agent_chat(
    request: Request,
    settings: GatewaySettings = Depends(get_settings),
    user: dict[str, Any] = Depends(get_current_user),
) -> Response:
    return await proxy_request(request, settings.orchestrate_url, "/agent/chat", user)


@router.get(
    "/agent/session/{session_id}",
    summary="Inspect an Orchestrate conversation session",
    dependencies=[Depends(require_scope("agent:read"))],
)
async def proxy_agent_session(
    session_id: str,
    request: Request,
    settings: GatewaySettings = Depends(get_settings),
    user: dict[str, Any] = Depends(get_current_user),
) -> Response:
    return await proxy_request(request, settings.orchestrate_url, f"/agent/session/{session_id}", user)


@router.delete(
    "/agent/session/{session_id}",
    summary="Clear an Orchestrate conversation session",
    dependencies=[Depends(require_scope("agent:admin"))],
)
async def proxy_agent_clear_session(
    session_id: str,
    request: Request,
    settings: GatewaySettings = Depends(get_settings),
    user: dict[str, Any] = Depends(get_current_user),
) -> Response:
    return await proxy_request(request, settings.orchestrate_url, f"/agent/session/{session_id}", user)


@router.get(
    "/agent/info",
    summary="List registered tools and agent configuration",
    dependencies=[Depends(require_scope("agent:read"))],
)
async def proxy_agent_info(
    request: Request,
    settings: GatewaySettings = Depends(get_settings),
    user: dict[str, Any] = Depends(get_current_user),
) -> Response:
    return await proxy_request(request, settings.orchestrate_url, "/agent/info", user)
