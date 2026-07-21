"""
shared/governance_logger.py
────────────────────────────
Logs every LLM inference call to watsonx.governance AI Factsheets.

Design principles:
  - NON-BLOCKING: a failure here MUST NOT break the main request path.
    Failures are logged as WARNING and silently swallowed.
  - Called by both agent1 and agent2 after every generate_text() invocation.
  - Records: model_id, prompt_template_version, token counts, latency,
    SHA-256 output hash, and any caller-provided metadata.

Usage:
    log_inference(
        settings=settings,
        agent_id="agent1-design",
        model_id=settings.watsonx_model_chat,
        prompt_template_version=settings.agent1_prompt_template_version,
        input_tokens=320,
        output_tokens=1100,
        latency_ms=2340,
        output_text=generated_doc,
        metadata={"tool_recommended": "NiFi", "scan_id": None},
    )
"""

import hashlib
import time

import requests

from shared.config import Settings
from shared.logging import get_logger

logger = get_logger(__name__)

_FACTSHEETS_PATH = "/v2/ai_factsheets/inference_records"
_REQUEST_TIMEOUT_SEC = 5


def log_inference(
    settings: Settings,
    agent_id: str,
    model_id: str,
    prompt_template_version: str,
    input_tokens: int,
    output_tokens: int,
    latency_ms: int,
    output_text: str,
    metadata: dict | None = None,
) -> None:
    """
    Post an inference record to watsonx.governance AI Factsheets.
    Failures are non-fatal — logged as WARNING.
    """
    payload = {
        "space_id": settings.wxgov_space_id,
        "agent_id": agent_id,
        "model_id": model_id,
        "prompt_template_version": prompt_template_version,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "latency_ms": latency_ms,
        "output_hash": hashlib.sha256(output_text.encode()).hexdigest(),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        **(metadata or {}),
    }
    url = f"{settings.wxgov_url}{_FACTSHEETS_PATH}"
    try:
        resp = requests.post(
            url,
            json=payload,
            headers={
                "Authorization": f"Bearer {settings.ibm_cloud_api_key}",
                "Content-Type": "application/json",
            },
            timeout=_REQUEST_TIMEOUT_SEC,
        )
        resp.raise_for_status()
        logger.debug(
            "AI Factsheets record written",
            extra={"agent_id": agent_id, "model_id": model_id},
        )
    except Exception as exc:
        logger.warning(
            "AI Factsheets write failed (non-fatal)",
            extra={"agent_id": agent_id, "error": str(exc)},
        )


def check_tool_approval(settings: Settings, tool_name: str) -> str:
    """
    Query watsonx.governance for the approval status of an integration tool.

    Returns: "Approved" | "Pending" | "Rejected" | "Unknown"
    Raises:  Never — returns "Unknown" on any failure.
    """
    url = f"{settings.wxgov_url}/v2/governance/tool_registry/{tool_name}/status"
    try:
        resp = requests.get(
            url,
            headers={"Authorization": f"Bearer {settings.ibm_cloud_api_key}"},
            timeout=_REQUEST_TIMEOUT_SEC,
        )
        resp.raise_for_status()
        return resp.json().get("status", "Unknown")
    except Exception as exc:
        logger.warning(
            "Governance tool approval check failed",
            extra={"tool": tool_name, "error": str(exc)},
        )
        return "Unknown"
