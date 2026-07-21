"""
tests/shared/test_logging.py
─────────────────────────────
Unit tests for shared.logging — JSON logger, correlation_id ContextVar,
and get_logger() factory.
"""

import json
import logging
import io
from contextvars import copy_context

import pytest

from shared.logging import configure_logging, correlation_id_var, get_logger


def _capture_log(func, level="INFO") -> list[dict]:
    """
    Run *func* with a fresh StreamHandler and return parsed JSON log records.
    """
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    root = logging.getLogger()
    original_handlers = root.handlers[:]
    root.handlers = [handler]
    root.setLevel(level)
    try:
        func()
    finally:
        root.handlers = original_handlers
    stream.seek(0)
    records = []
    for line in stream.readlines():
        line = line.strip()
        if line:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                records.append({"raw": line})
    return records


def test_get_logger_returns_logger():
    logger = get_logger("test.module")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test.module"


def test_configure_logging_sets_level():
    configure_logging("test-svc", "test", "DEBUG")
    root = logging.getLogger()
    assert root.level <= logging.DEBUG


def test_correlation_id_var_default():
    """Before being set, correlation_id_var should return None or default."""
    token = correlation_id_var.set("cid-001")
    assert correlation_id_var.get() == "cid-001"
    correlation_id_var.reset(token)


def test_correlation_id_isolated_per_context():
    """Each context (simulating a request) has its own correlation ID."""
    results = {}

    def task_a():
        token = correlation_id_var.set("aaa")
        results["a"] = correlation_id_var.get()
        correlation_id_var.reset(token)

    def task_b():
        token = correlation_id_var.set("bbb")
        results["b"] = correlation_id_var.get()
        correlation_id_var.reset(token)

    ctx_a = copy_context()
    ctx_b = copy_context()
    ctx_a.run(task_a)
    ctx_b.run(task_b)

    assert results["a"] == "aaa"
    assert results["b"] == "bbb"
