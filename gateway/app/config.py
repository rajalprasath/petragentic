"""
gateway/app/config.py
─────────────────────
Gateway-specific configuration.  Shared watsonx / COS credentials are not
needed here — the gateway only handles inbound auth and upstream proxying.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class GatewaySettings(BaseSettings):
    # ── IBM App ID (OIDC) ─────────────────────────────────────────────────────
    appid_issuer_url: str           # e.g. https://<region>.appid.cloud.ibm.com/oauth/v4/<tenantId>
    appid_jwks_url: str             # e.g. <issuer_url>/publickeys
    appid_audience: str             # Client ID registered in App ID

    # ── Upstream services (internal ClusterIP names, ROKS) ───────────────────
    agent1_url: str = "http://agent1-svc"          # resolves inside petragentic namespace
    agent2_url: str = "http://agent2-svc"
    orchestrate_url: str = "http://orchestrate-svc"

    # ── Rate limiting (requests/minute per authenticated subject) ─────────────
    rate_limit_per_minute: int = 60

    # ── Service identity ─────────────────────────────────────────────────────
    service_name: str = "gateway"
    log_level: str = "INFO"
    environment: str = "production"

    # ── Upstream HTTP client timeouts (seconds) ───────────────────────────────
    upstream_connect_timeout: float = 5.0
    upstream_read_timeout: float = 120.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache()
def get_settings() -> GatewaySettings:
    """Return the cached GatewaySettings singleton."""
    return GatewaySettings()
