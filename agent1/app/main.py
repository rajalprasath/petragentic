"""
agent1/app/main.py
───────────────────
FastAPI application entry point for Agent 1 — Integration Design & Automation.

Startup sequence (lifespan):
  1. Configure structured JSON logging
  2. Probe watsonx.ai connectivity (readiness gate)
  3. Probe watsonx.data connectivity (readiness gate)

Endpoints:
  GET  /health          — liveness probe (OCP)
  GET  /ready           — readiness probe (OCP)
  POST /design          — generate integration design document
  GET  /catalogue/stats — learnable catalogue statistics

Exception handlers:
  PetragenticError → structured JSON response with correlation_id
"""

import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from shared.config import Settings
from shared.exceptions import PetragenticError
from shared.logging import configure_logging, correlation_id_var, get_logger
from shared.watsonx_client import generate_text
from shared.wxdata_client import execute_query

from agent1.app.config import get_settings
from agent1.app.routes.catalogue import router as catalogue_router
from agent1.app.routes.design import router as design_router

logger = get_logger(__name__)

# Module-level readiness flag
_ready: dict = {"status": False, "reason": "starting"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan: startup checks then yield to serve traffic."""
    settings: Settings = get_settings()
    configure_logging(settings.service_name, settings.environment, settings.log_level)
    logger.info("Agent 1 starting", extra={"environment": settings.environment})

    # ── Probe watsonx.ai ─────────────────────────────────────────────────────
    try:
        # A minimal generate call to validate credentials and endpoint reachability
        generate_text(settings, settings.watsonx_model_chat, "ping", {"max_new_tokens": 1})
        logger.info("watsonx.ai reachable")
    except Exception as exc:
        logger.error("watsonx.ai unreachable at startup", extra={"error": str(exc)})
        _ready["reason"] = "watsonx_unreachable"

    # ── Probe watsonx.data ───────────────────────────────────────────────────
    try:
        execute_query(settings, "SELECT 1")
        logger.info("watsonx.data reachable")
        _ready["status"] = True
        _ready["reason"] = "ok"
    except Exception as exc:
        logger.error("watsonx.data unreachable at startup", extra={"error": str(exc)})
        if _ready["reason"] == "starting":
            _ready["reason"] = "wxdata_unreachable"

    logger.info("Agent 1 ready", extra={"ready": _ready["status"]})
    yield
    logger.info("Agent 1 shutting down")


# ── Application ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="Agent 1 — Integration Design & Automation",
    description="Generate enterprise integration design documents using watsonx.ai + Granite.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


# ── Middleware — correlation ID propagation ───────────────────────────────────

@app.middleware("http")
async def correlation_middleware(request: Request, call_next):
    cid = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    token = correlation_id_var.set(cid)
    try:
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = cid
        return response
    finally:
        correlation_id_var.reset(token)


# ── Exception handler ─────────────────────────────────────────────────────────

@app.exception_handler(PetragenticError)
async def petragentic_handler(request: Request, exc: PetragenticError) -> JSONResponse:
    logger.error(
        "PetragenticError",
        extra={"status_code": exc.status_code, "message": exc.message},
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.message,
            "detail": exc.detail,
            "correlation_id": request.headers.get("X-Correlation-ID", "-"),
        },
    )


# ── Ops endpoints ─────────────────────────────────────────────────────────────

@app.get("/health", tags=["ops"], summary="Liveness probe")
async def health():
    return {"status": "ok", "service": "agent1"}


@app.get("/ready", tags=["ops"], summary="Readiness probe")
async def ready():
    if _ready["status"]:
        return {"status": "ready", "service": "agent1"}
    return JSONResponse(
        status_code=503,
        content={"status": "not_ready", "reason": _ready["reason"]},
    )


# ── Business routers ──────────────────────────────────────────────────────────

app.include_router(design_router)
app.include_router(catalogue_router)
