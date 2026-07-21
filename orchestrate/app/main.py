"""
orchestrate/app/main.py
────────────────────────
FastAPI application entry point for the Petragentic Orchestrate service.

Startup sequence (lifespan):
  1. Configure structured JSON logging
  2. Probe watsonx.ai connectivity (readiness gate)
  3. Probe agent1 / agent2 reachability
  4. Initialise MemoryStore and ReActEngine — stored in app.state

Endpoints:
  GET  /health          — liveness probe (OCP)
  GET  /ready           — readiness probe (OCP)
  POST /agent/chat      — multi-turn ReAct conversation
  GET  /agent/session/{id} — inspect session
  DELETE /agent/session/{id} — clear session
  GET  /agent/info      — list tools
"""

import logging
import uuid
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from orchestrate.app.config import OrchestrateSettings, get_settings
from orchestrate.app.memory import MemoryStore
from orchestrate.app.react_engine import ReActEngine
from orchestrate.app.routes.agent import router as agent_router

logger = logging.getLogger("orchestrate")

_ready: dict = {"status": False, "reason": "starting"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: initialise engine + memory.  Shutdown: clean up."""
    settings: OrchestrateSettings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format=(
            '{"time":"%(asctime)s","level":"%(levelname)s",'
            '"service":"orchestrate","msg":"%(message)s"}'
        ),
    )
    logger.info("Orchestrate service starting — env=%s", settings.environment)

    # ── Probe watsonx.ai ──────────────────────────────────────────────────────
    try:
        from ibm_watsonx_ai import APIClient, Credentials
        creds = Credentials(url=settings.watsonx_url, api_key=settings.ibm_cloud_api_key)
        APIClient(creds)           # lightweight credential check
        logger.info("watsonx.ai credentials validated")
    except Exception as exc:
        logger.error("watsonx.ai probe failed: %s", exc)
        _ready["reason"] = "watsonx_unreachable"

    # ── Probe agent services ──────────────────────────────────────────────────
    for name, base_url in [("agent1", settings.agent1_url), ("agent2", settings.agent2_url)]:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{base_url}/health")
                resp.raise_for_status()
            logger.info("%s reachable", name)
        except Exception as exc:
            logger.warning("%s probe failed (non-fatal): %s", name, exc)

    # ── Initialise singletons ─────────────────────────────────────────────────
    memory = MemoryStore(max_turns=settings.max_conversation_turns)
    engine = ReActEngine(settings=settings, memory=memory)

    app.state.memory = memory
    app.state.react_engine = engine

    _ready["status"] = True
    _ready["reason"] = "ok"
    logger.info("Orchestrate service ready")

    yield

    logger.info("Orchestrate service shutting down")


# ── Application ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="Petragentic — Orchestrate Agent",
    description=(
        "Multi-turn ReAct orchestration layer. Drives IBM Granite over "
        "Integration Design (Agent 1) and Security Compliance (Agent 2) skills."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


# ── Middleware — correlation ID ───────────────────────────────────────────────

@app.middleware("http")
async def correlation_middleware(request: Request, call_next):
    cid = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = cid
    return response


# ── Ops endpoints ─────────────────────────────────────────────────────────────

@app.get("/health", tags=["ops"], summary="Liveness probe")
async def health():
    return {"status": "ok", "service": "orchestrate"}


@app.get("/ready", tags=["ops"], summary="Readiness probe")
async def ready():
    if _ready["status"]:
        return {"status": "ready", "service": "orchestrate"}
    return JSONResponse(
        status_code=503,
        content={"status": "not_ready", "reason": _ready["reason"]},
    )


# ── Business router ───────────────────────────────────────────────────────────

app.include_router(agent_router)
