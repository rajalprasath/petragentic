"""
orchestrate/app/models/request.py
───────────────────────────────────
Pydantic request schemas for the Orchestrate service.
"""

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """A single user message sent to the Orchestrate agent."""
    session_id: str = Field(
        ...,
        description="Stable session identifier — use a UUID per user conversation",
        examples=["sess-7a2f9c4e-1234-5678-abcd-ef0123456789"],
    )
    message: str = Field(
        ...,
        min_length=1,
        max_length=4000,
        description="User's natural-language message",
        examples=["Design an integration between SAP ECC and IBM Db2 Warehouse"],
    )


class ClearSessionRequest(BaseModel):
    """Request body for clearing a conversation session."""
    session_id: str = Field(..., description="Session to clear")
