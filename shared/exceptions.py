"""
shared/exceptions.py
─────────────────────
Custom exception hierarchy for the Petragentic platform.

All exceptions inherit from PetragenticError and carry:
  - message:     human-readable description
  - status_code: HTTP status to return to the caller
  - detail:      structured dict with machine-readable context

FastAPI exception handlers in each service's main.py translate these
into structured JSON responses — raw 500s are never returned.
"""


class PetragenticError(Exception):
    """Base exception for all Petragentic platform errors."""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        detail: dict | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.detail = detail or {}


# ── watsonx.ai ────────────────────────────────────────────────────────────────

class WatsonxInferenceError(PetragenticError):
    """LLM inference call failed or returned an unparseable response."""

    def __init__(self, message: str, model_id: str | None = None) -> None:
        super().__init__(message, status_code=502)
        self.detail = {"model_id": model_id}


class WatsonxQuotaError(PetragenticError):
    """Token quota exceeded on watsonx.ai."""

    def __init__(self) -> None:
        super().__init__("watsonx.ai token quota exceeded", status_code=429)


class WatsonxParseError(PetragenticError):
    """LLM returned output that could not be parsed into the expected schema."""

    def __init__(self, message: str, raw_output: str = "") -> None:
        super().__init__(message, status_code=502)
        self.detail = {"raw_output_preview": raw_output[:300]}


# ── watsonx.data ──────────────────────────────────────────────────────────────

class WxDataQueryError(PetragenticError):
    """Presto query against watsonx.data failed."""

    def __init__(self, message: str, query: str = "") -> None:
        super().__init__(message, status_code=502)
        self.detail = {"query_preview": query[:200]}


class WxDataInsertError(PetragenticError):
    """Row insert into watsonx.data failed."""

    def __init__(self, table: str, message: str) -> None:
        super().__init__(f"Insert into {table} failed: {message}", status_code=502)
        self.detail = {"table": table}


# ── watsonx.governance ────────────────────────────────────────────────────────

class GovernanceCheckError(PetragenticError):
    """A recommended tool failed the watsonx.governance approval check."""

    def __init__(self, tool: str, status: str) -> None:
        super().__init__(
            f"Tool '{tool}' is not approved — governance status: {status}",
            status_code=422,
        )
        self.detail = {"tool": tool, "governance_status": status}


# ── IBM COS ───────────────────────────────────────────────────────────────────

class COSUploadError(PetragenticError):
    """Object upload to IBM COS failed."""

    def __init__(self, bucket: str, key: str) -> None:
        super().__init__(f"COS upload failed: {bucket}/{key}", status_code=502)
        self.detail = {"bucket": bucket, "key": key}


# ── WinRM / PowerShell (Agent 2) ──────────────────────────────────────────────

class WinRMConnectionError(PetragenticError):
    """Cannot establish a WinRM connection to the target Windows server."""

    def __init__(self, host: str, reason: str = "") -> None:
        super().__init__(f"WinRM connection failed: {host}", status_code=502)
        self.detail = {"host": host, "reason": reason}


class WinRMCommandError(PetragenticError):
    """PowerShell command execution failed on the remote server."""

    def __init__(self, host: str, command_preview: str = "") -> None:
        super().__init__(f"PSRemoting command failed on {host}", status_code=502)
        self.detail = {"host": host, "command_preview": command_preview[:120]}


class PowerShellSyntaxError(PetragenticError):
    """Generated PowerShell script failed syntax validation."""

    def __init__(self, script_preview: str = "") -> None:
        super().__init__("Generated PS1 script failed syntax validation", status_code=500)
        self.detail = {"script_preview": script_preview[:200]}


# ── Agent 1 specific ──────────────────────────────────────────────────────────

class DesignGenerationError(PetragenticError):
    """Design document generation failed."""

    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=500)


class CatalogueStoreError(PetragenticError):
    """Failed to write design artefact to the integration catalogue."""

    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=500)


# ── Agent 2 specific ──────────────────────────────────────────────────────────

class BaselineNotFoundError(PetragenticError):
    """No Gold Image baseline found for the given server class."""

    def __init__(self, server_class: str) -> None:
        super().__init__(
            f"No baseline found for server class: {server_class}",
            status_code=404,
        )
        self.detail = {"server_class": server_class}


class ReportRenderError(PetragenticError):
    """Jinja2 compliance report rendering failed."""

    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=500)


class RemediationGenerationError(PetragenticError):
    """Remediation script generation failed for a drift finding."""

    def __init__(self, finding_id: str, message: str) -> None:
        super().__init__(f"Remediation generation failed for {finding_id}: {message}", status_code=500)
        self.detail = {"finding_id": finding_id}
