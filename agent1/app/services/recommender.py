"""
agent1/app/services/recommender.py
────────────────────────────────────
Approved-tool ranking engine for Agent 1.

Logic:
  1. Start with the static approved-tool list.
  2. Query watsonx.data integration_catalogue for historical usage counts.
  3. If the catalogue has enough data (>= catalogue_min_usage_for_ranking),
     sort tools by descending usage_count.
  4. Return a ranked list of ToolRecommendation objects.

The LLM later uses this ranked list as context when generating its
recommendations — it is NOT forced to pick the top-ranked tool.
The final selection is always driven by the NL requirement.

watsonx.governance is checked for each tool — tools with status
"Rejected" are excluded from the ranked list entirely.
"""

from shared.config import Settings
from shared.governance_logger import check_tool_approval
from shared.wxdata_client import execute_query
from shared.logging import get_logger
from agent1.app.models.response import (
    ApprovedTool,
    GovernanceStatus,
    ToolRecommendation,
)

logger = get_logger(__name__)

# Static ordered fallback (used when catalogue has insufficient data)
_APPROVED_TOOLS_ORDER = [
    ApprovedTool.IBM_REDWOOD,
    ApprovedTool.WEBMETHODS,
    ApprovedTool.APACHE_NIFI,
    ApprovedTool.AZURE_LOGIC,
]


def _fetch_usage_counts(settings: Settings) -> dict[str, int]:
    """
    Query integration_catalogue for tool usage frequency.
    Returns a dict of {tool_name: count}.
    Falls back to empty dict if the query fails (pre-population phase).
    """
    sql = f"""
        SELECT tool_chosen, COUNT(*) AS usage_count
        FROM {settings.wxdata_catalog}.{settings.wxdata_schema}.integration_catalogue
        GROUP BY tool_chosen
        ORDER BY usage_count DESC
    """
    try:
        rows = execute_query(settings, sql)
        return {row["tool_chosen"]: int(row["usage_count"]) for row in rows}
    except Exception as exc:
        logger.warning("Could not fetch usage counts from catalogue", extra={"error": str(exc)})
        return {}


def get_ranked_tools(settings: Settings) -> list[ToolRecommendation]:
    """
    Return a ranked list of approved tools.

    Tools with governance_status == "Rejected" are excluded.
    Ranking: catalogue usage count (descending) if sufficient data exists;
    otherwise static order.
    """
    usage_counts = _fetch_usage_counts(settings)
    total_catalogue_entries = sum(usage_counts.values())
    use_frequency_ranking = total_catalogue_entries >= settings.catalogue_min_usage_for_ranking

    ranked: list[ToolRecommendation] = []

    for tool in _APPROVED_TOOLS_ORDER:
        gov_status_str = check_tool_approval(settings, tool.value)
        gov_status = GovernanceStatus(gov_status_str) if gov_status_str in GovernanceStatus._value2member_map_ else GovernanceStatus.UNKNOWN

        if gov_status == GovernanceStatus.REJECTED:
            logger.info("Tool excluded — governance status Rejected", extra={"tool": tool.value})
            continue

        count = usage_counts.get(tool.value, 0)
        ranked.append(
            ToolRecommendation(
                rank=0,  # assigned after sorting
                tool=tool,
                rationale="",  # filled in by prompt_builder
                governance_status=gov_status,
                usage_count=count,
            )
        )

    # Sort by usage count descending if we have enough data
    if use_frequency_ranking:
        ranked.sort(key=lambda r: r.usage_count, reverse=True)

    # Assign sequential ranks
    for i, rec in enumerate(ranked, start=1):
        rec.rank = i

    logger.info(
        "Tool ranking complete",
        extra={
            "total_tools": len(ranked),
            "frequency_ranking_active": use_frequency_ranking,
        },
    )
    return ranked
