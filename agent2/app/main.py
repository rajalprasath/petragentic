"""
agent2/app/main.py
───────────────────
FastAPI application entry point for Agent 2 — Security Compliance & Audit.

Endpoints:
  GET  /health               — liveness probe
  GET  /ready                — readiness probe
  POST /validate             — run a compliance audit scan
  GET  /report/{scan_id}     — retrieve a completed scan report from COS
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

from agent2.app.config import get_settings
from agent2.app.routes.report import router as report_router
from agent2.app.routes.validate import router as validate_router

logger = get_logger(__name__)
_ready: dict = {"status": False, "reason": "starting"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings: Settings = get_settings()
    configure_logging(settings.service_name, settings.environment, settings.log_level)
    logger.info("Agent 2 starting", extra={"environment": settings.environment})

    try:
        generate_text(settings, settings.watsonx_model_code, "ping", {"max_new_tokens": 1})
        logger.info("watsonx.ai reachable")
    except Exception as exc:
        logger.error("watsonx.ai unreachable at startup", extra={"error": str(exc)})
        _ready["reason"] = "watsonx_unreachable"

    try:
        execute_query(settings, "SELECT 1")
        logger.info("watsonx.data reachable")
        _ready["status"] = True
        _ready["reason"] = "ok"
    except Exception as exc:
        logger.error("watsonx.data unreachable at startup", extra={"error": str(exc)})
        if _ready["reason"] == "starting":
            _ready["reason"] = "wxdata_unreachable"

    logger.info("Agent 2 ready", extra={"ready": _ready["status"]})
    yield
    logger.info("Agent 2 shutting down")


app = FastAPI(
    title="Agent 2 — Security Compliance & Audit",
    description="Windows server security baseline audit with CIS/NIST mapping and PS1 remediation.",
    version="1.0.0",
    lifespan=lifespan,
)


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


@app.exception_handler(PetragenticError)
async def petragentic_handler(request: Request, exc: PetragenticError) -> JSONResponse:
    logger.error("PetragenticError", extra={"status_code": exc.status_code, "message": exc.message})
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.message,
            "detail": exc.detail,
            "correlation_id": request.headers.get("X-Correlation-ID", "-"),
        },
    )


@app.get("/health", tags=["ops"])
async def health():
    return {"status": "ok", "service": "agent2"}


@app.get("/ready", tags=["ops"])
async def ready():
    if _ready["status"]:
        return {"status": "ready", "service": "agent2"}
    return JSONResponse(
        status_code=503,
        content={"status": "not_ready", "reason": _ready["reason"]},
    )


app.include_router(validate_router)
app.include_router(report_router)
