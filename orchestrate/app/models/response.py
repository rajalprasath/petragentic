"""
orchestrate/app/models/response.py
────────────────────────────────────
Pydantic response schemas for the Orchestrate service.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class ChatResponse(BaseModel):
    """Response from POST /agent/chat."""
    session_id: str
    answer: str = Field(..., description="Final Answer produced by the ReAct engine")
    turn_count: int = Field(..., description="Total turns in the session after this exchange")
    responded_at: datetime


class SessionInfo(BaseModel):
    """Response from GET /agent/session/{session_id}."""
    session_id: str
    exists: bool
    turn_count: int


class ToolInfo(BaseModel):
    """Metadata about a single registered tool."""
    name: str
    description: str


class AgentInfo(BaseModel):
    """Response from GET /agent/info."""
    service: str
    model_id: str
    max_react_iterations: int
    registered_tools: list[ToolInfo]
