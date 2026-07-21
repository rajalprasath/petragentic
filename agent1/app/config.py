"""
agent1/app/config.py
─────────────────────
Agent 1 service configuration.
Extends the shared Settings with agent1-specific env vars.
"""

from shared.config import Settings, get_settings as _base_get_settings
from functools import lru_cache


class Agent1Settings(Settings):
    """Agent 1 configuration — inherits all shared settings."""
    service_name: str = "agent1"
    # Agent 1 port (informational; uvicorn uses PORT env var in production)
    port: int = 8001


@lru_cache()
def get_settings() -> Agent1Settings:
    return Agent1Settings()
