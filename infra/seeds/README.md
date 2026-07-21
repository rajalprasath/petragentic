# Petragentic — watsonx.data Seed Data

## Overview

This directory seeds all four Iceberg tables in watsonx.data before the agents are started.

---

## Files

| File | Rows | Purpose |
|---|---|---|
| `01_ddl_create_tables.sql` | — | `CREATE TABLE IF NOT EXISTS` for all 4 Iceberg tables |
| `02_seed_integration_catalogue.sql` | 12 | Agent 1 design history — all 4 approved tools |
| `03_seed_server_baselines.sql` | 45 | Agent 2 Gold Image baselines — 3 server classes |
| `04_seed_audit_history.sql` | 30 | Agent 2 historical scans — 2 runs across 4 servers |
| `run_seeds.py` | — | Python runner — executes all files in order |

---

## Quick Start

```bash
# 1. Install dependency
pip install requests python-dotenv

# 2. Set credentials (add to .env at repo root)
WXDATA_PRESTO_URL=https://private.your-wxdata-instance.cloud.ibm.com
WXDATA_AUTH_TOKEN=your-bearer-token
WXDATA_CATALOG=petragentic
WXDATA_SCHEMA=main

# 3. Dry-run to validate SQL without connecting
DRY_RUN=true python infra/seeds/run_seeds.py

# 4. Execute against live watsonx.data
python infra/seeds/run_seeds.py
```

---

## Tables and Seeded Data

### `integration_catalogue` — Agent 1 Learnable Recommender

12 realistic design records seeded across all approved tools:

| Tool | Records | Cumulative Usage | Use Cases |
|---|---|---|---|
| Apache NiFi | 4 | 23 | SAP→Db2 CSV, IoT Kafka, SFTP XML, CDC replication |
| IBM Redwood | 3 | 20 | SAP batch orchestration, finance close, HR sync |
| webMethods | 3 | 15 | EDI X12 B2B, SAP BAPI REST exposure, SOAP/legacy |
| Azure Logic Apps | 2 | 5 | M365 approval workflow, Salesforce→SAP sync |

**Effect on recommender:** Apache NiFi ranks `#1` from day one. The learnable engine immediately has a realistic frequency distribution rather than a flat list.

---

### `server_baselines` — Agent 2 Gold Image

45 baseline rules across 3 server classes:

| Server Class | Folder Rules | Share Rules | Group Rules | Service Rules |
|---|---|---|---|---|
| `standard-windows-server` | 6 | 2 (`ADMIN$`, `IPC$`) | 3 | 4 |
| `domain-controller` | 3 | 3 (`NETLOGON`, `SYSVOL`, `ADMIN$`) | 2 | 3 |
| `sql-server` | 4 | 2 (`ADMIN$`, `SQLBackups`) | 2 | 4 |

---

### `audit_scans` + `drift_findings` — Agent 2 Scan History

2 scan runs simulating realistic enterprise scenarios:

| Server | Class | Jan Run | Feb Run | Story |
|---|---|---|---|---|
| WIN-SRV-001 | standard | ✅ 0 findings | ✅ 0 findings | Permanently compliant reference server |
| WIN-SRV-002 | standard | ❌ 3 findings (1 critical) | ❌ 3 findings (1 recurring critical, 1 new) | Persistent non-compliant — critical Administrators drift never fixed |
| WIN-SRV-003 | standard | ❌ 5 findings (2 critical) | ❌ 3 findings (0 critical) | New server improving after remediation — criticals resolved |
| WIN-DC-001 | domain-controller | ⚠️ 1 high finding | ✅ 0 findings | Successfully remediated between runs |

---

## Verification Queries

Run these against Presto after seeding to confirm data is correct:

```sql
-- Agent 1: tool frequency (NiFi should rank first)
SELECT tool_chosen, SUM(usage_count) AS total_usage
FROM petragentic.main.integration_catalogue
GROUP BY tool_chosen
ORDER BY total_usage DESC;

-- Agent 2: baseline coverage
SELECT server_class, category, COUNT(*) AS rules
FROM petragentic.main.server_baselines
GROUP BY server_class, category
ORDER BY server_class, category;

-- Agent 2: scan history summary
SELECT server, compliance_status, total_findings, critical_count, started_at
FROM petragentic.main.audit_scans
ORDER BY started_at DESC;

-- Agent 2: Iceberg time-travel (state before Feb run)
SELECT server, severity, title, is_new
FROM petragentic.main.drift_findings
FOR SYSTEM_TIME AS OF TIMESTAMP '2025-01-21 00:00:00'
ORDER BY server, severity;

-- Agent 2: recurring findings on WIN-SRV-002
SELECT title, is_new, created_at
FROM petragentic.main.drift_findings
WHERE server = 'WIN-SRV-002'
ORDER BY created_at;
```
