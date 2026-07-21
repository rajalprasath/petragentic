"""
shared/config.py
────────────────
Centralised configuration via environment variables.
All IBM Cloud and watsonx credentials are declared here.
Services call get_settings() which is cached for the process lifetime.

Private endpoints are used for all IBM Cloud services so that no
traffic leaves the VPC over the public internet.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── IBM Cloud identity ────────────────────────────────────────────────────
    ibm_cloud_api_key: str
    ibm_cloud_region: str = "us-south"

    # ── watsonx.ai (private endpoint) ────────────────────────────────────────
    watsonx_url: str = "https://private.us-south.ml.cloud.ibm.com"
    watsonx_project_id: str
    watsonx_model_chat: str = "ibm/granite-13b-chat-v2"
    watsonx_model_code: str = "ibm/granite-34b-code-instruct-v1"
    watsonx_max_new_tokens: int = 2048
    watsonx_temperature: float = 0.0          # greedy by default

    # ── watsonx.data (Presto REST, private endpoint) ─────────────────────────
    wxdata_presto_url: str                     # e.g. https://private.wxdata...
    wxdata_auth_token: str
    wxdata_catalog: str = "petragentic"
    wxdata_schema: str = "main"

    # ── watsonx.governance (AI Factsheets, private endpoint) ─────────────────
    wxgov_url: str
    wxgov_space_id: str

    # ── IBM Cloud Object Storage (private endpoint) ──────────────────────────
    cos_endpoint: str = "https://s3.private.us-south.cloud-object-storage.appdomain.cloud"
    cos_api_key: str
    cos_instance_id: str
    cos_bucket_artefacts: str = "petragentic-artefacts"
    cos_bucket_data: str = "petragentic-data"

    # ── IBM Secrets Manager (private endpoint) ───────────────────────────────
    secrets_manager_url: str
    secrets_manager_instance_id: str

    # ── Service identity ─────────────────────────────────────────────────────
    service_name: str = "petragentic"
    log_level: str = "INFO"
    environment: str = "production"

    # ── Agent 1 specific ─────────────────────────────────────────────────────
    agent1_prompt_template_version: str = "v1.0"
    catalogue_min_usage_for_ranking: int = 3   # min uses before frequency ranking kicks in

    # ── Agent 2 specific ─────────────────────────────────────────────────────
    agent2_prompt_template_version: str = "v1.0"
    winrm_transport: str = "ntlm"              # ntlm | kerberos | ssl
    winrm_port: int = 5985
    winrm_timeout_sec: int = 30
    ps_syntax_check: bool = True               # validate PS1 before returning

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache()
def get_settings() -> Settings:
    """Return the cached Settings singleton. One instance per process."""
    return Settings()
