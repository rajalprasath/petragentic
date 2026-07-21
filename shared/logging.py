"""
shared/logging.py
─────────────────
Structured JSON logging for IBM Log Analysis (Cloud Logs).

Every log line is a single JSON object containing:
  timestamp, level, service, environment, correlation_id, logger, message
plus any caller-provided 'extra' fields.

IBM Log Analysis ingests stdout/stderr from ROKS pods automatically
via the Fluent Bit DaemonSet. JSON fields become queryable attributes.

Usage:
    from shared.logging import get_logger, configure_logging
    logger = get_logger(__name__)
    logger.info("Design generated", extra={"tool": "NiFi", "latency_ms": 1240})
"""

import json
import logging
import sys
from contextvars import ContextVar
from datetime import datetime, timezone

# Holds the current request correlation ID — set by gateway middleware,
# propagated into every log line automatically.
correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="-")


class _JSONFormatter(logging.Formatter):
    def __init__(self, service_name: str, environment: str) -> None:
        super().__init__()
        self._service = service_name
        self._env = environment

    def format(self, record: logging.LogRecord) -> str:
        entry: dict = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "service": self._service,
            "environment": self._env,
            "correlation_id": correlation_id_var.get(),
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        # Merge any extra fields passed by the caller
        for key, value in record.__dict__.items():
            if key not in (
                "args", "asctime", "created", "exc_info", "exc_text",
                "filename", "funcName", "id", "levelname", "levelno",
                "lineno", "module", "msecs", "message", "msg", "name",
                "pathname", "process", "processName", "relativeCreated",
                "stack_info", "thread", "threadName",
            ):
                entry[key] = value
        return json.dumps(entry, default=str)


def configure_logging(service_name: str, environment: str, level: str = "INFO") -> None:
    """Call once at service startup inside the FastAPI lifespan handler."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_JSONFormatter(service_name, environment))
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    # Silence noisy third-party loggers
    for noisy in ("uvicorn.access", "ibm_watsonx_ai", "urllib3", "botocore"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
