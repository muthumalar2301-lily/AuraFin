import os
import requests

from dotenv import load_dotenv
from sqlalchemy.orm import Session
from datetime import date, timedelta
from models import Transaction, Invoice

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")


def generate_financial_advice(user_prompt: str, db: Session) -> str:

    if not GEMINI_API_KEY:
        return "Gemini API key is missing. Please configure GEMINI_API_KEY."

    today = date.today()

    tx_records = db.query(Transaction).all()
    invoices = db.query(Invoice).all()

    confirmed_income = sum(
        float(t.amount)
        for t in tx_records
        if t.type == "INCOME" and t.status == "CONFIRMED"
    )

    confirmed_expenses = sum(
        float(t.amount)
        for t in tx_records
        if t.type == "EXPENSE" and t.status == "CONFIRMED"
    )

    current_cash = confirmed_income - confirmed_expenses

    upcoming_expenses = [
        {
            "item": t.description,
            "amount": float(t.amount),
            "due": str(t.due_date)
        }
        for t in tx_records
        if (
            t.type == "EXPENSE"
            and t.due_date is not None
            and today <= t.due_date <= today + timedelta(days=30)
        )
    ]

    pending_invoices = [
        {
            "to": inv.recipient_email,
            "amount": float(inv.amount),
            "due": str(inv.due_date),
            "status": str(inv.status)
        }
        for inv in invoices
        if inv.status in ["SENT", "DRAFT"]
    ]

    system_instruction = f"""
You are AuraFin AI, an intelligent financial copilot
for independent creators, freelancers, and artists.

CREATOR FINANCIAL SNAPSHOT:

Current Liquid Cash: ${current_cash:.2f}
Confirmed Income: ${confirmed_income:.2f}
Confirmed Expenses: ${confirmed_expenses:.2f}

Pending PayPal Invoices:
{pending_invoices}

Scheduled Expenses (Next 30 Days):
{upcoming_expenses}

STRICT RULES:
1. Base financial conclusions only on supplied data.
2. Never invent transactions, balances, invoices, or dates.
3. Distinguish confirmed income from pending invoice amounts.
4. Never count pending invoices as available cash.
5. Explain financial risks and suggest practical actions.
6. If information is insufficient, explicitly say so.
7. Never claim to execute payments or modify records.
8. Keep answers between 2 and 5 sentences.
9. Use clear language and dollar amounts.
"""

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/"
        f"models/{GEMINI_MODEL}:generateContent"
    )

    headers = {
        "x-goog-api-key": GEMINI_API_KEY,
        "Content-Type": "application/json"
    }

    payload = {
        "system_instruction": {
            "parts": [{"text": system_instruction}]
        },
        "contents": [
            {
                "role": "user",
                "parts": [{"text": user_prompt}]
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 400
        }
    }

    try:
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=45
        )

        response.raise_for_status()

        result = response.json()

        answer = result["candidates"][0]["content"]["parts"][0]["text"]

        return answer.strip()

    except requests.exceptions.Timeout:
        return "Gemini AI took too long to respond. Please try again."

    except requests.exceptions.HTTPError as e:
        print("Gemini API error:", e.response.text)
        return "Gemini AI request failed. Check the backend logs."

    except requests.exceptions.RequestException as e:
        print("Gemini connection error:", str(e))
        return "Unable to connect to Gemini AI. Please try again later."

    except (KeyError, IndexError, ValueError):
        return "Gemini AI returned an unexpected response."