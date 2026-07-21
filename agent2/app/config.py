"""
agent2/app/config.py
─────────────────────
Agent 2 service configuration.
"""

from shared.config import Settings
from functools import lru_cache


class Agent2Settings(Settings):
    service_name: str = "agent2"
    port: int = 8002


@lru_cache()
def get_settings() -> Agent2Settings:
    return Agent2Settings()
