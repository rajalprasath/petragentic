"""
orchestrate/app/tools.py
─────────────────────────
Tool definitions for the watsonx Orchestrate ReAct engine.

Each tool wraps an Agent 1 or Agent 2 REST endpoint. The ReAct engine calls
these by name when Granite outputs an Action line.

Tool interface contract:
    async def call(params: dict) -> dict

Tools are registered in the TOOL_REGISTRY dict at the bottom of this module.
The ReAct engine looks up tools by the exact name Granite outputs in
"Action: <tool_name>".
"""

from __future__ import annotations

import json
from typing import Any, Awaitable, Callable

import httpx

from orchestrate.app.config import OrchestrateSettings


# ── Base HTTP helper ──────────────────────────────────────────────────────────

async def _http_post(
    settings: OrchestrateSettings,
    url: str,
    payload: dict,
) -> dict[str, Any]:
    """POST JSON payload and return the parsed response body."""
    timeout = httpx.Timeout(
        connect=settings.skill_connect_timeout,
        read=settings.skill_read_timeout,
        write=settings.skill_read_timeout,
        pool=settings.skill_connect_timeout,
    )
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        return resp.json()


async def _http_get(
    settings: OrchestrateSettings,
    url: str,
) -> dict[str, Any]:
    """GET and return the parsed response body."""
    timeout = httpx.Timeout(
        connect=settings.skill_connect_timeout,
        read=settings.skill_read_timeout,
        write=settings.skill_read_timeout,
        pool=settings.skill_connect_timeout,
    )
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.json()


# ── Tool implementations ──────────────────────────────────────────────────────

class GenerateIntegrationDesign:
    """
    Tool: generate_integration_design
    Calls Agent 1 POST /design.

    Granite must output:
        Action: generate_integration_design
        Action Input: {"requirement": "...", "pattern_hint": "file_transfer"}
    """
    name = "generate_integration_design"
    description = (
        "Generate an end-to-end enterprise integration design document. "
        "Required: requirement (str). Optional: pattern_hint (str), "
        "requester (str), tags (list[str])."
    )

    @staticmethod
    async def call(settings: OrchestrateSettings, params: dict) -> dict:
        url = f"{settings.agent1_url.rstrip('/')}/design"
        try:
            result = await _http_post(settings, url, params)
            # Summarise for the LLM — return key fields only to keep context lean
            return {
                "design_id": result.get("design_id"),
                "recommended_tool": result.get("recommended_tool"),
                "recommended_protocol": result.get("recommended_protocol"),
                "recommended_data_format": result.get("recommended_data_format"),
                "recommended_auth": result.get("recommended_auth"),
                "governance_status": result.get("governance_status"),
                "cos_uri": result.get("cos_uri"),
                "executive_summary": (
                    result.get("design_document", {}).get("executive_summary", "")[:400]
                ),
                "implementation_steps": (
                    result.get("design_document", {}).get("implementation_steps", [])[:5]
                ),
            }
        except httpx.HTTPStatusError as exc:
            return {"error": f"Agent 1 returned HTTP {exc.response.status_code}: {exc.response.text[:200]}"}
        except Exception as exc:
            return {"error": str(exc)}


class GetCatalogueStats:
    """
    Tool: get_catalogue_stats
    Calls Agent 1 GET /catalogue/stats.
    """
    name = "get_catalogue_stats"
    description = (
        "Return historical integration catalogue usage statistics: "
        "tool_frequency, protocol_frequency, top_tool. Call this to give "
        "context before making a design recommendation."
    )

    @staticmethod
    async def call(settings: OrchestrateSettings, params: dict) -> dict:
        url = f"{settings.agent1_url.rstrip('/')}/catalogue/stats"
        try:
            return await _http_get(settings, url)
        except httpx.HTTPStatusError as exc:
            return {"error": f"Agent 1 returned HTTP {exc.response.status_code}"}
        except Exception as exc:
            return {"error": str(exc)}


class RunSecurityAudit:
    """
    Tool: run_security_audit
    Calls Agent 2 POST /validate.

    Granite must output:
        Action: run_security_audit
        Action Input: {"servers": ["WIN-WEB-001"], "server_class": "standard-windows-server", ...}
    """
    name = "run_security_audit"
    description = (
        "Validate Windows server security baselines and detect drift. "
        "Required: servers (list[str]), winrm_username (str), winrm_password (str). "
        "Optional: server_class (str), scan_type (str), scope (list[str])."
    )

    @staticmethod
    async def call(settings: OrchestrateSettings, params: dict) -> dict:
        # Always tag as orchestrate-triggered for audit trail
        params.setdefault("triggered_by", "orchestrate_agent")
        url = f"{settings.agent2_url.rstrip('/')}/validate"
        try:
            result = await _http_post(settings, url, params)
            report = result.get("report", {})
            summary = report.get("summary", {})
            return {
                "scan_id": result.get("scan_id"),
                "status": result.get("status"),
                "message": result.get("message"),
                "total_servers": summary.get("total_servers"),
                "compliant_servers": summary.get("compliant_servers"),
                "non_compliant_servers": summary.get("non_compliant_servers"),
                "total_findings": summary.get("total_findings"),
                "critical_findings": summary.get("critical_findings"),
                "high_findings": summary.get("high_findings"),
                "medium_findings": summary.get("medium_findings"),
                "top_cis_violations": summary.get("top_cis_violations", []),
                "cos_html_uri": report.get("cos_html_uri"),
            }
        except httpx.HTTPStatusError as exc:
            return {"error": f"Agent 2 returned HTTP {exc.response.status_code}: {exc.response.text[:200]}"}
        except Exception as exc:
            return {"error": str(exc)}


class GetScanReport:
    """
    Tool: get_scan_report
    Calls Agent 2 GET /report/{scan_id}.
    """
    name = "get_scan_report"
    description = (
        "Retrieve a previously generated compliance scan report by scan_id. "
        "Required: scan_id (str)."
    )

    @staticmethod
    async def call(settings: OrchestrateSettings, params: dict) -> dict:
        scan_id = params.get("scan_id", "")
        if not scan_id:
            return {"error": "scan_id is required"}
        url = f"{settings.agent2_url.rstrip('/')}/report/{scan_id}"
        try:
            result = await _http_get(settings, url)
            summary = result.get("summary", {})
            return {
                "scan_id": result.get("scan_id"),
                "status": result.get("status"),
                "server_class": result.get("server_class"),
                "started_at": result.get("started_at"),
                "total_findings": summary.get("total_findings"),
                "critical_findings": summary.get("critical_findings"),
                "high_findings": summary.get("high_findings"),
                "cos_html_uri": result.get("cos_html_uri"),
            }
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return {"error": f"Scan report not found: {scan_id}"}
            return {"error": f"Agent 2 returned HTTP {exc.response.status_code}"}
        except Exception as exc:
            return {"error": str(exc)}


# ── Tool registry — keyed by the name Granite outputs in "Action:" ────────────

TOOL_REGISTRY: dict[str, Any] = {
    GenerateIntegrationDesign.name: GenerateIntegrationDesign,
    GetCatalogueStats.name: GetCatalogueStats,
    RunSecurityAudit.name: RunSecurityAudit,
    GetScanReport.name: GetScanReport,
}


def get_tools_description() -> str:
    """
    Returns a formatted string listing all tools and their descriptions.
    This is injected into the Granite system prompt so the LLM knows
    what tools are available.
    """
    lines = ["Available tools:\n"]
    for tool_cls in TOOL_REGISTRY.values():
        lines.append(f"- {tool_cls.name}: {tool_cls.description}")
    return "\n".join(lines)
