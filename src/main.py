"""
AI Spend Governance Control Plane
==================================
First pass: deterministic prototype.

Flow:
  Spend Request
       |
       v
  Policy Gate (deterministic rules)
       |
       v
  Authorization Decision (APPROVE / DENY / ESCALATE)
       |
       v
  Audit Record + Mock ERP Writeback (APPROVE only)

AI classification layer (ai_reasoner.py) will be wired in next pass.

Run from repo root:
  python -m src.main
"""

from __future__ import annotations
import json
from pathlib import Path

from src.audit_logger import write_decision_file, write_erp_file
from src.authorization_engine import build_erp_writeback
from src.policy_gate import evaluate_policy_gate


REQUEST_DIR = Path("sample_requests")
POLICY_DIR = Path("policies")

DIVIDER = "-" * 60


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def main() -> None:
    grant_rules = load_json(POLICY_DIR / "grant_policy_rules.json")
    procurement_rules = load_json(POLICY_DIR / "procurement_policy_rules.json")

    request_files = sorted(REQUEST_DIR.glob("*.json"))

    if not request_files:
        print("No sample requests found in sample_requests/")
        return

    print()
    print("=" * 60)
    print("  AI Spend Governance Control Plane")
    print("  First Pass: Deterministic Prototype")
    print("=" * 60)
    print()

    for path in request_files:
        request = load_json(path)

        result = evaluate_policy_gate(
            request=request,
            grant_rules=grant_rules,
            procurement_rules=procurement_rules,
        )

        decision_file = write_decision_file(result)
        erp_payload = build_erp_writeback(request, result, procurement_rules)

        print(DIVIDER)
        print(f"Request:     {request['request_id']}")
        print(f"Vendor:      {request['vendor']}")
        print(f"Description: {request['description']}")
        print(f"Amount:      ${request['amount']:,.2f}")
        print(f"Funding:     {request['funding_source']}")
        print(f"Category:    {request['merchant_category']}")
        print()
        print(f"DECISION:    {result['decision']}")
        print(f"Reason:      {result['reason']}")

        if result["required_approvers"]:
            print(f"Approvers:   {', '.join(result['required_approvers'])}")

        print()
        print(f"Audit file:  {decision_file}")

        if erp_payload:
            erp_file = write_erp_file(request["request_id"], erp_payload)
            print(f"ERP file:    {erp_file}")
        else:
            print("ERP file:    not generated (not approved)")

        print()

    print(DIVIDER)
    print("Demo complete.")
    print()


if __name__ == "__main__":
    main()
