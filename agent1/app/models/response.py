"""
agent1/app/models/response.py
──────────────────────────────
Pydantic response schemas for Agent 1 — Integration Design & Automation.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


# ── Enumerations ──────────────────────────────────────────────────────────────

class ApprovedTool(str, Enum):
    """Approved integration tools as per the enterprise tool catalogue."""
    IBM_REDWOOD   = "IBM Redwood"
    WEBMETHODS    = "webMethods"
    APACHE_NIFI   = "Apache NiFi"
    AZURE_LOGIC   = "Azure Logic Apps"


class RecommendedProtocol(str, Enum):
    REST    = "REST"
    SOAP    = "SOAP"
    FILE    = "file-based"
    AMQP    = "AMQP"
    KAFKA   = "Kafka"
    SFTP    = "SFTP"
    JMS     = "JMS"


class RecommendedDataFormat(str, Enum):
    JSON    = "JSON"
    XML     = "XML"
    CSV     = "CSV"
    AVRO    = "Avro"
    PARQUET = "Parquet"


class RecommendedAuthMethod(str, Enum):
    OAUTH2          = "OAuth 2.0"
    MTLS            = "mTLS / certificate"
    API_KEY         = "API key"
    SERVICE_PRINCIPAL = "service principal / managed identity"
    BASIC           = "basic auth"


class GovernanceStatus(str, Enum):
    APPROVED  = "Approved"
    PENDING   = "Pending"
    REJECTED  = "Rejected"
    UNKNOWN   = "Unknown"


# ── Sub-schemas ───────────────────────────────────────────────────────────────

class ToolRecommendation(BaseModel):
    """Ranked tool recommendation with governance check result."""
    rank: int = Field(..., description="1 = top recommendation")
    tool: ApprovedTool
    rationale: str = Field(..., description="Why this tool fits the requirement")
    governance_status: GovernanceStatus
    usage_count: int = Field(default=0, description="Historical usage count in integration_catalogue")


class AuthRecommendation(BaseModel):
    """Authentication pattern recommendation."""
    method: RecommendedAuthMethod
    rationale: str
    config_notes: str = Field(
        default="",
        description="Specific configuration notes (e.g. token endpoint, cert requirements)",
    )


class ArchitecturalDecision(BaseModel):
    """A single architectural decision record within the design document."""
    decision_id: str
    title: str
    context: str
    decision: str
    consequences: str
    status: str = "Accepted"


class SecurityConsideration(BaseModel):
    """Security concern identified for the integration."""
    area: str                            # e.g. "Transport Security", "Authentication"
    risk: str
    mitigation: str
    reference: str = ""                  # e.g. "NIST 800-53 SC-8"


class DesignDocument(BaseModel):
    """
    Full technical design document produced by Agent 1.
    This is the primary output artefact stored in IBM COS.
    """
    # Core recommendation fields
    primary_tool: ApprovedTool
    protocol: RecommendedProtocol
    data_format: RecommendedDataFormat
    auth_method: RecommendedAuthMethod

    # Narrative sections
    executive_summary: str
    integration_overview: str
    data_flow_description: str
    implementation_steps: list[str]
    security_considerations: list[SecurityConsideration]
    architectural_decisions: list[ArchitecturalDecision]
    testing_strategy: str
    open_issues: list[str] = Field(default_factory=list)

    # Alternative tool analysis
    tool_alternatives: list[ToolRecommendation]
    auth_alternatives: list[AuthRecommendation]


# ── Top-level response schemas ────────────────────────────────────────────────

class DesignResponse(BaseModel):
    """
    Full response from POST /design.
    Contains the recommendation summary, the full design document,
    and the COS artefact reference.
    """
    design_id: str = Field(..., description="UUID for this design artefact")
    created_at: datetime
    requirement_summary: str

    # Top-level recommendations (summary of the design doc)
    recommended_tool: ApprovedTool
    recommended_protocol: RecommendedProtocol
    recommended_data_format: RecommendedDataFormat
    recommended_auth: RecommendedAuthMethod
    governance_status: GovernanceStatus

    # Full design document
    design_document: DesignDocument

    # Storage reference
    cos_uri: str = Field(..., description="COS object URI for the persisted design document")
    prompt_template_version: str


class CatalogueEntry(BaseModel):
    """A single row from the integration_catalogue table."""
    id: str
    timestamp: datetime
    requirement_summary: str
    tool_chosen: str
    protocol: str
    data_format: str
    auth_method: str
    cos_object_key: str
    usage_count: int


class CatalogueStats(BaseModel):
    """Response from GET /catalogue/stats."""
    total_designs: int
    tool_frequency: dict[str, int] = Field(
        ..., description="Design count per tool, sorted descending"
    )
    protocol_frequency: dict[str, int]
    auth_frequency: dict[str, int]
    top_tool: str | None
    recent_entries: list[CatalogueEntry]
