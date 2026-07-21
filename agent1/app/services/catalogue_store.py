"""
agent1/app/services/catalogue_store.py
────────────────────────────────────────
Persists design artefacts to watsonx.data integration_catalogue
and updates tool usage frequency for the learnable recommender.

Table schema (Iceberg, created by infra/terraform DDL):
  integration_catalogue (
    id              VARCHAR,
    created_at      TIMESTAMP,
    requirement_summary VARCHAR,
    tool_chosen     VARCHAR,
    protocol        VARCHAR,
    data_format     VARCHAR,
    auth_method     VARCHAR,
    cos_object_key  VARCHAR,
    usage_count     BIGINT,        -- updated by increment_usage_count()
    prompt_version  VARCHAR
  )

Writes are non-blocking failures: if the write fails the design is still
returned to the caller — the catalogue is best-effort telemetry.
"""

import uuid
from datetime import datetime, timezone

from shared.config import Settings
from shared.logging import get_logger
from shared.wxdata_client import execute_query, insert_row

from agent1.app.models.response import DesignDocument, DesignResponse

logger = get_logger(__name__)

_TABLE = "{catalog}.{schema}.integration_catalogue"


def _table(settings: Settings) -> str:
    return _TABLE.format(catalog=settings.wxdata_catalog, schema=settings.wxdata_schema)


def store_design(
    settings: Settings,
    design_id: str,
    requirement_summary: str,
    doc: DesignDocument,
    cos_key: str,
) -> None:
    """
    INSERT a new row into integration_catalogue.
    Failures are logged as WARNING — never raised to the caller.
    """
    row = {
        "id": design_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "requirement_summary": requirement_summary[:500],
        "tool_chosen": doc.primary_tool.value,
        "protocol": doc.protocol.value,
        "data_format": doc.data_format.value,
        "auth_method": doc.auth_method.value,
        "cos_object_key": cos_key,
        "usage_count": 1,
        "prompt_version": settings.agent1_prompt_template_version,
    }
    try:
        insert_row(settings, _table(settings), row)
        logger.info(
            "Catalogue entry stored",
            extra={"design_id": design_id, "tool": doc.primary_tool.value},
        )
    except Exception as exc:
        logger.warning(
            "Catalogue store failed (non-fatal)",
            extra={"design_id": design_id, "error": str(exc)},
        )


def increment_usage_count(settings: Settings, tool_name: str) -> None:
    """
    Increment the usage_count for the most recent catalogue entry for
    the given tool. This keeps the learnable ranking up-to-date.
    """
    sql = f"""
        UPDATE {_table(settings)}
        SET usage_count = usage_count + 1
        WHERE tool_chosen = '{tool_name}'
          AND id = (
            SELECT id FROM {_table(settings)}
            WHERE tool_chosen = '{tool_name}'
            ORDER BY created_at DESC
            LIMIT 1
          )
    """
    try:
        execute_query(settings, sql)
    except Exception as exc:
        logger.warning(
            "Usage count increment failed (non-fatal)",
            extra={"tool": tool_name, "error": str(exc)},
        )


def get_catalogue_stats(settings: Settings) -> dict:
    """
    Query integration_catalogue for aggregated usage statistics.
    Returns a dict compatible with CatalogueStats model.
    """
    freq_sql = f"""
        SELECT tool_chosen, protocol, auth_method,
               COUNT(*) AS cnt
        FROM {_table(settings)}
        GROUP BY tool_chosen, protocol, auth_method
        ORDER BY cnt DESC
    """
    recent_sql = f"""
        SELECT id, created_at, requirement_summary, tool_chosen,
               protocol, data_format, auth_method, cos_object_key, usage_count
        FROM {_table(settings)}
        ORDER BY created_at DESC
        LIMIT 10
    """

    rows = execute_query(settings, freq_sql)
    recent = execute_query(settings, recent_sql)

    tool_freq: dict[str, int] = {}
    protocol_freq: dict[str, int] = {}
    auth_freq: dict[str, int] = {}
    total = 0

    for row in rows:
        cnt = int(row["cnt"])
        total += cnt
        tool_freq[row["tool_chosen"]] = tool_freq.get(row["tool_chosen"], 0) + cnt
        protocol_freq[row["protocol"]] = protocol_freq.get(row["protocol"], 0) + cnt
        auth_freq[row["auth_method"]] = auth_freq.get(row["auth_method"], 0) + cnt

    top_tool = max(tool_freq, key=tool_freq.get) if tool_freq else None

    return {
        "total_designs": total,
        "tool_frequency": dict(sorted(tool_freq.items(), key=lambda x: x[1], reverse=True)),
        "protocol_frequency": dict(sorted(protocol_freq.items(), key=lambda x: x[1], reverse=True)),
        "auth_frequency": dict(sorted(auth_freq.items(), key=lambda x: x[1], reverse=True)),
        "top_tool": top_tool,
        "recent_entries": recent,
    }
