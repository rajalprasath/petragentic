"""
shared/watsonx_client.py
────────────────────────
Factory and helper for ibm_watsonx_ai ModelInference.

Features:
  - lru_cache per (url, project_id, model_id) — one client per model per process
  - Greedy decoding by default; callers can override params
  - Detects token quota errors and raises WatsonxQuotaError (HTTP 429)
  - Detects and raises WatsonxInferenceError for all other failures
  - Logs every call: model_id, prompt length, response length, latency_ms

Usage:
    text = generate_text(settings, settings.watsonx_model_chat, prompt)
    code = generate_text(settings, settings.watsonx_model_code, prompt)
"""

import time
from functools import lru_cache

from ibm_watsonx_ai import Credentials
from ibm_watsonx_ai.foundation_models import ModelInference
from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as Params

from shared.config import Settings
from shared.exceptions import WatsonxInferenceError, WatsonxQuotaError
from shared.logging import get_logger

logger = get_logger(__name__)

_DEFAULT_PARAMS = {
    Params.DECODING_METHOD: "greedy",
    Params.MAX_NEW_TOKENS: 2048,
    Params.REPETITION_PENALTY: 1.05,
    Params.STOP_SEQUENCES: ["</output>", "```\n\n"],
}


@lru_cache(maxsize=8)
def _get_client(api_key: str, url: str, project_id: str, model_id: str) -> ModelInference:
    """Return (and cache) a ModelInference client for the given model."""
    credentials = Credentials(url=url, api_key=api_key)
    return ModelInference(
        model_id=model_id,
        credentials=credentials,
        project_id=project_id,
        params=_DEFAULT_PARAMS,
    )


def generate_text(
    settings: Settings,
    model_id: str,
    prompt: str,
    params: dict | None = None,
) -> str:
    """
    Call a Granite model and return the generated text.

    Raises:
        WatsonxQuotaError   — if the account token quota is exhausted (429)
        WatsonxInferenceError — for all other inference failures
    """
    client = _get_client(
        api_key=settings.ibm_cloud_api_key,
        url=settings.watsonx_url,
        project_id=settings.watsonx_project_id,
        model_id=model_id,
    )
    t0 = time.monotonic()
    try:
        result: str = client.generate_text(prompt=prompt, params=params or _DEFAULT_PARAMS)
        latency_ms = int((time.monotonic() - t0) * 1000)
        logger.info(
            "Granite inference complete",
            extra={
                "model_id": model_id,
                "prompt_chars": len(prompt),
                "response_chars": len(result),
                "latency_ms": latency_ms,
            },
        )
        return result
    except Exception as exc:
        msg = str(exc)
        if "429" in msg or "quota" in msg.lower():
            raise WatsonxQuotaError()
        raise WatsonxInferenceError(message=msg, model_id=model_id)
