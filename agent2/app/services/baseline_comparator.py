"""
agent2/app/services/baseline_comparator.py
────────────────────────────────────────────
Fetches the Gold Image baseline from watsonx.data server_baselines table
and provides comparison utilities.

The Gold Image baseline defines the expected (approved) state for each
server class. The comparator diffs the collected BaselineSnapshot against
the baseline and returns lists of unexpected deviations.

Table schema (Iceberg):
  server_baselines (
    server_class     VARCHAR,
    category         VARCHAR,   -- 'folder_permission' | 'share' | 'group_member' | 'service_account'
    attribute_key    VARCHAR,   -- e.g. path, share_name, group_name, service_name
    expected_value   VARCHAR,   -- JSON-serialised expected value
    updated_at       TIMESTAMP
  )
"""

import json
from dataclasses import dataclass
from typing import Any

from shared.config import Settings
from shared.exceptions import BaselineNotFoundError
from shared.logging import get_logger
from shared.wxdata_client import execute_query
from agent2.app.models.response import BaselineSnapshot

logger = get_logger(__name__)

_TABLE = "{catalog}.{schema}.server_baselines"


def _table(settings: Settings) -> str:
    return _TABLE.format(catalog=settings.wxdata_catalog, schema=settings.wxdata_schema)


@dataclass
class BaselineDiff:
    """A single deviation between collected state and the Gold Image baseline."""
    category: str          # 'folder_permission' | 'share' | 'group_member' | 'service_account'
    attribute_key: str     # The specific resource that differs
    expected: Any          # What the baseline says it should be
    actual: Any            # What was collected


def fetch_baseline(settings: Settings, server_class: str) -> dict[str, dict[str, Any]]:
    """
    Load the Gold Image baseline for the given server class from watsonx.data.

    Returns: {category: {attribute_key: expected_value}}
    Raises: BaselineNotFoundError if no rows found for server_class
    """
    sql = f"""
        SELECT category, attribute_key, expected_value
        FROM {_table(settings)}
        WHERE server_class = '{server_class}'
        ORDER BY category, attribute_key
    """
    rows = execute_query(settings, sql)
    if not rows:
        raise BaselineNotFoundError(server_class=server_class)

    baseline: dict[str, dict[str, Any]] = {}
    for row in rows:
        cat = row["category"]
        key = row["attribute_key"]
        try:
            val = json.loads(row["expected_value"])
        except (json.JSONDecodeError, TypeError):
            val = row["expected_value"]
        baseline.setdefault(cat, {})[key] = val

    logger.info(
        "Baseline loaded",
        extra={"server_class": server_class, "categories": list(baseline.keys())},
    )
    return baseline


def compare_snapshot(
    snapshot: BaselineSnapshot,
    baseline: dict[str, dict[str, Any]],
) -> list[BaselineDiff]:
    """
    Diff a collected BaselineSnapshot against a loaded baseline.

    Returns a list of BaselineDiff objects — one per deviation.
    """
    diffs: list[BaselineDiff] = []

    # ── Folder permissions ────────────────────────────────────────────────────
    baseline_folders = baseline.get("folder_permission", {})
    actual_folder_map: dict[str, list[str]] = {}
    for fp in snapshot.folder_permissions:
        actual_folder_map.setdefault(fp.path, []).append(fp.permissions)

    for path, expected_perms in baseline_folders.items():
        actual_perms = actual_folder_map.get(path, [])
        expected_set = set(expected_perms) if isinstance(expected_perms, list) else {expected_perms}
        actual_set = set(actual_perms)

        # Unexpected permissions (present but not in baseline)
        unexpected = actual_set - expected_set
        for perm in unexpected:
            diffs.append(BaselineDiff(
                category="folder_permission",
                attribute_key=path,
                expected=sorted(expected_set),
                actual=perm,
            ))

        # Missing permissions (in baseline but not collected)
        missing = expected_set - actual_set
        for perm in missing:
            diffs.append(BaselineDiff(
                category="folder_permission",
                attribute_key=path,
                expected=perm,
                actual="<not found>",
            ))

    # ── SMB shares ────────────────────────────────────────────────────────────
    baseline_shares = baseline.get("share", {})
    actual_share_map = {s.share_name: s for s in snapshot.shares}

    for share_name, expected_access in baseline_shares.items():
        if share_name not in actual_share_map:
            diffs.append(BaselineDiff(
                category="share",
                attribute_key=share_name,
                expected=expected_access,
                actual="<share not found>",
            ))
            continue
        actual_rights = set(actual_share_map[share_name].access_rights)
        expected_rights = set(expected_access) if isinstance(expected_access, list) else {expected_access}
        for right in actual_rights - expected_rights:
            diffs.append(BaselineDiff(
                category="share",
                attribute_key=share_name,
                expected=sorted(expected_rights),
                actual=right,
            ))

    # New shares not in baseline
    for share_name in actual_share_map:
        if share_name not in baseline_shares:
            diffs.append(BaselineDiff(
                category="share",
                attribute_key=share_name,
                expected="<not in baseline>",
                actual=actual_share_map[share_name].access_rights,
            ))

    # ── Local group memberships ───────────────────────────────────────────────
    baseline_groups = baseline.get("group_member", {})
    actual_group_map: dict[str, set[str]] = {}
    for gm in snapshot.local_groups:
        actual_group_map.setdefault(gm.group_name, set()).add(gm.member)

    for group_name, expected_members in baseline_groups.items():
        expected_set = set(expected_members) if isinstance(expected_members, list) else {expected_members}
        actual_members = actual_group_map.get(group_name, set())
        for member in actual_members - expected_set:
            diffs.append(BaselineDiff(
                category="group_member",
                attribute_key=group_name,
                expected=sorted(expected_set),
                actual=member,
            ))

    # ── Service accounts ──────────────────────────────────────────────────────
    baseline_services = baseline.get("service_account", {})
    actual_svc_map = {s.service_name: s for s in snapshot.service_accounts}

    for svc_name, expected_account in baseline_services.items():
        if svc_name in actual_svc_map:
            actual_acct = actual_svc_map[svc_name].account
            if actual_acct != expected_account:
                diffs.append(BaselineDiff(
                    category="service_account",
                    attribute_key=svc_name,
                    expected=expected_account,
                    actual=actual_acct,
                ))
        else:
            # Service in baseline not found — could indicate removal or rename
            diffs.append(BaselineDiff(
                category="service_account",
                attribute_key=svc_name,
                expected=expected_account,
                actual="<service not found>",
            ))

    logger.info(
        "Baseline comparison complete",
        extra={"server": snapshot.server, "diffs": len(diffs)},
    )
    return diffs
