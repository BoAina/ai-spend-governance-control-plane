#!/usr/bin/env python3
"""
The Wire
========
Pulls live transactions from the Ramp Mock API,
transforms them into Spend Platform X format,
runs them through the Policy Gate,
and writes audit + ERP files.

This is the full loop:
  Ramp API → Transform → Policy Gate → Audit → ERP Writeback

Run:
  python wire.py
"""

import json
import sys
import requests
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
RAMP_BASE      = "http://localhost:8100"
RAMP_TOKEN     = "mock_ramp_token_ainalabs_2026"
CONTROL_PLANE  = Path(__file__).parent.resolve()   # repo root — works on any machine
OUTPUT_DIR     = CONTROL_PLANE / "outputs" / "wired"

sys.path.insert(0, str(CONTROL_PLANE))
from src.policy_gate import evaluate_policy_gate
from src.authorization_engine import build_erp_writeback
from src.audit_logger import write_decision_file, write_erp_file

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {"Authorization": f"Bearer {RAMP_TOKEN}"}

# ── MCC → Spend Platform X category map ──────────────────────────────────────
MCC_CATEGORY_MAP = {
    "3020": "Travel",           # Airlines
    "5812": "Meals_Entertainment",
    "7372": "SaaS_Subscription",
    "5732": "Hardware",
    "5999": "Uncategorized",
    "7011": "Travel",           # Hotels
    "4111": "Travel",           # Local transit
}

FUNDING_MAP = {
    "dept_001": "OPERATING",   # Engineering
    "dept_002": "OPERATING",   # Sales
    "dept_003": "OPERATING",   # Marketing
    "dept_004": "OPERATING",   # Finance
    "dept_005": "OPERATING",   # Operations
}

BUDGET_MAP = {
    "dept_001": 50000.0,
    "dept_002": 75000.0,
    "dept_003": 100000.0,
    "dept_004": 30000.0,
    "dept_005": 25000.0,
}

DIVIDER = "─" * 62


def ramp_to_control_plane(txn: dict) -> dict:
    """Transform a Ramp API transaction into Spend Platform X request format."""
    mcc  = txn.get("merchant_category_code", "5999")
    dept = txn.get("department_id", "dept_002")
    return {
        "request_id":      txn["id"].upper(),
        "employee_id":     txn.get("user_id", "USR-000").upper(),
        "department":      dept.upper(),
        "vendor":          txn["merchant_name"],
        "description":     f"{txn.get('sk_category_name','Spend')} — {txn['merchant_name']}",
        "amount":          txn["amount"] / 100,          # cents → dollars
        "funding_source":  FUNDING_MAP.get(dept, "OPERATING"),
        "budget_code":     f"BDG-{dept.upper()}",
        "merchant_category": MCC_CATEGORY_MAP.get(mcc, "Uncategorized"),
        "available_budget":  BUDGET_MAP.get(dept, 20000.0),
    }


def fetch_transactions() -> list[dict]:
    r = requests.get(f"{RAMP_BASE}/developer/graphql/v1/transactions", headers=HEADERS)
    r.raise_for_status()
    return r.json()["data"]


def fetch_policy_check(txn_id: str) -> dict:
    r = requests.get(f"{RAMP_BASE}/developer/graphql/v1/transactions/{txn_id}/policy_check", headers=HEADERS)
    r.raise_for_status()
    return r.json()


def load_rules() -> tuple[dict, dict]:
    policy_dir = CONTROL_PLANE / "policies"
    grant = json.loads((policy_dir / "grant_policy_rules.json").read_text())
    proc  = json.loads((policy_dir / "procurement_policy_rules.json").read_text())
    return grant, proc


def run():
    print()
    print("=" * 62)
    print("  THE WIRE — Ramp API → Spend Governance Control Plane")
    print("=" * 62)
    print()

    # Load rules
    grant_rules, procurement_rules = load_rules()

    # Fetch all transactions from Ramp mock
    transactions = fetch_transactions()
    print(f"  Pulled {len(transactions)} transactions from Ramp API\n")

    for txn in transactions:
        # Step 1: Ramp mock policy signal
        ramp_check = fetch_policy_check(txn["id"])

        # Step 2: Transform to control plane format
        request = ramp_to_control_plane(txn)

        # Step 3: Run through Policy Gate
        result = evaluate_policy_gate(
            request=request,
            grant_rules=grant_rules,
            procurement_rules=procurement_rules,
        )

        # Step 4: Audit + ERP writeback
        import os
        orig_dir = os.getcwd()
        os.chdir(CONTROL_PLANE)
        decision_file = write_decision_file(result)
        erp_payload   = build_erp_writeback(request, result, procurement_rules)
        erp_file      = write_erp_file(request["request_id"], erp_payload) if erp_payload else None
        os.chdir(orig_dir)

        # Step 5: Print full loop output
        print(DIVIDER)
        print(f"  RAMP TXN     {txn['id']}  |  {txn['merchant_name']}")
        print(f"  Amount       ${txn['amount']/100:,.2f}  |  {txn.get('sk_category_name','')}")
        print(f"  State        {txn['state']}")
        print()
        print(f"  RAMP SIGNAL  {ramp_check['policy_gate_result']}")
        print(f"  GATE RESULT  {result['decision']}")
        print(f"  Reason       {result['reason']}")

        if result.get("required_approvers"):
            print(f"  Approvers    {', '.join(result['required_approvers'])}")

        print()
        print(f"  Audit file   {decision_file}")
        if erp_file:
            print(f"  ERP file     {erp_file}")
        else:
            print(f"  ERP file     ✗ not generated ({result['decision']} — no writeback)")
        print()

    print("=" * 62)
    print("  Full loop complete. Ramp → Policy Gate → ERP.")
    print("=" * 62)
    print()


if __name__ == "__main__":
    run()
