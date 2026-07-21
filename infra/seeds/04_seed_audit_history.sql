-- =============================================================================
-- infra/seeds/04_seed_audit_history.sql
-- =============================================================================
-- Sample historical audit scan data for audit_scans + drift_findings tables.
--
-- Simulates 2 periodic scan runs across 4 servers showing:
--   WIN-SRV-001  standard-windows-server  Always compliant
--   WIN-SRV-002  standard-windows-server  Persistent non-compliant (recurring findings)
--   WIN-SRV-003  standard-windows-server  New server with critical findings, improving over time
--   WIN-DC-001   domain-controller        One high finding in run 1, remediated by run 2
--
-- This enables:
--   - new vs recurring detection in audit_store.py from day one
--   - meaningful dashboard data without running real scans first
--   - Iceberg time-travel query demonstration
-- =============================================================================


-- ============================================================================
-- SCAN RUN 1 -- 2025-01-20 (Periodic audit, 4 servers)
-- ============================================================================

INSERT INTO petragentic.main.audit_scans
(scan_id, server, server_class, scan_type, started_at, completed_at,
 compliance_status, total_findings, critical_count, triggered_by)
VALUES ('scan-2025-01-20-001', 'WIN-SRV-001', 'standard-windows-server', 'periodic_audit',
 TIMESTAMP '2025-01-20 06:01:00', TIMESTAMP '2025-01-20 06:03:12',
 'compliant', 0, 0, 'github_actions_scheduled');

INSERT INTO petragentic.main.audit_scans
(scan_id, server, server_class, scan_type, started_at, completed_at,
 compliance_status, total_findings, critical_count, triggered_by)
VALUES ('scan-2025-01-20-002', 'WIN-SRV-002', 'standard-windows-server', 'periodic_audit',
 TIMESTAMP '2025-01-20 06:03:15', TIMESTAMP '2025-01-20 06:05:44',
 'non_compliant', 3, 1, 'github_actions_scheduled');

INSERT INTO petragentic.main.audit_scans
(scan_id, server, server_class, scan_type, started_at, completed_at,
 compliance_status, total_findings, critical_count, triggered_by)
VALUES ('scan-2025-01-20-003', 'WIN-SRV-003', 'standard-windows-server', 'new_validation',
 TIMESTAMP '2025-01-20 06:05:50', TIMESTAMP '2025-01-20 06:08:30',
 'non_compliant', 5, 2, 'manual');

INSERT INTO petragentic.main.audit_scans
(scan_id, server, server_class, scan_type, started_at, completed_at,
 compliance_status, total_findings, critical_count, triggered_by)
VALUES ('scan-2025-01-20-004', 'WIN-DC-001', 'domain-controller', 'periodic_audit',
 TIMESTAMP '2025-01-20 06:09:00', TIMESTAMP '2025-01-20 06:11:20',
 'non_compliant', 1, 0, 'github_actions_scheduled');

-- Findings for WIN-SRV-002 (scan run 1)

INSERT INTO petragentic.main.drift_findings
(finding_id, scan_id, server, category, severity, title,
 cis_control_id, nist_control, is_new, created_at)
VALUES ('find-2025-01-20-001', 'scan-2025-01-20-002', 'WIN-SRV-002',
 'group_member', 'critical', 'Unauthorised member in Administrators',
 'CIS 1.1.1', 'AC-2', 'true', TIMESTAMP '2025-01-20 06:04:00');

INSERT INTO petragentic.main.drift_findings
(finding_id, scan_id, server, category, severity, title,
 cis_control_id, nist_control, is_new, created_at)
VALUES ('find-2025-01-20-002', 'scan-2025-01-20-002', 'WIN-SRV-002',
 'share', 'high', 'Share access deviation: DataShare',
 'CIS 9.2.1', 'AC-17', 'true', TIMESTAMP '2025-01-20 06:04:30');

INSERT INTO petragentic.main.drift_findings
(finding_id, scan_id, server, category, severity, title,
 cis_control_id, nist_control, is_new, created_at)
VALUES ('find-2025-01-20-003', 'scan-2025-01-20-002', 'WIN-SRV-002',
 'folder_permission', 'high', 'Unexpected NTFS permission on C:\\Scripts',
 'CIS 18.9.85.2', 'CM-6', 'true', TIMESTAMP '2025-01-20 06:05:00');

-- Findings for WIN-SRV-003 (new server, scan run 1 — 5 findings including 2 critical)

INSERT INTO petragentic.main.drift_findings
(finding_id, scan_id, server, category, severity, title,
 cis_control_id, nist_control, is_new, created_at)
VALUES ('find-2025-01-20-004', 'scan-2025-01-20-003', 'WIN-SRV-003',
 'group_member', 'critical', 'Unauthorised member in Administrators',
 'CIS 1.1.1', 'AC-2', 'true', TIMESTAMP '2025-01-20 06:06:10');

INSERT INTO petragentic.main.drift_findings
(finding_id, scan_id, server, category, severity, title,
 cis_control_id, nist_control, is_new, created_at)
VALUES ('find-2025-01-20-005', 'scan-2025-01-20-003', 'WIN-SRV-003',
 'service_account', 'critical', 'Service account drift: W3SVC',
 'CIS 3.1', 'IA-5', 'true', TIMESTAMP '2025-01-20 06:06:45');

INSERT INTO petragentic.main.drift_findings
(finding_id, scan_id, server, category, severity, title,
 cis_control_id, nist_control, is_new, created_at)
VALUES ('find-2025-01-20-006', 'scan-2025-01-20-003', 'WIN-SRV-003',
 'share', 'high', 'Share access deviation: WebContent',
 'CIS 9.2.1', 'AC-17', 'true', TIMESTAMP '2025-01-20 06:07:00');

INSERT INTO petragentic.main.drift_findings
(finding_id, scan_id, server, category, severity, title,
 cis_control_id, nist_control, is_new, created_at)
VALUES ('find-2025-01-20-007', 'scan-2025-01-20-003', 'WIN-SRV-003',
 'folder_permission', 'high', 'Unexpected NTFS permission on C:\\inetpub',
 'CIS 2.3.10.2', 'AC-6', 'true', TIMESTAMP '2025-01-20 06:07:30');

INSERT INTO petragentic.main.drift_findings
(finding_id, scan_id, server, category, severity, title,
 cis_control_id, nist_control, is_new, created_at)
VALUES ('find-2025-01-20-008', 'scan-2025-01-20-003', 'WIN-SRV-003',
 'group_member', 'medium', 'Unauthorised member in Remote Desktop Users',
 'CIS 2.2.26', 'AC-17', 'true', TIMESTAMP '2025-01-20 06:07:50');

-- Findings for WIN-DC-001 (scan run 1 — 1 high finding)

INSERT INTO petragentic.main.drift_findings
(finding_id, scan_id, server, category, severity, title,
 cis_control_id, nist_control, is_new, created_at)
VALUES ('find-2025-01-20-009', 'scan-2025-01-20-004', 'WIN-DC-001',
 'group_member', 'high', 'Unauthorised member in Remote Desktop Users',
 'CIS 2.2.26', 'AC-17', 'true', TIMESTAMP '2025-01-20 06:10:00');


-- ============================================================================
-- SCAN RUN 2 -- 2025-02-17 (Periodic audit — WIN-SRV-003 improving, WIN-DC-001 fixed)
-- ============================================================================

INSERT INTO petragentic.main.audit_scans
(scan_id, server, server_class, scan_type, started_at, completed_at,
 compliance_status, total_findings, critical_count, triggered_by)
VALUES ('scan-2025-02-17-001', 'WIN-SRV-001', 'standard-windows-server', 'periodic_audit',
 TIMESTAMP '2025-02-17 06:01:00', TIMESTAMP '2025-02-17 06:03:05',
 'compliant', 0, 0, 'github_actions_scheduled');

INSERT INTO petragentic.main.audit_scans
(scan_id, server, server_class, scan_type, started_at, completed_at,
 compliance_status, total_findings, critical_count, triggered_by)
VALUES ('scan-2025-02-17-002', 'WIN-SRV-002', 'standard-windows-server', 'periodic_audit',
 TIMESTAMP '2025-02-17 06:03:10', TIMESTAMP '2025-02-17 06:05:55',
 'non_compliant', 3, 1, 'github_actions_scheduled');

INSERT INTO petragentic.main.audit_scans
(scan_id, server, server_class, scan_type, started_at, completed_at,
 compliance_status, total_findings, critical_count, triggered_by)
VALUES ('scan-2025-02-17-003', 'WIN-SRV-003', 'standard-windows-server', 'periodic_audit',
 TIMESTAMP '2025-02-17 06:06:00', TIMESTAMP '2025-02-17 06:09:10',
 'non_compliant', 3, 0, 'github_actions_scheduled');

INSERT INTO petragentic.main.audit_scans
(scan_id, server, server_class, scan_type, started_at, completed_at,
 compliance_status, total_findings, critical_count, triggered_by)
VALUES ('scan-2025-02-17-004', 'WIN-DC-001', 'domain-controller', 'periodic_audit',
 TIMESTAMP '2025-02-17 06:09:15', TIMESTAMP '2025-02-17 06:11:00',
 'compliant', 0, 0, 'github_actions_scheduled');

-- Findings for WIN-SRV-002 (scan run 2 — 2 recurring + 1 new)

INSERT INTO petragentic.main.drift_findings
(finding_id, scan_id, server, category, severity, title,
 cis_control_id, nist_control, is_new, created_at)
VALUES ('find-2025-02-17-001', 'scan-2025-02-17-002', 'WIN-SRV-002',
 'group_member', 'critical', 'Unauthorised member in Administrators',
 'CIS 1.1.1', 'AC-2', 'false', TIMESTAMP '2025-02-17 06:04:10');

INSERT INTO petragentic.main.drift_findings
(finding_id, scan_id, server, category, severity, title,
 cis_control_id, nist_control, is_new, created_at)
VALUES ('find-2025-02-17-002', 'scan-2025-02-17-002', 'WIN-SRV-002',
 'folder_permission', 'high', 'Unexpected NTFS permission on C:\\Scripts',
 'CIS 18.9.85.2', 'CM-6', 'false', TIMESTAMP '2025-02-17 06:04:45');

INSERT INTO petragentic.main.drift_findings
(finding_id, scan_id, server, category, severity, title,
 cis_control_id, nist_control, is_new, created_at)
VALUES ('find-2025-02-17-003', 'scan-2025-02-17-002', 'WIN-SRV-002',
 'service_account', 'high', 'Service account drift: BackupExec',
 'CIS 3.1', 'IA-5', 'true', TIMESTAMP '2025-02-17 06:05:00');

-- Findings for WIN-SRV-003 (scan run 2 — 2 critical remediated, 3 remaining)

INSERT INTO petragentic.main.drift_findings
(finding_id, scan_id, server, category, severity, title,
 cis_control_id, nist_control, is_new, created_at)
VALUES ('find-2025-02-17-004', 'scan-2025-02-17-003', 'WIN-SRV-003',
 'share', 'high', 'Share access deviation: WebContent',
 'CIS 9.2.1', 'AC-17', 'false', TIMESTAMP '2025-02-17 06:07:00');

INSERT INTO petragentic.main.drift_findings
(finding_id, scan_id, server, category, severity, title,
 cis_control_id, nist_control, is_new, created_at)
VALUES ('find-2025-02-17-005', 'scan-2025-02-17-003', 'WIN-SRV-003',
 'folder_permission', 'high', 'Unexpected NTFS permission on C:\\inetpub',
 'CIS 2.3.10.2', 'AC-6', 'false', TIMESTAMP '2025-02-17 06:07:30');

INSERT INTO petragentic.main.drift_findings
(finding_id, scan_id, server, category, severity, title,
 cis_control_id, nist_control, is_new, created_at)
VALUES ('find-2025-02-17-006', 'scan-2025-02-17-003', 'WIN-SRV-003',
 'folder_permission', 'medium', 'Unexpected NTFS permission on C:\\Scripts',
 'CIS 18.9.85.2', 'CM-6', 'true', TIMESTAMP '2025-02-17 06:08:00');
