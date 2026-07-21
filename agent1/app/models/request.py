"""
agent1/app/models/request.py
─────────────────────────────
Pydantic request schemas for Agent 1 — Integration Design & Automation.
"""

from enum import Enum
from pydantic import BaseModel, Field, field_validator


class IntegrationPattern(str, Enum):
    """Broad integration pattern categories used to guide tool selection."""
    DATA_PIPELINE = "data_pipeline"
    API_INTEGRATION = "api_integration"
    FILE_TRANSFER = "file_transfer"
    EVENT_STREAMING = "event_streaming"
    ETL = "etl"
    UNKNOWN = "unknown"


class DesignRequest(BaseModel):
    """
    Intake schema for Agent 1.

    The 'requirement' field is the raw natural-language description provided
    by the integration architect or business analyst.
    """
    requirement: str = Field(
        ...,
        min_length=20,
        max_length=4000,
        description="Natural-language integration requirement",
        examples=[
            "We need to move daily CSV exports from our SAP ERP system to an IBM Db2 "
            "data warehouse on IBM Cloud. The files are ~500 MB each. Security requires "
            "certificate-based authentication and end-to-end encryption."
        ],
    )
    pattern_hint: IntegrationPattern = Field(
        default=IntegrationPattern.UNKNOWN,
        description="Optional hint about the broad integration pattern",
    )
    requester: str | None = Field(
        default=None,
        max_length=100,
        description="Name or ID of the person submitting the request",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Optional tags for catalogue search and filtering",
    )

    @field_validator("requirement")
    @classmethod
    def requirement_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("requirement must not be blank")
        return v.strip()
