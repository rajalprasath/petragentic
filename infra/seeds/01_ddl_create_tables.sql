-- =============================================================================
-- infra/seeds/01_ddl_create_tables.sql
-- =============================================================================
-- Creates all four Iceberg tables in watsonx.data (Presto / Hive Metastore).
-- Run this ONCE against the watsonx.data Presto REST endpoint before seeding.
--
-- Connection:
--   POST {WXDATA_PRESTO_URL}/v1/statement
--   Headers: Authorization: Bearer {WXDATA_AUTH_TOKEN}
--             X-Presto-Catalog: petragentic
--             X-Presto-Schema:  main
--
-- Execute each statement individually — Presto REST does not support
-- multi-statement batches in a single POST.
-- =============================================================================

-- ── Agent 1: Integration Catalogue ──────────────────────────────────────────
-- Learnable tool recommendation history.
-- usage_count is incremented by catalogue_store.increment_usage_count()
-- after every successful /design call.

CREATE TABLE IF NOT EXISTS petragentic.main.integration_catalogue (
    id                  VARCHAR         COMMENT 'UUID for the design artefact',
    created_at          TIMESTAMP       COMMENT 'UTC timestamp of generation',
    requirement_summary VARCHAR         COMMENT 'First 500 chars of the NL requirement',
    tool_chosen         VARCHAR         COMMENT 'ApprovedTool enum value',
    protocol            VARCHAR         COMMENT 'RecommendedProtocol enum value',
    data_format         VARCHAR         COMMENT 'RecommendedDataFormat enum value',
    auth_method         VARCHAR         COMMENT 'RecommendedAuthMethod enum value',
    cos_object_key      VARCHAR         COMMENT 'COS key under petragentic-artefacts bucket',
    usage_count         BIGINT          COMMENT 'Incremented on each tool recommendation',
    prompt_version      VARCHAR         COMMENT 'agent1_prompt_template_version at generation time'
)
WITH (
    format            = 'PARQUET',
    partitioning      = ARRAY['month(created_at)']
);

-- ── Agent 2: Gold Image Baselines ────────────────────────────────────────────
-- Approved security state per server class.
-- Loaded once by the security team; updated via change-controlled PRs.
-- Agent 2 reads this table at every /validate call.

CREATE TABLE IF NOT EXISTS petragentic.main.server_baselines (
    server_class        VARCHAR         COMMENT 'Logical server class identifier',
    category            VARCHAR         COMMENT 'folder_permission | share | group_member | service_account',
    attribute_key       VARCHAR         COMMENT 'Path / share name / group / service name',
    expected_value      VARCHAR         COMMENT 'JSON-encoded expected value(s)',
    updated_at          TIMESTAMP       COMMENT 'Last modification timestamp',
    updated_by          VARCHAR         COMMENT 'Who last modified this baseline entry'
)
WITH (
    format            = 'PARQUET',
    partitioning      = ARRAY['server_class']
);

-- ── Agent 2: Audit Scans ─────────────────────────────────────────────────────
-- One row per (scan_id, server) pair.
-- Written by audit_store.store_scan_result() as a background task.

CREATE TABLE IF NOT EXISTS petragentic.main.audit_scans (
    scan_id             VARCHAR         COMMENT 'UUID for the scan run',
    server              VARCHAR         COMMENT 'Target server hostname',
    server_class        VARCHAR         COMMENT 'Baseline class used for comparison',
    scan_type           VARCHAR         COMMENT 'new_validation | periodic_audit | drift_check',
    started_at          TIMESTAMP       COMMENT 'Scan start (UTC)',
    completed_at        TIMESTAMP       COMMENT 'Scan end (UTC)',
    compliance_status   VARCHAR         COMMENT 'compliant | non_compliant | partial | scan_failed',
    total_findings      BIGINT          COMMENT 'Total drift findings for this server in this scan',
    critical_count      BIGINT          COMMENT 'Critical severity findings',
    triggered_by        VARCHAR         COMMENT 'manual | github_actions_scheduled | ...'
)
WITH (
    format            = 'PARQUET',
    partitioning      = ARRAY['month(started_at)', 'server_class']
);

-- ── Agent 2: Drift Findings ───────────────────────────────────────────────────
-- One row per finding per scan.
-- Time-travel query example:
--   SELECT * FROM petragentic.main.drift_findings
--   FOR SYSTEM_TIME AS OF TIMESTAMP '2025-01-01 00:00:00'
--   WHERE server = 'WIN-SRV-001';

CREATE TABLE IF NOT EXISTS petragentic.main.drift_findings (
    finding_id          VARCHAR         COMMENT 'UUID for the specific finding',
    scan_id             VARCHAR         COMMENT 'FK to audit_scans.scan_id',
    server              VARCHAR         COMMENT 'Target server hostname',
    category            VARCHAR         COMMENT 'folder_permission | share | group_member | service_account',
    severity            VARCHAR         COMMENT 'critical | high | medium | low | info',
    title               VARCHAR         COMMENT 'Human-readable finding title (max 500 chars)',
    cis_control_id      VARCHAR         COMMENT 'CIS Benchmark control ID e.g. CIS 1.1.1',
    nist_control        VARCHAR         COMMENT 'NIST 800-53 control e.g. AC-2',
    is_new              VARCHAR         COMMENT 'true if not seen in the previous scan',
    created_at          TIMESTAMP       COMMENT 'UTC timestamp of this finding row'
)
WITH (
    format            = 'PARQUET',
    partitioning      = ARRAY['month(created_at)', 'severity']
);
