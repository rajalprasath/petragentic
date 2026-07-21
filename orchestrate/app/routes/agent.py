"""
orchestrate/app/routes/agent.py
─────────────────────────────────
Routes for the Petragentic Orchestrate agent.

Endpoints:
  POST /agent/chat               — send a message, get a Final Answer
  GET  /agent/session/{id}       — inspect a conversation session
  DELETE /agent/session/{id}     — clear a session's memory
  GET  /agent/info               — list registered tools and model info
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request

from orchestrate.app.config import OrchestrateSettings, get_settings
from orchestrate.app.models.request import ChatMessage, ClearSessionRequest
from orchestrate.app.models.response import AgentInfo, ChatResponse, SessionInfo, ToolInfo
from orchestrate.app.tools import TOOL_REGISTRY

router = APIRouter(prefix="/agent", tags=["agent"])


def _get_engine(request: Request):
    """Retrieve the ReActEngine singleton stored in app.state at startup."""
    return request.app.state.react_engine


def _get_memory(request: Request):
    """Retrieve the MemoryStore singleton stored in app.state at startup."""
    return request.app.state.memory


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Send a message to the Petragentic Orchestrate agent",
    description=(
        "The agent runs a ReAct (plan → act → observe) loop over IBM Granite, "
        "calling Agent 1 or Agent 2 skills as needed, then returns a Final Answer. "
        "Conversation history is maintained per session_id."
    ),
)
async def chat(
    body: ChatMessage,
    engine=Depends(_get_engine),
    memory=Depends(_get_memory),
    settings: OrchestrateSettings = Depends(get_settings),
) -> ChatResponse:
    """Multi-turn ReAct chat endpoint."""
    final_answer = await engine.run_turn(body.session_id, body.message)
    return ChatResponse(
        session_id=body.session_id,
        answer=final_answer,
        turn_count=memory.session_turn_count(body.session_id),
        responded_at=datetime.now(timezone.utc),
    )


@router.get(
    "/session/{session_id}",
    response_model=SessionInfo,
    summary="Inspect a conversation session",
)
async def get_session(
    session_id: str,
    memory=Depends(_get_memory),
) -> SessionInfo:
    return SessionInfo(
        session_id=session_id,
        exists=memory.session_exists(session_id),
        turn_count=memory.session_turn_count(session_id),
    )


@router.delete(
    "/session/{session_id}",
    summary="Clear a conversation session's memory",
    status_code=204,
)
async def clear_session(
    session_id: str,
    memory=Depends(_get_memory),
) -> None:
    memory.clear_session(session_id)


@router.get(
    "/info",
    response_model=AgentInfo,
    summary="List registered tools and agent configuration",
)
async def agent_info(
    settings: OrchestrateSettings = Depends(get_settings),
) -> AgentInfo:
    return AgentInfo(
        service="petragentic-orchestrate",
        model_id=settings.watsonx_model_id,
        max_react_iterations=settings.max_react_iterations,
        registered_tools=[
            ToolInfo(name=cls.name, description=cls.description)
            for cls in TOOL_REGISTRY.values()
        ],
    )
