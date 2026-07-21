"""
shared/wxdata_client.py
───────────────────────
Thin wrapper over the watsonx.data Presto REST API.

Presto REST protocol:
  POST /v1/statement  → returns nextUri to poll
  GET  <nextUri>      → repeat until state == FINISHED

This module handles the polling loop transparently.
All SQL construction stays in the calling service — this module
is purely transport.

Usage:
    rows = execute_query(settings, "SELECT * FROM main.integration_catalogue LIMIT 10")
    insert_row(settings, "main.integration_catalogue", {"id": "...", "tool": "NiFi"})
"""

import time
from typing import Any

import requests

from shared.config import Settings
from shared.exceptions import WxDataInsertError, WxDataQueryError
from shared.logging import get_logger

logger = get_logger(__name__)

_POLL_INTERVAL_SEC = 0.5
_MAX_POLLS = 120           # 60 seconds max wait


def _headers(settings: Settings) -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.wxdata_auth_token}",
        "X-Presto-User": "petragentic",
        "X-Presto-Catalog": settings.wxdata_catalog,
        "X-Presto-Schema": settings.wxdata_schema,
    }


def execute_query(settings: Settings, sql: str) -> list[dict[str, Any]]:
    """
    Execute a Presto SQL statement and return all rows as a list of dicts.

    Raises:
        WxDataQueryError — on HTTP error or Presto FAILED state
    """
    url = f"{settings.wxdata_presto_url}/v1/statement"
    try:
        resp = requests.post(
            url,
            data=sql,
            headers=_headers(settings),
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.HTTPError as exc:
        raise WxDataQueryError(message=str(exc), query=sql)

    # Poll until Presto finishes
    polls = 0
    columns: list[str] = []
    rows: list[dict] = []

    while True:
        state = data.get("stats", {}).get("state", "UNKNOWN")

        if state == "FAILED":
            error = data.get("error", {}).get("message", "Unknown Presto error")
            raise WxDataQueryError(message=error, query=sql)

        if "columns" in data:
            columns = [c["name"] for c in data["columns"]]

        if "data" in data:
            for row in data["data"]:
                rows.append(dict(zip(columns, row)))

        next_uri = data.get("nextUri")
        if not next_uri:
            break

        if state == "FINISHED" and not next_uri:
            break

        polls += 1
        if polls > _MAX_POLLS:
            raise WxDataQueryError(message="Presto query timed out", query=sql)

        time.sleep(_POLL_INTERVAL_SEC)
        try:
            resp = requests.get(next_uri, headers=_headers(settings), timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except requests.HTTPError as exc:
            raise WxDataQueryError(message=str(exc), query=sql)

    logger.debug("Presto query complete", extra={"rows": len(rows), "state": state})
    return rows


def insert_row(settings: Settings, table: str, row: dict[str, Any]) -> None:
    """
    Build and execute a single-row INSERT from a dict.
    Values are single-quoted; callers are responsible for sanitising inputs.

    Raises:
        WxDataInsertError — wraps WxDataQueryError with table context
    """
    cols = ", ".join(row.keys())
    vals = ", ".join(
        f"NULL" if v is None else f"'{str(v).replace(chr(39), chr(39)*2)}'"
        for v in row.values()
    )
    sql = f"INSERT INTO {table} ({cols}) VALUES ({vals})"
    try:
        execute_query(settings, sql)
    except WxDataQueryError as exc:
        raise WxDataInsertError(table=table, message=exc.message)
