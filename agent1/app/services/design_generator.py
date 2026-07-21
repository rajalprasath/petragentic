"""
agent1/app/services/design_generator.py
─────────────────────────────────────────
Orchestrates the full design document generation pipeline for Agent 1.

Steps:
  1. Build the structured Granite prompt (prompt_builder)
  2. Call Granite-13b-chat via shared/watsonx_client
  3. Parse the JSON response into a DesignDocument Pydantic model
  4. Check the primary_tool against watsonx.governance
  5. Log the inference to watsonx.governance AI Factsheets
  6. Return the populated DesignDocument

Raises:
  WatsonxParseError       — if the LLM output is not valid JSON or doesn't
                            match the DesignDocument schema
  GovernanceCheckError    — if the recommended tool has status "Rejected"
  WatsonxInferenceError   — propagated from watsonx_client
"""

import json
import re
import time
from datetime import datetime, timezone

from shared.config import Settings
from shared.exceptions import GovernanceCheckError, WatsonxParseError
from shared.governance_logger import check_tool_approval, log_inference
from shared.logging import get_logger
from shared.watsonx_client import generate_text

from agent1.app.models.request import DesignRequest
from agent1.app.models.response import (
    DesignDocument,
    GovernanceStatus,
    ToolRecommendation,
)
from agent1.app.services.prompt_builder import build_design_prompt

logger = get_logger(__name__)

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def _extract_json(raw: str) -> str:
    """
    Extract the JSON object from the LLM output.
    Handles: raw JSON, markdown fences, leading/trailing text.
    """
    # Try fence first
    match = _JSON_FENCE_RE.search(raw)
    if match:
        return match.group(1).strip()
    # Try to find first '{' ... last '}'
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start >= 0 and end > start:
        return raw[start:end]
    return raw.strip()


def generate_design(
    settings: Settings,
    request: DesignRequest,
    ranked_tools: list[ToolRecommendation],
) -> tuple[DesignDocument, int, int, int]:
    """
    Generate a DesignDocument from the ranked tool list and NL requirement.

    Returns: (DesignDocument, input_tokens, output_tokens, latency_ms)
    Raises:  WatsonxParseError, GovernanceCheckError, WatsonxInferenceError
    """
    prompt = build_design_prompt(request, ranked_tools)
    t0 = time.monotonic()

    raw_output = generate_text(
        settings=settings,
        model_id=settings.watsonx_model_chat,
        prompt=prompt,
    )

    latency_ms = int((time.monotonic() - t0) * 1000)
    # Rough token estimate (watsonx SDK does not return token counts in all versions)
    input_tokens = len(prompt.split())
    output_tokens = len(raw_output.split())

    json_str = _extract_json(raw_output)

    try:
        raw_dict = json.loads(json_str)
    except json.JSONDecodeError as exc:
        raise WatsonxParseError(
            message=f"LLM output is not valid JSON: {exc}",
            raw_output=raw_output,
        )

    # Governance check on the primary tool recommended by the LLM
    primary_tool_name = raw_dict.get("primary_tool", "")
    gov_status_str = check_tool_approval(settings, primary_tool_name)

    if gov_status_str == GovernanceStatus.REJECTED:
        raise GovernanceCheckError(tool=primary_tool_name, status=gov_status_str)

    # Enrich tool_alternatives with governance status from the pre-ranked list
    ranked_map = {r.tool.value: r for r in ranked_tools}
    if "tool_alternatives" in raw_dict:
        for alt in raw_dict["tool_alternatives"]:
            if alt.get("tool") in ranked_map:
                alt["governance_status"] = ranked_map[alt["tool"]].governance_status.value
                alt["usage_count"] = ranked_map[alt["tool"]].usage_count

    try:
        doc = DesignDocument.model_validate(raw_dict)
    except Exception as exc:
        raise WatsonxParseError(
            message=f"LLM output does not match DesignDocument schema: {exc}",
            raw_output=raw_output,
        )

    # Log to watsonx.governance AI Factsheets
    log_inference(
        settings=settings,
        agent_id="agent1-design",
        model_id=settings.watsonx_model_chat,
        prompt_template_version=settings.agent1_prompt_template_version,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        latency_ms=latency_ms,
        output_text=raw_output,
        metadata={
            "tool_recommended": primary_tool_name,
            "governance_status": gov_status_str,
        },
    )

    logger.info(
        "Design document generated",
        extra={
            "tool": primary_tool_name,
            "latency_ms": latency_ms,
            "governance_status": gov_status_str,
        },
    )
    return doc, input_tokens, output_tokens, latency_ms
