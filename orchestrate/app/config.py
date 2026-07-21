"""
orchestrate/app/config.py
──────────────────────────
Configuration for the Petragentic Orchestrate service.

Adds Orchestrate-specific settings on top of the shared platform settings.
The Orchestrate service needs:
  - watsonx.ai credentials (for the ReAct loop LLM calls)
  - agent1 / agent2 internal ClusterIP URLs (skill call targets)
  - Conversation memory settings
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class OrchestrateSettings(BaseSettings):
    # ── IBM Cloud identity ────────────────────────────────────────────────────
    ibm_cloud_api_key: str
    ibm_cloud_region: str = "us-south"

    # ── watsonx.ai (for ReAct loop) ───────────────────────────────────────────
    watsonx_url: str = "https://private.us-south.ml.cloud.ibm.com"
    watsonx_project_id: str
    watsonx_model_id: str = "ibm/granite-13b-chat-v2"
    watsonx_max_new_tokens: int = 2048
    watsonx_temperature: float = 0.0
    watsonx_repetition_penalty: float = 1.05

    # ── Upstream skill endpoints (internal ClusterIP) ─────────────────────────
    agent1_url: str = "http://agent1-svc"
    agent2_url: str = "http://agent2-svc"

    # ── Conversation memory ───────────────────────────────────────────────────
    max_conversation_turns: int = 20       # max turns stored per session
    max_react_iterations: int = 8          # max plan→act→observe cycles per turn

    # ── Service identity ─────────────────────────────────────────────────────
    service_name: str = "orchestrate"
    log_level: str = "INFO"
    environment: str = "production"

    # ── Upstream HTTP client timeouts (seconds) ───────────────────────────────
    skill_connect_timeout: float = 5.0
    skill_read_timeout: float = 120.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache()
def get_settings() -> OrchestrateSettings:
    """Return the cached OrchestrateSettings singleton."""
    return OrchestrateSettings()
