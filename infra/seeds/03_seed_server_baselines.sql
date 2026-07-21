-- =============================================================================
-- infra/seeds/03_seed_server_baselines.sql
-- =============================================================================
-- Gold Image baseline definitions for Agent 2.
--
-- Server classes seeded:
--   standard-windows-server  -- general-purpose Windows Server 2019/2022 member server
--   domain-controller        -- Active Directory Domain Controller
--   sql-server               -- SQL Server host
--
-- expected_value holds a JSON-encoded value:
--   folder_permission  -> JSON array of approved "IDENTITY:RIGHTS" strings
--   share              -> JSON array of approved "ACCOUNT:ACCESS" strings
--   group_member       -> JSON array of approved member names
--   service_account    -> JSON string of approved service account name
--
-- Based on:
--   CIS Microsoft Windows Server 2022 Benchmark v2.0
--   NIST SP 800-53 Rev 5
-- =============================================================================


-- ============================================================================
-- CLASS: standard-windows-server
-- ============================================================================

-- Folder permissions

INSERT INTO petragentic.main.server_baselines
(server_class, category, attribute_key, expected_value, updated_at, updated_by)
VALUES ('standard-windows-server', 'folder_permission', 'C:\\',
 '["NT AUTHORITY\\\\SYSTEM:(F)","BUILTIN\\\\Administrators:(F)","BUILTIN\\\\Users:(RX)"]',
 TIMESTAMP '2025-01-01 00:00:00', 'security-baseline-v1.0');

INSERT INTO petragentic.main.server_baselines
(server_class, category, attribute_key, expected_value, updated_at, updated_by)
VALUES ('standard-windows-server', 'folder_permission', 'C:\\Windows',
 '["NT AUTHORITY\\\\SYSTEM:(F)","BUILTIN\\\\Administrators:(F)","BUILTIN\\\\Users:(RX)","CREATOR OWNER:(OI)(CI)(IO)(F)"]',
 TIMESTAMP '2025-01-01 00:00:00', 'security-baseline-v1.0');

INSERT INTO petragentic.main.server_baselines
(server_class, category, attribute_key, expected_value, updated_at, updated_by)
VALUES ('standard-windows-server', 'folder_permission', 'C:\\Program Files',
 '["NT AUTHORITY\\\\SYSTEM:(F)","BUILTIN\\\\Administrators:(F)","BUILTIN\\\\Users:(RX)"]',
 TIMESTAMP '2025-01-01 00:00:00', 'security-baseline-v1.0');

INSERT INTO petragentic.main.server_baselines
(server_class, category, attribute_key, expected_value, updated_at, updated_by)
VALUES ('standard-windows-server', 'folder_permission', 'C:\\Program Files (x86)',
 '["NT AUTHORITY\\\\SYSTEM:(F)","BUILTIN\\\\Administrators:(F)","BUILTIN\\\\Users:(RX)"]',
 TIMESTAMP '2025-01-01 00:00:00', 'security-baseline-v1.0');

INSERT INTO petragentic.main.server_baselines
(server_class, category, attribute_key, expected_value, updated_at, updated_by)
VALUES ('standard-windows-server', 'folder_permission', 'C:\\Users',
 '["NT AUTHORITY\\\\SYSTEM:(F)","BUILTIN\\\\Administrators:(F)","BUILTIN\\\\Users:(RX)(W)"]',
 TIMESTAMP '2025-01-01 00:00:00', 'security-baseline-v1.0');

INSERT INTO petragentic.main.server_baselines
(server_class, category, attribute_key, expected_value, updated_at, updated_by)
VALUES ('standard-windows-server', 'folder_permission', 'C:\\Scripts',
 '["NT AUTHORITY\\\\SYSTEM:(F)","BUILTIN\\\\Administrators:(F)"]',
 TIMESTAMP '2025-01-01 00:00:00', 'security-baseline-v1.0');

-- SMB Shares (standard server: admin shares only)

INSERT INTO petragentic.main.server_baselines
(server_class, category, attribute_key, expected_value, updated_at, updated_by)
VALUES ('standard-windows-server', 'share', 'ADMIN$',
 '["BUILTIN\\\\Administrators:Full"]',
 TIMESTAMP '2025-01-01 00:00:00', 'security-baseline-v1.0');

INSERT INTO petragentic.main.server_baselines
(server_class, category, attribute_key, expected_value, updated_at, updated_by)
VALUES ('standard-windows-server', 'share', 'IPC$',
 '["Everyone:Read"]',
 TIMESTAMP '2025-01-01 00:00:00', 'security-baseline-v1.0');

-- Local group memberships

INSERT INTO petragentic.main.server_baselines
(server_class, category, attribute_key, expected_value, updated_at, updated_by)
VALUES ('standard-windows-server', 'group_member', 'Administrators',
 '["DOMAIN\\\\Server-Admins","NT AUTHORITY\\\\SYSTEM","Administrator"]',
 TIMESTAMP '2025-01-01 00:00:00', 'security-baseline-v1.0');

INSERT INTO petragentic.main.server_baselines
(server_class, category, attribute_key, expected_value, updated_at, updated_by)
VALUES ('standard-windows-server', 'group_member', 'Remote Desktop Users',
 '["DOMAIN\\\\RDP-Standard-Servers"]',
 TIMESTAMP '2025-01-01 00:00:00', 'security-baseline-v1.0');

INSERT INTO petragentic.main.server_baselines
(server_class, category, attribute_key, expected_value, updated_at, updated_by)
VALUES ('standard-windows-server', 'group_member', 'Backup Operators',
 '["DOMAIN\\\\Backup-Svc-Account"]',
 TIMESTAMP '2025-01-01 00:00:00', 'security-baseline-v1.0');

-- Service accounts

INSERT INTO petragentic.main.server_baselines
(server_class, category, attribute_key, expected_value, updated_at, updated_by)
VALUES ('standard-windows-server', 'service_account', 'WinRM',
 '"NT AUTHORITY\\\\NetworkService"',
 TIMESTAMP '2025-01-01 00:00:00', 'security-baseline-v1.0');

INSERT INTO petragentic.main.server_baselines
(server_class, category, attribute_key, expected_value, updated_at, updated_by)
VALUES ('standard-windows-server', 'service_account', 'Spooler',
 '"NT AUTHORITY\\\\SYSTEM"',
 TIMESTAMP '2025-01-01 00:00:00', 'security-baseline-v1.0');

INSERT INTO petragentic.main.server_baselines
(server_class, category, attribute_key, expected_value, updated_at, updated_by)
VALUES ('standard-windows-server', 'service_account', 'W32Time',
 '"NT AUTHORITY\\\\LocalService"',
 TIMESTAMP '2025-01-01 00:00:00', 'security-baseline-v1.0');

INSERT INTO petragentic.main.server_baselines
(server_class, category, attribute_key, expected_value, updated_at, updated_by)
VALUES ('standard-windows-server', 'service_account', 'EventLog',
 '"NT AUTHORITY\\\\LocalService"',
 TIMESTAMP '2025-01-01 00:00:00', 'security-baseline-v1.0');


-- ============================================================================
-- CLASS: domain-controller
-- ============================================================================

-- Folder permissions

INSERT INTO petragentic.main.server_baselines
(server_class, category, attribute_key, expected_value, updated_at, updated_by)
VALUES ('domain-controller', 'folder_permission', 'C:\\',
 '["NT AUTHORITY\\\\SYSTEM:(F)","BUILTIN\\\\Administrators:(F)"]',
 TIMESTAMP '2025-01-01 00:00:00', 'security-baseline-v1.0');

INSERT INTO petragentic.main.server_baselines
(server_class, category, attribute_key, expected_value, updated_at, updated_by)
VALUES ('domain-controller', 'folder_permission', 'C:\\Windows\\SYSVOL',
 '["NT AUTHORITY\\\\SYSTEM:(F)","BUILTIN\\\\Administrators:(F)","Authenticated Users:(RX)"]',
 TIMESTAMP '2025-01-01 00:00:00', 'security-baseline-v1.0');

INSERT INTO petragentic.main.server_baselines
(server_class, category, attribute_key, expected_value, updated_at, updated_by)
VALUES ('domain-controller', 'folder_permission', 'C:\\Windows\\NTDS',
 '["NT AUTHORITY\\\\SYSTEM:(F)","BUILTIN\\\\Administrators:(F)"]',
 TIMESTAMP '2025-01-01 00:00:00', 'security-baseline-v1.0');

-- SMB Shares (DC: NETLOGON, SYSVOL, ADMIN$)

INSERT INTO petragentic.main.server_baselines
(server_class, category, attribute_key, expected_value, updated_at, updated_by)
VALUES ('domain-controller', 'share', 'NETLOGON',
 '["Authenticated Users:Read"]',
 TIMESTAMP '2025-01-01 00:00:00', 'security-baseline-v1.0');

INSERT INTO petragentic.main.server_baselines
(server_class, category, attribute_key, expected_value, updated_at, updated_by)
VALUES ('domain-controller', 'share', 'SYSVOL',
 '["Authenticated Users:Read"]',
 TIMESTAMP '2025-01-01 00:00:00', 'security-baseline-v1.0');

INSERT INTO petragentic.main.server_baselines
(server_class, category, attribute_key, expected_value, updated_at, updated_by)
VALUES ('domain-controller', 'share', 'ADMIN$',
 '["BUILTIN\\\\Administrators:Full"]',
 TIMESTAMP '2025-01-01 00:00:00', 'security-baseline-v1.0');

-- Local group memberships

INSERT INTO petragentic.main.server_baselines
(server_class, category, attribute_key, expected_value, updated_at, updated_by)
VALUES ('domain-controller', 'group_member', 'Administrators',
 '["DOMAIN\\\\Domain Admins","NT AUTHORITY\\\\SYSTEM"]',
 TIMESTAMP '2025-01-01 00:00:00', 'security-baseline-v1.0');

INSERT INTO petragentic.main.server_baselines
(server_class, category, attribute_key, expected_value, updated_at, updated_by)
VALUES ('domain-controller', 'group_member', 'Remote Desktop Users',
 '[]',
 TIMESTAMP '2025-01-01 00:00:00', 'security-baseline-v1.0');

-- Service accounts

INSERT INTO petragentic.main.server_baselines
(server_class, category, attribute_key, expected_value, updated_at, updated_by)
VALUES ('domain-controller', 'service_account', 'NTDS',
 '"NT AUTHORITY\\\\SYSTEM"',
 TIMESTAMP '2025-01-01 00:00:00', 'security-baseline-v1.0');

INSERT INTO petragentic.main.server_baselines
(server_class, category, attribute_key, expected_value, updated_at, updated_by)
VALUES ('domain-controller', 'service_account', 'Netlogon',
 '"NT AUTHORITY\\\\SYSTEM"',
 TIMESTAMP '2025-01-01 00:00:00', 'security-baseline-v1.0');

INSERT INTO petragentic.main.server_baselines
(server_class, category, attribute_key, expected_value, updated_at, updated_by)
VALUES ('domain-controller', 'service_account', 'DNS',
 '"NT AUTHORITY\\\\SYSTEM"',
 TIMESTAMP '2025-01-01 00:00:00', 'security-baseline-v1.0');


-- ============================================================================
-- CLASS: sql-server
-- ============================================================================

-- Folder permissions

INSERT INTO petragentic.main.server_baselines
(server_class, category, attribute_key, expected_value, updated_at, updated_by)
VALUES ('sql-server', 'folder_permission', 'C:\\',
 '["NT AUTHORITY\\\\SYSTEM:(F)","BUILTIN\\\\Administrators:(F)","BUILTIN\\\\Users:(RX)"]',
 TIMESTAMP '2025-01-01 00:00:00', 'security-baseline-v1.0');

INSERT INTO petragentic.main.server_baselines
(server_class, category, attribute_key, expected_value, updated_at, updated_by)
VALUES ('sql-server', 'folder_permission', 'C:\\Program Files\\Microsoft SQL Server',
 '["NT AUTHORITY\\\\SYSTEM:(F)","BUILTIN\\\\Administrators:(F)","NT SERVICE\\\\MSSQLSERVER:(RX)"]',
 TIMESTAMP '2025-01-01 00:00:00', 'security-baseline-v1.0');

INSERT INTO petragentic.main.server_baselines
(server_class, category, attribute_key, expected_value, updated_at, updated_by)
VALUES ('sql-server', 'folder_permission', 'C:\\SQLData',
 '["NT AUTHORITY\\\\SYSTEM:(F)","BUILTIN\\\\Administrators:(F)","NT SERVICE\\\\MSSQLSERVER:(F)"]',
 TIMESTAMP '2025-01-01 00:00:00', 'security-baseline-v1.0');

INSERT INTO petragentic.main.server_baselines
(server_class, category, attribute_key, expected_value, updated_at, updated_by)
VALUES ('sql-server', 'folder_permission', 'C:\\SQLBackups',
 '["NT AUTHORITY\\\\SYSTEM:(F)","BUILTIN\\\\Administrators:(F)","NT SERVICE\\\\MSSQLSERVER:(F)","DOMAIN\\\\Backup-Svc-Account:(M)"]',
 TIMESTAMP '2025-01-01 00:00:00', 'security-baseline-v1.0');

-- SMB Shares

INSERT INTO petragentic.main.server_baselines
(server_class, category, attribute_key, expected_value, updated_at, updated_by)
VALUES ('sql-server', 'share', 'ADMIN$',
 '["BUILTIN\\\\Administrators:Full"]',
 TIMESTAMP '2025-01-01 00:00:00', 'security-baseline-v1.0');

INSERT INTO petragentic.main.server_baselines
(server_class, category, attribute_key, expected_value, updated_at, updated_by)
VALUES ('sql-server', 'share', 'SQLBackups',
 '["DOMAIN\\\\Backup-Svc-Account:Change","BUILTIN\\\\Administrators:Full"]',
 TIMESTAMP '2025-01-01 00:00:00', 'security-baseline-v1.0');

-- Local group memberships

INSERT INTO petragentic.main.server_baselines
(server_class, category, attribute_key, expected_value, updated_at, updated_by)
VALUES ('sql-server', 'group_member', 'Administrators',
 '["DOMAIN\\\\SQL-Server-Admins","NT AUTHORITY\\\\SYSTEM","Administrator"]',
 TIMESTAMP '2025-01-01 00:00:00', 'security-baseline-v1.0');

INSERT INTO petragentic.main.server_baselines
(server_class, category, attribute_key, expected_value, updated_at, updated_by)
VALUES ('sql-server', 'group_member', 'Remote Desktop Users',
 '["DOMAIN\\\\RDP-SQL-Admins"]',
 TIMESTAMP '2025-01-01 00:00:00', 'security-baseline-v1.0');

-- Service accounts

INSERT INTO petragentic.main.server_baselines
(server_class, category, attribute_key, expected_value, updated_at, updated_by)
VALUES ('sql-server', 'service_account', 'MSSQLSERVER',
 '"NT SERVICE\\\\MSSQLSERVER"',
 TIMESTAMP '2025-01-01 00:00:00', 'security-baseline-v1.0');

INSERT INTO petragentic.main.server_baselines
(server_class, category, attribute_key, expected_value, updated_at, updated_by)
VALUES ('sql-server', 'service_account', 'SQLSERVERAGENT',
 '"DOMAIN\\\\svc-sqlagent"',
 TIMESTAMP '2025-01-01 00:00:00', 'security-baseline-v1.0');

INSERT INTO petragentic.main.server_baselines
(server_class, category, attribute_key, expected_value, updated_at, updated_by)
VALUES ('sql-server', 'service_account', 'SQLBrowser',
 '"NT AUTHORITY\\\\LocalService"',
 TIMESTAMP '2025-01-01 00:00:00', 'security-baseline-v1.0');

INSERT INTO petragentic.main.server_baselines
(server_class, category, attribute_key, expected_value, updated_at, updated_by)
VALUES ('sql-server', 'service_account', 'ReportServer',
 '"DOMAIN\\\\svc-ssrs"',
 TIMESTAMP '2025-01-01 00:00:00', 'security-baseline-v1.0');
