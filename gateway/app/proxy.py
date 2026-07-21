"""
gateway/app/proxy.py
─────────────────────
Async HTTP reverse proxy using httpx.

A shared AsyncClient is created once during app lifespan and reused for all
upstream calls.  Headers are forwarded as-is with the following mutations:
  - X-Correlation-ID  — echoed if present, generated if absent
  - X-Forwarded-For   — set to the gateway's client IP
  - Authorization     — STRIPPED before forwarding (upstream services trust the
                        network layer inside the petragentic namespace)
  - X-Gateway-User    — injected with the authenticated subject (sub claim)
"""

import uuid
from typing import Any

import httpx
from fastapi import HTTPException, Request
from fastapi.responses import Response

from gateway.app.config import GatewaySettings

# Module-level client; initialised in lifespan
_http_client: httpx.AsyncClient | None = None

# Headers that must not be forwarded to upstreams
_HOP_BY_HOP = frozenset(
    [
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailers",
        "transfer-encoding",
        "upgrade",
        "authorization",   # stripped — gateway handles auth, not upstreams
        "host",            # httpx sets the correct Host for the upstream
    ]
)


def init_client(settings: GatewaySettings) -> None:
    """Called once at startup to initialise the shared httpx.AsyncClient."""
    global _http_client
    _http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(
            connect=settings.upstream_connect_timeout,
            read=settings.upstream_read_timeout,
            write=settings.upstream_read_timeout,
            pool=settings.upstream_connect_timeout,
        ),
        follow_redirects=False,
        limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
    )


async def close_client() -> None:
    """Called once at shutdown to drain the httpx connection pool."""
    global _http_client
    if _http_client is not None:
        await _http_client.aclose()
        _http_client = None


async def proxy_request(
    request: Request,
    upstream_base: str,
    path_suffix: str,
    user_claims: dict[str, Any],
) -> Response:
    """
    Forward *request* to ``upstream_base + path_suffix`` and stream the
    response back.

    Args:
        request:       Incoming FastAPI request.
        upstream_base: Root URL of the target service (e.g. http://agent1-svc).
        path_suffix:   Path portion to append (e.g. /design).
        user_claims:   Decoded JWT claims from IBM App ID.

    Returns:
        FastAPI Response with upstream status, headers, and body.
    """
    if _http_client is None:
        raise HTTPException(status_code=503, detail="Proxy client not initialised.")

    # Build upstream URL
    url = f"{upstream_base.rstrip('/')}{path_suffix}"
    if request.url.query:
        url = f"{url}?{request.url.query}"

    # Filter and forward headers
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    forward_headers = {
        k: v
        for k, v in request.headers.items()
        if k.lower() not in _HOP_BY_HOP
    }
    forward_headers["X-Correlation-ID"] = correlation_id
    forward_headers["X-Forwarded-For"] = request.client.host if request.client else "unknown"
    forward_headers["X-Gateway-User"] = user_claims.get("sub", "unknown")

    # Stream body through
    body = await request.body()

    try:
        upstream_resp = await _http_client.request(
            method=request.method,
            url=url,
            headers=forward_headers,
            content=body,
        )
    except httpx.ConnectError as exc:
        raise HTTPException(status_code=502, detail=f"Upstream unreachable: {exc}") from exc
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail=f"Upstream timeout: {exc}") from exc

    # Forward response back — exclude hop-by-hop
    resp_headers = {
        k: v
        for k, v in upstream_resp.headers.items()
        if k.lower() not in _HOP_BY_HOP
    }
    resp_headers["X-Correlation-ID"] = correlation_id

    return Response(
        content=upstream_resp.content,
        status_code=upstream_resp.status_code,
        headers=resp_headers,
        media_type=upstream_resp.headers.get("content-type"),
    )
