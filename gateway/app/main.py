"""
gateway/app/main.py
────────────────────
FastAPI application entry point for the Petragentic API Gateway.

Responsibilities:
  1. IBM App ID JWT authentication (every route is protected)
  2. Scope-based authorisation (design:read/write, audit:read/write)
  3. Per-subject rate limiting (default 60 req/min via slowapi)
  4. Async reverse-proxy to Agent 1 and Agent 2 ClusterIP services
  5. Correlation ID propagation (X-Correlation-ID header)
  6. Structured JSON logging

Endpoints:
  GET  /health             — liveness probe (unauthenticated)
  GET  /ready              — readiness probe (unauthenticated)
  POST /api/v1/design      → Agent 1
  GET  /api/v1/catalogue/stats → Agent 1
  POST /api/v1/validate    → Agent 2
  GET  /api/v1/report/{id} → Agent 2
  GET  /api/v1/report/{id}/html → Agent 2
"""

import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from gateway.app.config import GatewaySettings, get_settings
from gateway.app.proxy import close_client, init_client
from gateway.app.routes.agent1 import router as agent1_router
from gateway.app.routes.agent2 import router as agent2_router
from gateway.app.routes.orchestrate import router as orchestrate_router

# ── Rate limiter (keyed by remote IP; can be switched to JWT sub in future) ───
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: initialise async HTTP client.  Shutdown: drain connections."""
    settings: GatewaySettings = get_settings()

    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format='{"time":"%(asctime)s","level":"%(levelname)s","service":"gateway","msg":"%(message)s"}',
    )
    logger = logging.getLogger("gateway")
    logger.info("Gateway starting — environment=%s", settings.environment)

    init_client(settings)
    logger.info(
        "Upstream targets: agent1=%s agent2=%s",
        settings.agent1_url,
        settings.agent2_url,
    )

    yield

    logger.info("Gateway shutting down — draining HTTP client")
    await close_client()


# ── Application ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="Petragentic API Gateway",
    description=(
        "IBM App ID–authenticated reverse proxy to Agent 1 (Integration Design) "
        "and Agent 2 (Security Compliance)."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── Rate limiting ─────────────────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# ── Middleware — correlation ID propagation ───────────────────────────────────

@app.middleware("http")
async def correlation_middleware(request: Request, call_next):
    cid = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = cid
    return response


# ── Ops endpoints (unauthenticated) ──────────────────────────────────────────

@app.get("/health", tags=["ops"], summary="Liveness probe")
async def health():
    return {"status": "ok", "service": "gateway"}


@app.get("/ready", tags=["ops"], summary="Readiness probe")
async def ready():
    """
    Readiness check — returns 200 when the httpx proxy client is initialised.
    If the agent services are down the gateway is still ready; their
    individual /ready probes govern their own traffic.
    """
    from gateway.app.proxy import _http_client  # noqa: PLC0415
    if _http_client is not None:
        return {"status": "ready", "service": "gateway"}
    return JSONResponse(status_code=503, content={"status": "not_ready", "reason": "client_not_initialised"})


# ── Business routers ──────────────────────────────────────────────────────────

app.include_router(agent1_router)
app.include_router(agent2_router)
app.include_router(orchestrate_router)
