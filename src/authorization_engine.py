"""
Authorization Engine
====================
Builds the mock ERP writeback payload when a request is approved.

Only generates a writeback record when erp_writeback_allowed is True.
This separates the authorization decision from the ledger commitment —
a key architectural principle of the control plane.
"""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Any


def build_erp_writeback(
    request: dict[str, Any],
    decision_result: dict[str, Any],
    procurement_rules: dict[str, Any],
) -> dict[str, Any] | None:
    """
    Mock ERP writeback payload.
    Only generated when the policy gate returns APPROVE.

    In production this would post to an ERP API (Oracle Financials,
    Workday, SAP, Tyler Incode, etc.) to create the ledger entry.
    """
    if not decision_result["erp_writeback_allowed"]:
        return None

    gl_map = procurement_rules["category_to_gl_account"]

    return {
        "request_id": request["request_id"],
        "erp_system": "MockERP",
        "ledger_status": "READY_FOR_POSTING",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "ledger_entry": {
            "department": request["department"],
            "budget_code": request["budget_code"],
            "vendor": request["vendor"],
            "amount": request["amount"],
            "gl_account": gl_map.get(request["merchant_category"], "69999 - Uncategorized"),
            "funding_source": request["funding_source"],
            "description": request["description"],
        },
    }
