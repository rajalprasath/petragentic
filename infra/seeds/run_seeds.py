#!/usr/bin/env python3
"""
infra/seeds/run_seeds.py
─────────────────────────
Execute all seed SQL files against the watsonx.data Presto REST endpoint
in the correct order:
  01_ddl_create_tables.sql           -- CREATE TABLE IF NOT EXISTS
  02_seed_integration_catalogue.sql  -- Agent 1 design history
  03_seed_server_baselines.sql       -- Agent 2 Gold Image baselines
  04_seed_audit_history.sql          -- Agent 2 historical scan results

Usage (from repo root):
  python infra/seeds/run_seeds.py

Dry-run (validate SQL without executing):
  DRY_RUN=true python infra/seeds/run_seeds.py

Prerequisites:
  pip install requests python-dotenv
  .env file in repo root with WXDATA_PRESTO_URL and WXDATA_AUTH_TOKEN
"""

import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

PRESTO_URL = os.environ.get("WXDATA_PRESTO_URL", "").rstrip("/")
AUTH_TOKEN = os.environ.get("WXDATA_AUTH_TOKEN", "")
CATALOG    = os.environ.get("WXDATA_CATALOG", "petragentic")
SCHEMA     = os.environ.get("WXDATA_SCHEMA", "main")
DRY_RUN    = os.environ.get("DRY_RUN", "false").lower() == "true"

SEEDS_DIR  = Path(__file__).parent
SEED_FILES = [
    "01_ddl_create_tables.sql",
    "02_seed_integration_catalogue.sql",
    "03_seed_server_baselines.sql",
    "04_seed_audit_history.sql",
]

HEADERS = {
    "Content-Type": "text/plain",
    "Authorization": f"Bearer {AUTH_TOKEN}",
    "X-Presto-User":    "petragentic-seed",
    "X-Presto-Catalog": CATALOG,
    "X-Presto-Schema":  SCHEMA,
}


def _poll(next_uri: str, preview: str) -> bool:
    polls = 0
    while next_uri and polls < 120:
        time.sleep(0.5)
        resp = requests.get(next_uri, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        state = data.get("stats", {}).get("state", "UNKNOWN")
        next_uri = data.get("nextUri")
        if state == "FAILED":
            print(f"    FAILED: {data.get('error', {}).get('message', '?')}")
            return False
        if state == "FINISHED" and not next_uri:
            return True
        polls += 1
    return True


def execute(sql: str) -> bool:
    preview = " ".join(sql.split())[:90]
    if DRY_RUN:
        print(f"  [DRY-RUN] {preview}...")
        return True
    resp = requests.post(f"{PRESTO_URL}/v1/statement", data=sql, headers=HEADERS, timeout=30)
    try:
        resp.raise_for_status()
    except requests.HTTPError:
        print(f"    HTTP {resp.status_code}: {resp.text[:200]}")
        return False
    data = resp.json()
    if data.get("stats", {}).get("state") == "FAILED":
        print(f"    FAILED: {data.get('error', {}).get('message', '?')}")
        return False
    return _poll(data.get("nextUri"), preview)


def parse_statements(text: str) -> list[str]:
    """Split SQL file into individual statements on semicolons."""
    stmts, current = [], []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("--"):
            continue
        # Strip inline comments
        if "--" in line:
            line = line[:line.index("--")].strip()
        if not line:
            continue
        if line.endswith(";"):
            current.append(line[:-1].rstrip())
            stmt = " ".join(current).strip()
            if stmt:
                stmts.append(stmt)
            current = []
        elif line == ";":
            stmt = " ".join(current).strip()
            if stmt:
                stmts.append(stmt)
            current = []
        else:
            current.append(line)
    remaining = " ".join(current).strip()
    if remaining:
        stmts.append(remaining)
    return [s for s in stmts if s]


def main() -> int:
    if not DRY_RUN and (not PRESTO_URL or not AUTH_TOKEN):
        print("ERROR: WXDATA_PRESTO_URL and WXDATA_AUTH_TOKEN must be set.")
        print("       Set them in .env or as environment variables.")
        print("       Use DRY_RUN=true to validate SQL without connecting.")
        return 1

    print("Petragentic -- watsonx.data seed runner")
    print(f"URL:     {PRESTO_URL or '(dry-run mode)'}")
    print(f"Catalog: {CATALOG}.{SCHEMA}")
    print(f"Dry run: {DRY_RUN}\n")

    ok_total, err_total = 0, 0

    for fname in SEED_FILES:
        fpath = SEEDS_DIR / fname
        if not fpath.exists():
            print(f"[SKIP] {fname} not found\n")
            continue

        print(f"── {fname} ──────────────────────────────")
        stmts = parse_statements(fpath.read_text(encoding="utf-8"))
        print(f"   {len(stmts)} statements")

        for i, stmt in enumerate(stmts, 1):
            preview = " ".join(stmt.split())[:80]
            print(f"   [{i:03d}] {preview}...")
            if execute(stmt):
                ok_total += 1
                print("         OK")
            else:
                err_total += 1
                print("         FAILED (continuing)")
        print()

    print(f"{'─' * 45}")
    print(f"Done: {ok_total} OK, {err_total} failed")
    return 0 if err_total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
