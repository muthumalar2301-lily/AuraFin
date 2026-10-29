# backend/main.py

import os
from datetime import date
from typing import List

import requests
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from database import engine, Base, get_db
from models import Transaction, Invoice
import schemas
from engine import compute_product_price, project_cash_flow
from paypal_service import create_and_send_invoice, get_access_token
from ai_service import generate_financial_advice


# ---------------------------------------------------------
# Database Initialization
# ---------------------------------------------------------

Base.metadata.create_all(bind=engine)


# ---------------------------------------------------------
# FastAPI Application
# ---------------------------------------------------------

app = FastAPI(
    title="AuraFin Core API",
    version="1.0.0",
)


# ---------------------------------------------------------
# CORS Configuration
# ---------------------------------------------------------

# Preserve local React development compatibility.
# Configure explicit frontend origins before production deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------
# PayPal Configuration
# ---------------------------------------------------------

PAYPAL_BASE_URL = "https://api-m.sandbox.paypal.com"
PAYPAL_TIMEOUT = 20


# ---------------------------------------------------------
# 1. Health & Status
# ---------------------------------------------------------

@app.get("/api/health")
def health_check():
    return {
        "status": "online",
        "system": "AuraFin Backend",
    }


# ---------------------------------------------------------
# 2. Financial Dashboard Summary & Cash Flow
# ---------------------------------------------------------

@app.get("/api/dashboard/summary")
def get_dashboard_summary(db: Session = Depends(get_db)):
    txs = db.query(Transaction).all()
    invoices = db.query(Invoice).all()

    income = sum(
        t.amount
        for t in txs
        if t.type == "INCOME" and t.status == "CONFIRMED"
    )

    expenses = sum(
        t.amount
        for t in txs
        if t.type == "EXPENSE" and t.status == "CONFIRMED"
    )

    cash_balance = float(income - expenses)

    pending_invoices_total = sum(
        inv.amount
        for inv in invoices
        if inv.status in ["SENT", "DRAFT"]
    )

    # Preserve the existing cash-flow input structure.
    tx_dicts = [
        {
            "amount": float(t.amount),
            "type": t.type,
            "due_date": t.due_date,
        }
        for t in txs
    ]

    inv_dicts = [
        {
            "amount": float(inv.amount),
            "status": inv.status,
            "due_date": inv.due_date,
        }
        for inv in invoices
    ]

    cash_flow_normal = project_cash_flow(
        cash_balance,
        30,
        tx_dicts,
        inv_dicts,
        delay_invoices_by_days=0,
    )

    cash_flow_delayed = project_cash_flow(
        cash_balance,
        30,
        tx_dicts,
        inv_dicts,
        delay_invoices_by_days=14,
    )

    # Keep the existing response keys for frontend compatibility.
    return {
        "current_cash_balance": cash_balance,
        "total_income": float(income),
        "total_expenses": float(expenses),
        "pending_invoices_total": float(pending_invoices_total),
        "forecast_normal": cash_flow_normal,
        "forecast_delayed": cash_flow_delayed,
    }


# ---------------------------------------------------------
# 3. Deterministic Pricing Advisor
# ---------------------------------------------------------

@app.post("/api/pricing/calculate")
def calculate_price(payload: schemas.PricingRequest):
    return compute_product_price(
        materials=payload.materials,
        hours=payload.hours,
        rate=payload.rate,
        packaging=payload.packaging,
        shipping=payload.shipping,
        overhead=payload.overhead,
        target_margin_pct=payload.target_margin,
    )


# ---------------------------------------------------------
# 4. PayPal Invoice Generation & Dispatch
# ---------------------------------------------------------

@app.post("/api/invoices/send")
def send_invoice(
    payload: schemas.InvoiceCreateRequest,
    db: Session = Depends(get_db),
):
    try:
        paypal_id = create_and_send_invoice(
            recipient_email=payload.recipient_email,
            item_name=payload.item_name,
            unit_amount=payload.amount,
            due_date=str(payload.due_date),
        )

        new_inv = Invoice(
            paypal_invoice_id=paypal_id,
            recipient_email=payload.recipient_email,
            item_name=payload.item_name,
            amount=payload.amount,
            status="SENT",
            due_date=payload.due_date,
        )

        db.add(new_inv)
        db.commit()
        db.refresh(new_inv)

        return {
            "status": "SUCCESS",
            "invoice_id": paypal_id,
        }

    except Exception:
        db.rollback()

        # Do not expose credentials, provider responses, or internal
        # exception details to API clients.
        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to complete invoice processing. "
                "Check the backend logs and PayPal invoice status "
                "before attempting another request."
            ),
        )


# ---------------------------------------------------------
# 5. PayPal Webhook Verification
# ---------------------------------------------------------

def verify_paypal_webhook(
    request: Request,
    payload: dict,
) -> bool:
    """
    Verify a PayPal webhook using PayPal's verification API.

    PAYPAL_WEBHOOK_ID must be the actual webhook ID registered
    in the PayPal Sandbox Developer Dashboard.
    """

    webhook_id = os.getenv("PAYPAL_WEBHOOK_ID")

    if not webhook_id:
        raise HTTPException(
            status_code=503,
            detail="PayPal webhook verification is not configured.",
        )

    required_headers = {
        "auth_algo": "paypal-auth-algo",
        "cert_url": "paypal-cert-url",
        "transmission_id": "paypal-transmission-id",
        "transmission_sig": "paypal-transmission-sig",
        "transmission_time": "paypal-transmission-time",
    }

    verification_data = {}

    for field, header_name in required_headers.items():
        header_value = request.headers.get(header_name)

        if not header_value:
            raise HTTPException(
                status_code=400,
                detail="Missing required PayPal webhook headers.",
            )

        verification_data[field] = header_value

    verification_data["webhook_id"] = webhook_id
    verification_data["webhook_event"] = payload

    try:
        access_token = get_access_token()

        response = requests.post(
            (
                f"{PAYPAL_BASE_URL}"
                "/v1/notifications/verify-webhook-signature"
            ),
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            json=verification_data,
            timeout=PAYPAL_TIMEOUT,
        )

        response.raise_for_status()

        result = response.json()

    except (requests.RequestException, RuntimeError, ValueError):
        raise HTTPException(
            status_code=503,
            detail="Unable to verify the PayPal webhook.",
        )

    return result.get("verification_status") == "SUCCESS"


@app.post("/api/webhooks/paypal")
async def handle_paypal_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    # Step 1: Parse the event.
    try:
        payload = await request.json()
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(
            status_code=400,
            detail="Invalid webhook JSON.",
        )

    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=400,
            detail="Invalid webhook payload.",
        )

    # Step 2: Verify the event before processing any payment.
    if not verify_paypal_webhook(request, payload):
        raise HTTPException(
            status_code=400,
            detail="PayPal webhook signature verification failed.",
        )

    event_type = payload.get("event_type")

    # Acknowledge other legitimate PayPal events without treating
    # them as completed payments.
    if event_type != "INVOICING.INVOICE.PAID":
        return {
            "status": "acknowledged",
            "processed": False,
        }

    # Step 3: Validate the verified event's invoice ID.
    resource = payload.get("resource") or {}

    if not isinstance(resource, dict):
        raise HTTPException(
            status_code=400,
            detail="Invalid PayPal event resource.",
        )

    paypal_id = resource.get("id")

    if not paypal_id:
        raise HTTPException(
            status_code=400,
            detail="PayPal payment event has no invoice ID.",
        )

    # Step 4: Find the invoice created by AuraFin.
    try:
        inv = (
            db.query(Invoice)
            .filter(Invoice.paypal_invoice_id == paypal_id)
            .with_for_update()
            .first()
        )

        if inv is None:
            # Never manufacture income for an unknown invoice.
            # This also removes the previous simulator-income fallback.
            return {
                "status": "acknowledged",
                "processed": False,
                "reason": "Invoice not found in AuraFin.",
            }

        # Step 5: Avoid processing an invoice already marked as paid.
        if inv.status == "PAID":
            return {
                "status": "acknowledged",
                "processed": False,
                "reason": "Invoice was already processed.",
            }

        # Only process invoices in the expected state.
        if inv.status != "SENT":
            return {
                "status": "acknowledged",
                "processed": False,
                "reason": "Invoice is not in a payable state.",
            }

        # Step 6: Record payment and invoice status in one transaction.
        inv.status = "PAID"

        payment_transaction = Transaction(
            description=f"PayPal Invoice Paid: {inv.item_name}",
            amount=inv.amount,
            type="INCOME",
            category="Client Commission",
            status="CONFIRMED",
            due_date=date.today(),
        )

        db.add(payment_transaction)
        db.commit()

        return {
            "status": "acknowledged",
            "processed": True,
        }

    except Exception:
        db.rollback()

        # Raising an error allows PayPal to retry the webhook.
        # The invoice status guard helps prevent ordinary duplicates.
        raise HTTPException(
            status_code=500,
            detail="Unable to process the PayPal payment event.",
        )


# ---------------------------------------------------------
# 6. Ollama Local Financial Assistant
# ---------------------------------------------------------

@app.post("/api/assistant/chat")
def chat_copilot(
    payload: schemas.ChatQueryRequest,
    db: Session = Depends(get_db),
):
    try:
        advice = generate_financial_advice(payload.query, db)

        return {
            "reply": advice,
        }

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Unable to generate financial advice right now.",
        )
