-- =============================================================================
-- infra/seeds/02_seed_integration_catalogue.sql
-- =============================================================================
-- Seed data for petragentic.main.integration_catalogue (Agent 1).
--
-- Provides 12 realistic design history records across all four approved tools.
-- This gives the learnable recommender enough signal from day one so that
-- the frequency-ranking path activates immediately (threshold = 3 records).
--
-- Tool distribution:
--   Apache NiFi       -- 4 records (most used for data-pipeline / ETL)
--   webMethods        -- 3 records (API + B2B integration)
--   IBM Redwood       -- 3 records (scheduled / ERP workloads)
--   Azure Logic Apps  -- 2 records (cloud-to-cloud / SaaS)
-- =============================================================================

INSERT INTO petragentic.main.integration_catalogue
(id, created_at, requirement_summary, tool_chosen, protocol,
 data_format, auth_method, cos_object_key, usage_count, prompt_version)
VALUES
(
  'seed-0001-nifi-erp-to-db2',
  TIMESTAMP '2025-01-10 09:15:00',
  'Move daily CSV exports from SAP ERP to IBM Db2 data warehouse on IBM Cloud. Files ~500 MB. Certificate-based auth required.',
  'Apache NiFi', 'file-based', 'CSV', 'mTLS / certificate',
  'designs/seed-0001-nifi-erp-to-db2.json', 8, 'v1.0'
);

INSERT INTO petragentic.main.integration_catalogue
(id, created_at, requirement_summary, tool_chosen, protocol,
 data_format, auth_method, cos_object_key, usage_count, prompt_version)
VALUES
(
  'seed-0002-nifi-kafka-stream',
  TIMESTAMP '2025-01-15 14:30:00',
  'Stream IoT sensor events from on-prem Kafka topic to IBM Event Streams on IBM Cloud for real-time analytics.',
  'Apache NiFi', 'Kafka', 'Avro', 'OAuth 2.0',
  'designs/seed-0002-nifi-kafka-stream.json', 5, 'v1.0'
);

INSERT INTO petragentic.main.integration_catalogue
(id, created_at, requirement_summary, tool_chosen, protocol,
 data_format, auth_method, cos_object_key, usage_count, prompt_version)
VALUES
(
  'seed-0003-nifi-sftp-inbound',
  TIMESTAMP '2025-02-03 08:45:00',
  'Ingest partner SFTP file drops (XML invoices) into IBM Cloud Object Storage for downstream processing. PGP encryption required.',
  'Apache NiFi', 'SFTP', 'XML', 'mTLS / certificate',
  'designs/seed-0003-nifi-sftp-inbound.json', 6, 'v1.0'
);

INSERT INTO petragentic.main.integration_catalogue
(id, created_at, requirement_summary, tool_chosen, protocol,
 data_format, auth_method, cos_object_key, usage_count, prompt_version)
VALUES
(
  'seed-0004-nifi-db-replication',
  TIMESTAMP '2025-02-20 11:00:00',
  'Replicate Oracle database change events to IBM Db2 on IBM Cloud using CDC. Near real-time, JSON payload, OAuth for API layer.',
  'Apache NiFi', 'REST', 'JSON', 'OAuth 2.0',
  'designs/seed-0004-nifi-db-replication.json', 4, 'v1.0'
);

INSERT INTO petragentic.main.integration_catalogue
(id, created_at, requirement_summary, tool_chosen, protocol,
 data_format, auth_method, cos_object_key, usage_count, prompt_version)
VALUES
(
  'seed-0005-wm-b2b-edi',
  TIMESTAMP '2025-01-22 10:00:00',
  'Implement EDI X12 850/855 purchase order exchange with three trading partners via AS2. Requires message transformation and acknowledgement.',
  'webMethods', 'SOAP', 'XML', 'mTLS / certificate',
  'designs/seed-0005-wm-b2b-edi.json', 7, 'v1.0'
);

INSERT INTO petragentic.main.integration_catalogue
(id, created_at, requirement_summary, tool_chosen, protocol,
 data_format, auth_method, cos_object_key, usage_count, prompt_version)
VALUES
(
  'seed-0006-wm-api-gateway',
  TIMESTAMP '2025-02-08 16:20:00',
  'Expose internal SAP BAPI functions as REST APIs to external partners. Need rate limiting, OAuth 2.0 token validation, and audit logging.',
  'webMethods', 'REST', 'JSON', 'OAuth 2.0',
  'designs/seed-0006-wm-api-gateway.json', 5, 'v1.0'
);

INSERT INTO petragentic.main.integration_catalogue
(id, created_at, requirement_summary, tool_chosen, protocol,
 data_format, auth_method, cos_object_key, usage_count, prompt_version)
VALUES
(
  'seed-0007-wm-legacy-soap',
  TIMESTAMP '2025-03-01 09:30:00',
  'Integrate legacy mainframe COBOL services (exposed as SOAP) with a modern React front-end via an orchestration layer.',
  'webMethods', 'SOAP', 'XML', 'API key',
  'designs/seed-0007-wm-legacy-soap.json', 3, 'v1.0'
);

INSERT INTO petragentic.main.integration_catalogue
(id, created_at, requirement_summary, tool_chosen, protocol,
 data_format, auth_method, cos_object_key, usage_count, prompt_version)
VALUES
(
  'seed-0008-redwood-sap-batch',
  TIMESTAMP '2025-01-28 07:00:00',
  'Orchestrate end-of-month SAP batch jobs across three landscapes (DEV, QA, PROD) with dependency management and SLA alerting.',
  'IBM Redwood', 'REST', 'JSON', 'service principal / managed identity',
  'designs/seed-0008-redwood-sap-batch.json', 9, 'v1.0'
);

INSERT INTO petragentic.main.integration_catalogue
(id, created_at, requirement_summary, tool_chosen, protocol,
 data_format, auth_method, cos_object_key, usage_count, prompt_version)
VALUES
(
  'seed-0009-redwood-finance-close',
  TIMESTAMP '2025-02-14 18:00:00',
  'Automate financial month-close sequence across SAP FICO, Hyperion, and IBM Cognos. Critical SLA: complete by 23:59 on last business day.',
  'IBM Redwood', 'REST', 'JSON', 'service principal / managed identity',
  'designs/seed-0009-redwood-finance-close.json', 7, 'v1.0'
);

INSERT INTO petragentic.main.integration_catalogue
(id, created_at, requirement_summary, tool_chosen, protocol,
 data_format, auth_method, cos_object_key, usage_count, prompt_version)
VALUES
(
  'seed-0010-redwood-hr-sync',
  TIMESTAMP '2025-03-05 06:30:00',
  'Nightly synchronisation of employee master data from SAP HCM to Workday via IBM Cloud. Delta-only sync, CSV format, PGP encryption.',
  'IBM Redwood', 'file-based', 'CSV', 'mTLS / certificate',
  'designs/seed-0010-redwood-hr-sync.json', 4, 'v1.0'
);

INSERT INTO petragentic.main.integration_catalogue
(id, created_at, requirement_summary, tool_chosen, protocol,
 data_format, auth_method, cos_object_key, usage_count, prompt_version)
VALUES
(
  'seed-0011-ala-m365-sharepoint',
  TIMESTAMP '2025-02-01 13:45:00',
  'Automate document approval workflow: SharePoint form triggers email approval in Outlook, updates Dynamics 365, notifies Teams.',
  'Azure Logic Apps', 'REST', 'JSON', 'service principal / managed identity',
  'designs/seed-0011-ala-m365-sharepoint.json', 3, 'v1.0'
);

INSERT INTO petragentic.main.integration_catalogue
(id, created_at, requirement_summary, tool_chosen, protocol,
 data_format, auth_method, cos_object_key, usage_count, prompt_version)
VALUES
(
  'seed-0012-ala-saas-connector',
  TIMESTAMP '2025-03-10 15:00:00',
  'Sync Salesforce opportunity close events to SAP SD order creation. Near real-time, REST webhooks, Azure API Management for routing.',
  'Azure Logic Apps', 'REST', 'JSON', 'OAuth 2.0',
  'designs/seed-0012-ala-saas-connector.json', 2, 'v1.0'
);
