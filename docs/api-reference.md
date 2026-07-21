# Petragentic API Reference

## Overview

All API endpoints are exposed through the **API Gateway** (port 8080 in local dev).
In production, the gateway is the only public-facing component — it handles IBM App ID
authentication before forwarding requests to Agent 1 and Agent 2 over the internal
cluster network.

---

## Authentication

Every business endpoint requires a valid **IBM App ID Bearer JWT** in the
`Authorization` header:

```
Authorization: Bearer <access_token>
```

Obtain a token from your App ID tenant:

```bash
curl -X POST \
  "https://us-south.appid.cloud.ibm.com/oauth/v4/<tenantId>/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials&client_id=<clientId>&client_secret=<secret>"
```

The response `access_token` carries scopes. Required scopes per route:

| Route | Scope |
|---|---|
| `POST /api/v1/design` | `design:write` |
| `GET  /api/v1/catalogue/stats` | `design:read` |
| `POST /api/v1/validate` | `audit:write` |
| `GET  /api/v1/report/{scan_id}` | `audit:read` |
| `GET  /api/v1/report/{scan_id}/html` | `audit:read` |

Health and readiness endpoints (`/health`, `/ready`) are **unauthenticated**.

---

## Headers

| Header | Direction | Description |
|---|---|---|
| `X-Correlation-ID` | Request / Response | UUID for request tracing. Auto-generated if absent. |
| `X-Gateway-User` | Forwarded to agents | JWT `sub` claim injected by gateway. |

---

## Agent 1 — Integration Design & Automation

### `POST /api/v1/design`

Generate a complete integration design document from natural-language requirements.

**Request body** (`application/json`):

```json
{
  "requirements": "Send daily sales CSV from SAP ECC to IBM Db2 Warehouse",
  "source_system": "SAP ECC",
  "target_system": "IBM Db2 Warehouse",
  "integration_pattern": "batch",
  "data_volume_gb": 2.5,
  "sla_minutes": 60
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `requirements` | string | ✅ | Free-text description of the integration need |
| `source_system` | string | ✅ | Source application or system name |
| `target_system` | string | ✅ | Target application or system name |
| `integration_pattern` | enum | ✅ | `batch` \| `real_time` \| `event_driven` \| `api_gateway` |
| `data_volume_gb` | float | ❌ | Expected data volume per run in GB |
| `sla_minutes` | int | ❌ | Max acceptable end-to-end latency in minutes |

**Response** (`200 OK`):

```json
{
  "design_id": "des-a3f8...",
  "tool": "IBM Redwood",
  "protocol": "file-based",
  "data_format": "CSV",
  "authentication": "service_principal",
  "design_document": {
    "overview": "...",
    "architecture": "...",
    "security_considerations": "...",
    "error_handling": "..."
  },
  "recommended_tools": ["IBM Redwood", "webMethods"],
  "governance_approved": true,
  "generated_at": "2025-01-15T10:23:45Z"
}
```

**Error responses:**

| Code | Reason |
|---|---|
| 422 | Governance check failed — tool not approved |
| 502 | watsonx.ai inference failed |
| 503 | watsonx.data unreachable |

---

### `GET /api/v1/catalogue/stats`

Return usage statistics from the learnable integration catalogue stored in watsonx.data.

**Response** (`200 OK`):

```json
{
  "total_designs": 42,
  "tool_usage": {
    "IBM Redwood": 18,
    "webMethods": 12,
    "Apache NiFi": 8,
    "Azure Logic Apps": 4
  },
  "pattern_usage": {
    "batch": 25,
    "real_time": 10,
    "event_driven": 7
  },
  "top_source_systems": ["SAP ECC", "Oracle EBS", "Salesforce"]
}
```

---

## Agent 2 — Security Compliance & Audit

### `POST /api/v1/validate`

Run a full security baseline validation against a Windows server.

**Request body** (`application/json`):

```json
{
  "host": "10.0.1.50",
  "server_class": "web-server",
  "scan_type": "new_server",
  "winrm_username": "svc_audit",
  "winrm_password": "...",
  "audit_scope": ["folders", "permissions", "shares", "local_groups", "service_accounts"]
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `host` | string | ✅ | IP or hostname of target Windows server |
| `server_class` | string | ✅ | Gold Image class: `web-server`, `db-server`, `app-server` |
| `scan_type` | enum | ✅ | `new_server` \| `periodic_audit` |
| `winrm_username` | string | ✅ | WinRM/PSRemoting credential username |
| `winrm_password` | string | ✅ | WinRM/PSRemoting credential password |
| `audit_scope` | array | ❌ | Limit scan to specific categories (default: all) |

**Response** (`200 OK`):

```json
{
  "scan_id": "scan-b7c2...",
  "host": "10.0.1.50",
  "server_class": "web-server",
  "scan_type": "new_server",
  "scan_timestamp": "2025-01-15T10:30:00Z",
  "drift_findings": [
    {
      "finding_id": "find-001",
      "category": "shares",
      "description": "Unexpected share: ROGUE_SHARE",
      "severity": "HIGH",
      "cis_controls": "CIS-2.3.1",
      "nist_controls": "AC-3",
      "is_new_finding": true
    }
  ],
  "remediation_scripts": [
    {
      "finding_id": "find-001",
      "script_name": "remove_rogue_share.ps1",
      "script_content": "Remove-SmbShare -Name 'ROGUE_SHARE' -Force",
      "syntax_valid": true
    }
  ],
  "compliance_summary": {
    "cis_benchmark": "CIS Windows Server 2022 v3.0",
    "nist_framework": "NIST 800-53 Rev 5",
    "total_checks": 45,
    "passed": 44,
    "failed": 1,
    "compliance_pct": 97.8
  },
  "report_cos_key": "reports/scan-b7c2/report.json"
}
```

---

### `GET /api/v1/report/{scan_id}`

Retrieve a previously generated compliance scan report as JSON.

**Response** (`200 OK`): Same schema as the `POST /api/v1/validate` response body.

**Error**: `404` if `scan_id` not found in watsonx.data.

---

### `GET /api/v1/report/{scan_id}/html`

Retrieve the rendered HTML compliance report for a scan.

**Response** (`200 OK`, `Content-Type: text/html`): Full CIS/NIST compliance report with
drift findings table, severity badges, and remediation script download links.

---

## Ops Endpoints (all services)

These endpoints bypass the gateway and are called directly by OpenShift probes:

| Endpoint | Service | Description |
|---|---|---|
| `GET /health` | gateway, agent1, agent2 | Liveness probe — always 200 if process alive |
| `GET /ready` | gateway, agent1, agent2 | Readiness probe — 503 if upstream dependencies unreachable |

---

## Error Response Schema

All error responses follow this structure:

```json
{
  "error": "Human-readable message",
  "detail": { "key": "machine-readable context" },
  "correlation_id": "uuid"
}
```
