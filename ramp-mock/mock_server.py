#!/usr/bin/env python3
"""
Ramp API Mock Server
Mirrors the real Ramp REST API schema with realistic fake data.
Swap BASE_URL to https://api.ramp.com/developer/graphql when sandbox credentials arrive.

Run: uvicorn mock_server:app --reload --port 8100
Docs: http://localhost:8100/docs
"""

from fastapi import FastAPI, Query, HTTPException, Header
from fastapi.responses import JSONResponse
from typing import Optional
import uuid
from datetime import datetime, timedelta
import random

app = FastAPI(
    title="Ramp API Mock",
    description="Local mock of the Ramp Developer API — schema-identical to production.",
    version="1.0.0",
)

# ── Auth middleware (mirrors Ramp bearer token pattern) ───────────────────────
MOCK_TOKEN = "mock_ramp_token_ainalabs_2026"

def check_auth(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    return authorization.split(" ")[1]


# ── Seed data ─────────────────────────────────────────────────────────────────
DEPARTMENTS = [
    {"id": "dept_001", "name": "Engineering"},
    {"id": "dept_002", "name": "Sales"},
    {"id": "dept_003", "name": "Marketing"},
    {"id": "dept_004", "name": "Finance"},
    {"id": "dept_005", "name": "Operations"},
]

USERS = [
    {"id": "usr_001", "first_name": "Sarah", "last_name": "Chen", "email": "sarah.chen@acme.com", "department_id": "dept_002", "role": "BUSINESS_USER"},
    {"id": "usr_002", "first_name": "Marcus", "last_name": "Webb", "email": "marcus.webb@acme.com", "department_id": "dept_001", "role": "BUSINESS_USER"},
    {"id": "usr_003", "first_name": "Priya", "last_name": "Nair", "email": "priya.nair@acme.com", "department_id": "dept_003", "role": "BUSINESS_USER"},
    {"id": "usr_004", "first_name": "James", "last_name": "Torres", "email": "james.torres@acme.com", "department_id": "dept_004", "role": "ADMIN"},
    {"id": "usr_005", "first_name": "Dana", "last_name": "Okafor", "email": "dana.okafor@acme.com", "department_id": "dept_005", "role": "BUSINESS_USER"},
]

CARDS = [
    {"id": "card_001", "display_name": "Sarah Chen - Travel", "cardholder_id": "usr_001", "spend_limit": {"amount": 500000, "interval": "MONTHLY"}, "state": "ACTIVE"},
    {"id": "card_002", "display_name": "Marcus Webb - SaaS Tools", "cardholder_id": "usr_002", "spend_limit": {"amount": 200000, "interval": "MONTHLY"}, "state": "ACTIVE"},
    {"id": "card_003", "display_name": "Priya Nair - Advertising", "cardholder_id": "usr_003", "spend_limit": {"amount": 1000000, "interval": "MONTHLY"}, "state": "ACTIVE"},
    {"id": "card_004", "display_name": "Dana Okafor - Office Supplies", "cardholder_id": "usr_005", "spend_limit": {"amount": 100000, "interval": "MONTHLY"}, "state": "ACTIVE"},
]

# ── Transactions: designed to hit all 3 Policy Gate outcomes ──────────────────
# Amounts in cents (Ramp standard)
TRANSACTIONS = [
    # ✅ APPROVE scenarios
    {
        "id": "txn_001",
        "user_transaction_time": "2026-03-14T09:23:11Z",
        "merchant_name": "Delta Airlines",
        "merchant_category_code": "3020",
        "merchant_category_code_description": "Airlines",
        "amount": 62500,           # $625 — within travel card limit
        "currency_code": "USD",
        "state": "CLEARED",
        "card_id": "card_001",
        "user_id": "usr_001",
        "department_id": "dept_002",
        "sk_category_name": "Travel",
        "accounting_field_selections": [
            {"category_id": "gl_6200", "category_name": "Travel & Entertainment", "external_id": "6200"},
        ],
        "policy_violations": [],
        "_mock_policy_signal": "APPROVE",
        "_mock_note": "Within limit, pre-approved vendor, correct GL category",
    },
    {
        "id": "txn_002",
        "user_transaction_time": "2026-03-13T14:05:33Z",
        "merchant_name": "GitHub",
        "merchant_category_code": "7372",
        "merchant_category_code_description": "Computer Programming, Data Processing",
        "amount": 4000,            # $40 — routine SaaS
        "currency_code": "USD",
        "state": "CLEARED",
        "card_id": "card_002",
        "user_id": "usr_002",
        "department_id": "dept_001",
        "sk_category_name": "Software",
        "accounting_field_selections": [
            {"category_id": "gl_6300", "category_name": "Software & Subscriptions", "external_id": "6300"},
        ],
        "policy_violations": [],
        "_mock_policy_signal": "APPROVE",
        "_mock_note": "Recurring approved vendor, within limit, correct GL",
    },
    # ✅✅ BOTH GATES PASS — clean transactions that clear Ramp + Control Plane
    {
        "id": "txn_007",
        "user_transaction_time": "2026-03-15T18:44:10Z",
        "merchant_name": "Marriott Hotels",
        "merchant_category_code": "3509",
        "merchant_category_code_description": "Hotels and Motels",
        "amount": 38000,           # $380 — lodging, within travel card limit
        "currency_code": "USD",
        "state": "CLEARED",
        "card_id": "card_001",
        "user_id": "usr_001",
        "department_id": "dept_002",
        "sk_category_name": "Travel",
        "accounting_field_selections": [
            {"category_id": "gl_6200", "category_name": "Travel & Entertainment", "external_id": "6200"},
        ],
        "policy_violations": [],
        "_mock_policy_signal": "APPROVE",
        "_mock_note": "Approved lodging vendor, within limit, correct GL, Workday work tag ready",
    },
    {
        "id": "txn_008",
        "user_transaction_time": "2026-03-15T10:12:55Z",
        "merchant_name": "Amazon Business",
        "merchant_category_code": "5111",
        "merchant_category_code_description": "Stationery Stores, Office Supplies",
        "amount": 9500,            # $95 — routine office supplies
        "currency_code": "USD",
        "state": "CLEARED",
        "card_id": "card_004",
        "user_id": "usr_005",
        "department_id": "dept_005",
        "sk_category_name": "Office Supplies",
        "accounting_field_selections": [
            {"category_id": "gl_6100", "category_name": "Office Supplies & Equipment", "external_id": "6100"},
        ],
        "policy_violations": [],
        "_mock_policy_signal": "APPROVE",
        "_mock_note": "Approved vendor, low amount, correct GL, all 7 checks passed",
    },
    # 🔴 DENY scenarios
    {
        "id": "txn_003",
        "user_transaction_time": "2026-03-12T21:47:02Z",
        "merchant_name": "Nobu Restaurant",
        "merchant_category_code": "5812",
        "merchant_category_code_description": "Eating Places, Restaurants",
        "amount": 84000,           # $840 — single meal over $500 policy limit
        "currency_code": "USD",
        "state": "DECLINED",
        "card_id": "card_001",
        "user_id": "usr_001",
        "department_id": "dept_002",
        "sk_category_name": "Meals & Entertainment",
        "accounting_field_selections": [],
        "policy_violations": [
            {"policy_rule": "MEAL_LIMIT_PER_PERSON", "message": "Transaction exceeds $500 per-meal policy limit"}
        ],
        "_mock_policy_signal": "DENY",
        "_mock_note": "Meal limit exceeded. Policy rule triggered pre-authorization.",
    },
    {
        "id": "txn_004",
        "user_transaction_time": "2026-03-11T16:30:55Z",
        "merchant_name": "Best Buy",
        "merchant_category_code": "5732",
        "merchant_category_code_description": "Electronics Stores",
        "amount": 249900,          # $2,499 — electronics without approval
        "currency_code": "USD",
        "state": "DECLINED",
        "card_id": "card_002",
        "user_id": "usr_002",
        "department_id": "dept_001",
        "sk_category_name": "Hardware",
        "accounting_field_selections": [],
        "policy_violations": [
            {"policy_rule": "HARDWARE_REQUIRES_APPROVAL", "message": "Hardware purchases over $500 require manager approval"},
            {"policy_rule": "CARD_CATEGORY_RESTRICTION", "message": "Card not authorized for Electronics category"},
        ],
        "_mock_policy_signal": "DENY",
        "_mock_note": "Category mismatch + approval gate. Two policy rules triggered.",
    },
    # ⚠️ ESCALATE scenarios
    {
        "id": "txn_005",
        "user_transaction_time": "2026-03-10T11:15:20Z",
        "merchant_name": "Salesforce",
        "merchant_category_code": "7372",
        "merchant_category_code_description": "Computer Programming, Data Processing",
        "amount": 4800000,         # $48,000 — annual enterprise contract
        "currency_code": "USD",
        "state": "PENDING",
        "card_id": "card_002",
        "user_id": "usr_002",
        "department_id": "dept_001",
        "sk_category_name": "Software",
        "accounting_field_selections": [
            {"category_id": "gl_6300", "category_name": "Software & Subscriptions", "external_id": "6300"},
        ],
        "policy_violations": [
            {"policy_rule": "LARGE_PURCHASE_REVIEW", "message": "Transactions over $10,000 require CFO review"}
        ],
        "_mock_policy_signal": "ESCALATE",
        "_mock_note": "Legitimate vendor, correct category, but amount triggers CFO review threshold.",
    },
    {
        "id": "txn_006",
        "user_transaction_time": "2026-03-09T08:52:44Z",
        "merchant_name": "Unknown Vendor LLC",
        "merchant_category_code": "5999",
        "merchant_category_code_description": "Miscellaneous Retail",
        "amount": 75000,           # $750 — unknown vendor, unclassified
        "currency_code": "USD",
        "state": "PENDING",
        "card_id": "card_004",
        "user_id": "usr_005",
        "department_id": "dept_005",
        "sk_category_name": "Uncategorized",
        "accounting_field_selections": [],
        "policy_violations": [
            {"policy_rule": "UNRECOGNIZED_VENDOR", "message": "Vendor not in approved vendor list — requires review"},
            {"policy_rule": "MISSING_GL_CODE", "message": "No accounting field selection — cannot post to ERP"},
        ],
        "_mock_policy_signal": "ESCALATE",
        "_mock_note": "New vendor + missing GL. Cannot auto-post. Human review required.",
    },
]


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {
        "service": "Ramp API Mock",
        "version": "v1",
        "status": "running",
        "note": "Schema-identical mock of the Ramp Developer API. Swap base URL for sandbox/production."
    }

@app.get("/developer/graphql/v1/transactions")
def list_transactions(
    authorization: Optional[str] = Header(None),
    start: Optional[str] = Query(None, description="ISO8601 start date"),
    end: Optional[str] = Query(None, description="ISO8601 end date"),
    department_id: Optional[str] = Query(None),
    card_id: Optional[str] = Query(None),
    state: Optional[str] = Query(None, description="CLEARED | DECLINED | PENDING"),
    page_size: int = Query(10, le=100),
):
    check_auth(authorization)
    txns = TRANSACTIONS.copy()
    if department_id:
        txns = [t for t in txns if t.get("department_id") == department_id]
    if card_id:
        txns = [t for t in txns if t.get("card_id") == card_id]
    if state:
        txns = [t for t in txns if t.get("state") == state.upper()]
    return {
        "data": txns[:page_size],
        "page": {"next": None, "total_count": len(txns)},
    }

@app.get("/developer/graphql/v1/transactions/{transaction_id}")
def get_transaction(transaction_id: str, authorization: Optional[str] = Header(None)):
    check_auth(authorization)
    for txn in TRANSACTIONS:
        if txn["id"] == transaction_id:
            return txn
    raise HTTPException(status_code=404, detail=f"Transaction {transaction_id} not found")

@app.get("/developer/graphql/v1/cards")
def list_cards(authorization: Optional[str] = Header(None)):
    check_auth(authorization)
    return {"data": CARDS, "page": {"next": None, "total_count": len(CARDS)}}

@app.get("/developer/graphql/v1/cards/{card_id}")
def get_card(card_id: str, authorization: Optional[str] = Header(None)):
    check_auth(authorization)
    for card in CARDS:
        if card["id"] == card_id:
            return card
    raise HTTPException(status_code=404, detail=f"Card {card_id} not found")

@app.get("/developer/graphql/v1/users")
def list_users(authorization: Optional[str] = Header(None)):
    check_auth(authorization)
    return {"data": USERS, "page": {"next": None, "total_count": len(USERS)}}

@app.get("/developer/graphql/v1/departments")
def list_departments(authorization: Optional[str] = Header(None)):
    check_auth(authorization)
    return {"data": DEPARTMENTS, "page": {"next": None, "total_count": len(DEPARTMENTS)}}

@app.get("/developer/graphql/v1/accounting/sync_records")
def list_accounting_records(
    authorization: Optional[str] = Header(None),
    state: Optional[str] = Query(None, description="SYNCED | PENDING | ERROR"),
):
    check_auth(authorization)
    records = []
    for txn in TRANSACTIONS:
        if txn["state"] == "CLEARED" and txn["accounting_field_selections"]:
            records.append({
                "transaction_id": txn["id"],
                "sync_state": "SYNCED",
                "gl_account": txn["accounting_field_selections"][0]["external_id"],
                "gl_account_name": txn["accounting_field_selections"][0]["category_name"],
                "synced_at": txn["user_transaction_time"],
                "erp_entry_id": f"JE-{txn['id'].upper()}",
            })
        elif not txn["accounting_field_selections"]:
            records.append({
                "transaction_id": txn["id"],
                "sync_state": "ERROR",
                "gl_account": None,
                "gl_account_name": None,
                "synced_at": None,
                "erp_entry_id": None,
                "error": "Missing GL code — cannot post to ERP",
            })
    if state:
        records = [r for r in records if r["sync_state"] == state.upper()]
    return {"data": records, "page": {"next": None, "total_count": len(records)}}


# ── Policy Gate integration endpoint ─────────────────────────────────────────
@app.get("/developer/graphql/v1/transactions/{transaction_id}/policy_check")
def policy_check(transaction_id: str, authorization: Optional[str] = Header(None)):
    """
    Non-standard mock endpoint: runs a transaction through the Policy Gate
    and returns APPROVE / DENY / ESCALATE with full reasoning.
    Demonstrates Ramp's pre-transaction control architecture.
    """
    check_auth(authorization)
    for txn in TRANSACTIONS:
        if txn["id"] == transaction_id:
            signal = txn["_mock_policy_signal"]
            violations = txn.get("policy_violations", [])
            return {
                "transaction_id": transaction_id,
                "merchant": txn["merchant_name"],
                "amount_usd": txn["amount"] / 100,
                "policy_gate_result": signal,
                "checks_passed": 7 - len(violations),
                "checks_failed": len(violations),
                "violations": violations,
                "reasoning": txn["_mock_note"],
                "gl_ready": bool(txn["accounting_field_selections"]),
                "erp_outcome": (
                    f"Post to GL {txn['accounting_field_selections'][0]['external_id']} — {txn['accounting_field_selections'][0]['category_name']}"
                    if txn["accounting_field_selections"]
                    else "BLOCKED — missing GL code"
                ),
            }
    raise HTTPException(status_code=404, detail=f"Transaction {transaction_id} not found")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8100)
