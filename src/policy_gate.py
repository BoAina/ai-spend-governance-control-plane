"""
Policy Gate
===========
Deterministic rules engine for procurement and spend authorization.

AI reasoning happens upstream (ai_reasoner.py, added in next pass).
This module contains no probabilistic logic.

The gate evaluates:
1. Category approval
2. Restricted vendor check
3. Vendor approval for category
4. Single transaction limit
5. Budget availability
6. Funding-source-specific rules (grants, etc.)
7. Threshold-based escalation

Returns one of: APPROVE / DENY / ESCALATE
"""

from __future__ import annotations
from typing import Any


def evaluate_policy_gate(
    request: dict[str, Any],
    grant_rules: dict[str, Any],
    procurement_rules: dict[str, Any],
) -> dict[str, Any]:
    """
    Core deterministic policy gate.
    AI reasons upstream. This function decides.
    """

    global_rules = procurement_rules["global_rules"]
    funding_source = request["funding_source"]
    category = request["merchant_category"]
    vendor = request["vendor"]
    amount = float(request["amount"])
    available_budget = float(request["available_budget"])

    applied_rules: list[str] = []
    required_approvers: list[str] = []
    audit_steps: list[str] = []

    # 1. Category approved?
    if category not in global_rules["approved_categories"]:
        return _result(
            decision="DENY",
            reason=f"Category '{category}' is not in approved procurement categories.",
            applied_rules=["CATEGORY_NOT_APPROVED"],
            required_approvers=[],
            request=request,
            audit_steps=["Denied: category is not approved."]
        )
    audit_steps.append(f"Category '{category}' is approved.")

    # 2. Restricted vendor?
    if vendor in global_rules["restricted_vendors"]:
        return _result(
            decision="DENY",
            reason=f"Vendor '{vendor}' is on the restricted vendor list.",
            applied_rules=["RESTRICTED_VENDOR"],
            required_approvers=[],
            request=request,
            audit_steps=["Denied: vendor is restricted."]
        )
    audit_steps.append(f"Vendor '{vendor}' is not restricted.")

    # 3. Vendor approved for this category?
    approved_vendors = procurement_rules["approved_vendors_by_category"].get(category, [])
    if vendor not in approved_vendors:
        return _result(
            decision="ESCALATE",
            reason=f"Vendor '{vendor}' is not in the approved vendor list for category '{category}'. Procurement review required.",
            applied_rules=["UNAPPROVED_VENDOR_FOR_CATEGORY"],
            required_approvers=["procurement_admin"],
            request=request,
            audit_steps=audit_steps + [f"Vendor '{vendor}' not approved for category '{category}'."]
        )
    audit_steps.append(f"Vendor '{vendor}' is approved for category '{category}'.")

    # 4. Single transaction limit
    if amount > float(global_rules["single_transaction_limit"]):
        return _result(
            decision="DENY",
            reason=(
                f"Amount ${amount:,.2f} exceeds single transaction limit "
                f"of ${global_rules['single_transaction_limit']:,.2f}."
            ),
            applied_rules=["SINGLE_TRANSACTION_LIMIT"],
            required_approvers=[],
            request=request,
            audit_steps=audit_steps + ["Denied: amount exceeds single transaction limit."]
        )
    audit_steps.append("Amount is within single transaction limit.")

    # 5. Budget availability
    if amount > available_budget:
        return _result(
            decision="DENY",
            reason=(
                f"Insufficient budget. Requested ${amount:,.2f}, "
                f"available ${available_budget:,.2f}."
            ),
            applied_rules=["INSUFFICIENT_BUDGET"],
            required_approvers=[],
            request=request,
            audit_steps=audit_steps + ["Denied: available budget is insufficient."]
        )
    audit_steps.append("Available budget is sufficient.")

    # 6. Funding-source-specific rules
    funding_rules = grant_rules["funding_source_rules"].get(funding_source, {})
    deny_categories = funding_rules.get("deny_categories", [])
    review_categories = funding_rules.get("review_categories", [])
    approver_map = funding_rules.get("required_approvers_by_category", {})

    if category in deny_categories:
        return _result(
            decision="DENY",
            reason=f"Category '{category}' is not allowable under funding source '{funding_source}'.",
            applied_rules=["FUNDING_SOURCE_DENY_CATEGORY"],
            required_approvers=[],
            request=request,
            audit_steps=audit_steps + [
                f"Denied: '{category}' is prohibited under '{funding_source}'."
            ]
        )

    if category in review_categories:
        applied_rules.append("FUNDING_SOURCE_REVIEW_REQUIRED")
        required_approvers.extend(approver_map.get(category, []))
        audit_steps.append(
            f"Funding source '{funding_source}' requires review for category '{category}'."
        )

    # 7. Threshold-based escalation
    if amount > float(global_rules["director_approval_threshold"]):
        applied_rules.append("DIRECTOR_APPROVAL_THRESHOLD")
        required_approvers.append("department_director")
        audit_steps.append("Amount exceeds director approval threshold.")
    elif amount > float(global_rules["manager_approval_threshold"]):
        applied_rules.append("MANAGER_APPROVAL_THRESHOLD")
        required_approvers.append("manager")
        audit_steps.append("Amount exceeds manager approval threshold.")

    if required_approvers:
        return _result(
            decision="ESCALATE",
            reason="Request requires additional approval before authorization.",
            applied_rules=sorted(set(applied_rules)),
            required_approvers=sorted(set(required_approvers)),
            request=request,
            audit_steps=audit_steps
        )

    # 8. All checks passed — approve
    audit_steps.append("All deterministic policy checks passed.")
    return _result(
        decision="APPROVE",
        reason="All policy conditions satisfied.",
        applied_rules=["ALL_POLICY_CHECKS_PASSED"],
        required_approvers=[],
        request=request,
        audit_steps=audit_steps
    )


def _result(
    decision: str,
    reason: str,
    applied_rules: list[str],
    required_approvers: list[str],
    request: dict[str, Any],
    audit_steps: list[str],
) -> dict[str, Any]:
    return {
        "request_id": request["request_id"],
        "decision": decision,
        "reason": reason,
        "policy_rules_applied": applied_rules,
        "required_approvers": required_approvers,
        "erp_writeback_allowed": decision == "APPROVE",
        "audit_steps": audit_steps,
        "request_summary": {
            "vendor": request["vendor"],
            "amount": request["amount"],
            "funding_source": request["funding_source"],
            "merchant_category": request["merchant_category"],
            "budget_code": request["budget_code"],
        },
    }
