"""
Funds-Aware Authorization Engine
=================================
A prototype demonstrating what a real-time spend authorization decision
looks like when it has access to both FinTech card data and ERP budget data.

The core argument: a card limit tells you what a cardholder *can* spend.
ERP budget state tells you what they *should* spend. These are two different
layers. Good authorization needs both.

Author: Bo Aina
"""

from dataclasses import dataclass
from enum import Enum
from datetime import datetime
from typing import Optional
import time


# ============================================================
# DATA MODELS
# ============================================================

@dataclass
class TransactionRequest:
    """Incoming authorization request at point of swipe."""
    transaction_id: str
    cardholder_id: str
    department_id: str
    cost_center: str
    amount: float
    merchant_name: str
    merchant_category_code: str
    timestamp: datetime


@dataclass
class FinTechSignal:
    """
    LAYER 1 - FinTech Card Platform Data.
    What the card platform knows at the moment of swipe.
    This data is real-time by design: sub-100ms availability is standard.
    """
    card_limit: float
    current_balance: float           # amount already spent this period
    available_on_card: float         # card_limit - current_balance
    spend_last_24h: float
    spend_last_7d: float
    merchant_category_code: str
    card_active: bool
    velocity_flag: bool              # unusual spend rate detected


@dataclass
class ERPSignal:
    """
    LAYER 2 - ERP Budget Intelligence.
    What the financial system knows about actual budget state.
    This is where the engineering challenge lives.

    'Available on card' and 'available to spend' are two different numbers.
    The ERP knows about purchase orders, encumbrances, grant restrictions,
    and period-end constraints that the card platform cannot see.
    """
    budget_total: float              # full approved budget for period
    actuals_to_date: float           # confirmed spend already recorded
    open_encumbrances: float         # committed POs not yet invoiced
    available_to_spend: float        # budget_total - actuals - encumbrances
    grant_restricted: bool           # spend tied to grant with restrictions
    grant_restriction_note: str      # human-readable restriction detail
    period_end_approaching: bool     # within N days of fiscal period close
    period_end_note: str
    data_freshness_seconds: int      # age of this data snapshot (key metric)


class AuthorizationDecision(Enum):
    APPROVE = "APPROVE"
    APPROVE_WITH_FLAG = "APPROVE_WITH_FLAG"
    DECLINE = "DECLINE"


@dataclass
class AuthorizationResult:
    decision: AuthorizationDecision
    reasons: list
    card_available: float
    erp_available: float
    effective_available: float       # the binding constraint
    binding_layer: str               # which layer drove the decision
    latency_ms: float                # total decision time
    erp_data_age_seconds: int        # how fresh was the ERP signal


# ============================================================
# SIMULATED DATA SOURCES
# In production these would be live API calls.
# ============================================================

def fetch_fintech_signal(transaction: TransactionRequest) -> FinTechSignal:
    """
    Simulates a call to the card platform API.
    In production: real-time, typically < 50ms.
    """
    return FinTechSignal(
        card_limit=10000.00,
        current_balance=6200.00,
        available_on_card=3800.00,
        spend_last_24h=1400.00,
        spend_last_7d=4800.00,
        merchant_category_code=transaction.merchant_category_code,
        card_active=True,
        velocity_flag=False
    )


def fetch_erp_signal(transaction: TransactionRequest) -> ERPSignal:
    """
    Simulates a call to the ERP budget API.
    In production: this is where latency, freshness, and availability
    become real engineering problems. See the reality check below.

    This example shows a department that looks fine on the card
    but is nearly exhausted at the ERP level once encumbrances are counted.
    """
    return ERPSignal(
        budget_total=15000.00,
        actuals_to_date=9800.00,
        open_encumbrances=4500.00,       # POs approved, not yet invoiced
        available_to_spend=700.00,        # 15000 - 9800 - 4500
        grant_restricted=True,
        grant_restriction_note="Federal grant 2024-DOE-447: no travel spend after Q3 close.",
        period_end_approaching=True,
        period_end_note="Fiscal period closes in 4 days. Uncommitted budget may not carry over.",
        data_freshness_seconds=180        # ERP snapshot is 3 minutes old
    )


# ============================================================
# DECISION ENGINE
# Combines both layers to produce an authorization decision.
# ============================================================

def evaluate_authorization(
    transaction: TransactionRequest,
    fintech: FinTechSignal,
    erp: ERPSignal
) -> AuthorizationResult:
    """
    Core authorization logic.
    The key insight: the effective available amount is the minimum
    of what the card allows and what the ERP says is actually available.
    A transaction can be within card limits and still be wrong.
    """
    reasons = []
    decision = AuthorizationDecision.APPROVE
    binding_layer = "none"

    card_available = fintech.available_on_card
    erp_available = erp.available_to_spend
    effective_available = min(card_available, erp_available)

    # --- Check 1: Card active ---
    if not fintech.card_active:
        reasons.append("Card is inactive.")
        return AuthorizationResult(
            decision=AuthorizationDecision.DECLINE,
            reasons=reasons,
            card_available=card_available,
            erp_available=erp_available,
            effective_available=0,
            binding_layer="fintech",
            latency_ms=0,
            erp_data_age_seconds=erp.data_freshness_seconds
        )

    # --- Check 2: Card limit ---
    if transaction.amount > card_available:
        decision = AuthorizationDecision.DECLINE
        binding_layer = "fintech"
        reasons.append(
            f"Exceeds card available balance. "
            f"Requested: ${transaction.amount:,.2f} | Card available: ${card_available:,.2f}"
        )

    # --- Check 3: ERP budget availability ---
    if transaction.amount > erp_available:
        decision = AuthorizationDecision.DECLINE
        binding_layer = "erp"
        reasons.append(
            f"Insufficient budget at ERP level. "
            f"Requested: ${transaction.amount:,.2f} | "
            f"ERP available (after encumbrances): ${erp_available:,.2f} | "
            f"Open POs already committed: ${erp.open_encumbrances:,.2f}"
        )

    # --- Check 4: Grant restriction ---
    if erp.grant_restricted:
        decision = AuthorizationDecision.DECLINE
        binding_layer = "erp"
        reasons.append(f"Grant restriction: {erp.grant_restriction_note}")

    # --- Check 5: Period-end flag (approve but flag) ---
    if erp.period_end_approaching and decision == AuthorizationDecision.APPROVE:
        decision = AuthorizationDecision.APPROVE_WITH_FLAG
        binding_layer = "erp"
        reasons.append(f"Period-end advisory: {erp.period_end_note}")

    # --- Check 6: Velocity flag (approve but flag) ---
    if fintech.velocity_flag and decision == AuthorizationDecision.APPROVE:
        decision = AuthorizationDecision.APPROVE_WITH_FLAG
        binding_layer = "fintech"
        reasons.append("Unusual spend velocity detected. Flagged for review.")

    if not reasons:
        reasons.append("All checks passed.")

    return AuthorizationResult(
        decision=decision,
        reasons=reasons,
        card_available=card_available,
        erp_available=erp_available,
        effective_available=effective_available,
        binding_layer=binding_layer,
        latency_ms=0,                        # filled in by run_authorization
        erp_data_age_seconds=erp.data_freshness_seconds
    )


# ============================================================
# RUNNER
# Orchestrates the full authorization flow and measures latency.
# ============================================================

def run_authorization(transaction: TransactionRequest) -> AuthorizationResult:
    start = time.time()

    fintech = fetch_fintech_signal(transaction)
    erp = fetch_erp_signal(transaction)
    result = evaluate_authorization(transaction, fintech, erp)

    result.latency_ms = round((time.time() - start) * 1000, 2)
    return result


def print_result(transaction: TransactionRequest, result: AuthorizationResult):
    print("\n" + "=" * 60)
    print(f"AUTHORIZATION REQUEST: {transaction.transaction_id}")
    print(f"Merchant: {transaction.merchant_name}")
    print(f"Amount:   ${transaction.amount:,.2f}")
    print(f"Dept:     {transaction.department_id} / {transaction.cost_center}")
    print("-" * 60)
    print(f"Card available:       ${result.card_available:,.2f}")
    print(f"ERP available:        ${result.erp_available:,.2f}  (after encumbrances)")
    print(f"Effective available:  ${result.effective_available:,.2f}  (binding constraint)")
    print(f"Binding layer:        {result.binding_layer.upper()}")
    print("-" * 60)
    print(f"DECISION: {result.decision.value}")
    for r in result.reasons:
        print(f"  - {r}")
    print("-" * 60)
    print(f"Total decision latency:  {result.latency_ms} ms")
    print(f"ERP data age:            {result.erp_data_age_seconds}s")
    print("=" * 60)


# ============================================================
# EXAMPLE SCENARIOS
# ============================================================

if __name__ == "__main__":

    # Scenario A: Transaction that looks fine on the card,
    # but the ERP layer catches it.
    txn_a = TransactionRequest(
        transaction_id="TXN-001",
        cardholder_id="EMP-4421",
        department_id="DEPT-ENGINEERING",
        cost_center="CC-4400",
        amount=850.00,
        merchant_name="Cloud Infrastructure Vendor",
        merchant_category_code="7372",
        timestamp=datetime.now()
    )

    result_a = run_authorization(txn_a)
    print_result(txn_a, result_a)

    # Scenario B: Small transaction, still caught by grant restriction.
    txn_b = TransactionRequest(
        transaction_id="TXN-002",
        cardholder_id="EMP-4421",
        department_id="DEPT-ENGINEERING",
        cost_center="CC-4400",
        amount=120.00,
        merchant_name="Airport Lounge Services",
        merchant_category_code="7011",
        timestamp=datetime.now()
    )

    result_b = run_authorization(txn_b)
    print_result(txn_b, result_b)


# ============================================================
# ENGINEERING REALITY CHECK
# ============================================================
#
# The decision engine above is straightforward. The hard problem
# is not the logic - it is getting reliable ERP data in time.
#
# LATENCY
#   ERP systems are not built for sub-100ms API responses.
#   A live budget query against Oracle Financials or SAP
#   can take 200-800ms depending on load and configuration.
#   Card authorization networks expect a decision in < 150ms.
#   That gap is real and cannot be ignored.
#
# DATA FRESHNESS
#   ERP budget data is often updated in batch cycles:
#   nightly, hourly, or triggered by specific events (PO approval,
#   journal entry, period close). A 3-minute-old ERP snapshot
#   may not reflect a purchase order approved 2 minutes ago.
#   The authorization engine above flags this (data_freshness_seconds).
#   In production, acceptable staleness depends on transaction size
#   and risk tolerance - and that is a policy decision, not a
#   technical one.
#
# THE CACHING STRATEGY (most viable path)
#   Rather than querying ERP live at authorization time,
#   maintain a warm cache of budget state per cost center.
#   Invalidate or refresh the cache on known ERP events:
#     - PO creation or approval
#     - Journal entry posting
#     - Period open / period close
#     - Budget amendment
#   This moves the latency problem out of the authorization path
#   and into the event pipeline - where it is manageable.
#
# WHAT THIS MEANS IN PRACTICE
#   The architecture is sound.
#   The engineering challenge is making ERP data event-driven
#   rather than batch-driven.
#   That is an integration problem, not an authorization problem.
#   And it is a solvable one - but it requires ERP vendors,
#   card platforms, and finance teams to agree on what
#   "close enough to real-time" actually means.
#
# ============================================================
