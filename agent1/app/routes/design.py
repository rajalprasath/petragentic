"""
agent1/app/routes/design.py
────────────────────────────
POST /design — Integration Design & Automation endpoint.

Pipeline:
  1. Validate DesignRequest (Pydantic)
  2. Fetch ranked tool list from recommender (watsonx.data + governance)
  3. Generate DesignDocument (Granite-13b-chat via watsonx.ai)
  4. Persist design doc JSON to IBM COS
  5. Store catalogue entry in watsonx.data (background task — non-blocking)
  6. Return DesignResponse
"""

import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends

from shared.config import Settings
from shared.cos_client import upload_object
from shared.logging import get_logger

from agent1.app.config import get_settings
from agent1.app.models.request import DesignRequest
from agent1.app.models.response import DesignResponse, GovernanceStatus
from agent1.app.services.catalogue_store import increment_usage_count, store_design
from agent1.app.services.design_generator import generate_design
from agent1.app.services.recommender import get_ranked_tools

logger = get_logger(__name__)
router = APIRouter(prefix="/design", tags=["design"])


@router.post("", response_model=DesignResponse, status_code=200)
async def create_design(
    request: DesignRequest,
    background_tasks: BackgroundTasks,
    settings: Settings = Depends(get_settings),
) -> DesignResponse:
    """
    Accept a natural-language integration requirement and return a
    fully structured integration design document.

    - Recommends the best approved tool from the enterprise catalogue
    - Validates tool approval status against watsonx.governance
    - Generates design document using Granite-13b-chat
    - Stores the artefact in IBM COS
    - Updates the learnable catalogue in watsonx.data (background)
    """
    design_id = str(uuid.uuid4())
    logger.info("Design request received", extra={"design_id": design_id})

    # Step 1: Get ranked tool list
    ranked_tools = get_ranked_tools(settings)

    # Step 2: Generate design document
    doc, input_tokens, output_tokens, latency_ms = generate_design(
        settings=settings,
        request=request,
        ranked_tools=ranked_tools,
    )

    # Step 3: Persist to COS
    cos_key = f"designs/{design_id}.json"
    doc_json = doc.model_dump_json(indent=2)
    cos_uri = upload_object(
        settings=settings,
        bucket=settings.cos_bucket_artefacts,
        key=cos_key,
        body=doc_json,
        content_type="application/json",
    )

    # Step 4: Update catalogue (background — must not block response)
    requirement_summary = request.requirement[:200]
    background_tasks.add_task(
        store_design,
        settings, design_id, requirement_summary, doc, cos_key,
    )
    background_tasks.add_task(
        increment_usage_count,
        settings, doc.primary_tool.value,
    )

    logger.info(
        "Design request complete",
        extra={
            "design_id": design_id,
            "tool": doc.primary_tool.value,
            "latency_ms": latency_ms,
        },
    )

    return DesignResponse(
        design_id=design_id,
        created_at=datetime.now(timezone.utc),
        requirement_summary=requirement_summary,
        recommended_tool=doc.primary_tool,
        recommended_protocol=doc.protocol,
        recommended_data_format=doc.data_format,
        recommended_auth=doc.auth_method,
        governance_status=GovernanceStatus.APPROVED,
        design_document=doc,
        cos_uri=cos_uri,
        prompt_template_version=settings.agent1_prompt_template_version,
    )
