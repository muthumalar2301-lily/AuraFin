import ollama
from sqlalchemy.orm import Session
from datetime import date, timedelta
from models import Transaction, Invoice

# Your verified model tag
OLLAMA_MODEL = "llama3.2"

def generate_financial_advice(user_prompt: str, db: Session) -> str:
    today = date.today()
    
    # 1. Fetch current transaction records
    tx_records = db.query(Transaction).all()
    invoices = db.query(Invoice).all()

    confirmed_income = sum(t.amount for t in tx_records if t.type == "INCOME" and t.status == "CONFIRMED")
    confirmed_expenses = sum(t.amount for t in tx_records if t.type == "EXPENSE" and t.status == "CONFIRMED")
    current_cash = float(confirmed_income - confirmed_expenses)

    # 2. Extract next 30 days of expenses
    upcoming_expenses = [
        {"item": t.description, "amount": float(t.amount), "due": str(t.due_date)}
        for t in tx_records 
        if t.type == "EXPENSE" and today <= t.due_date <= today + timedelta(days=30)
    ]

    # 3. Extract pending PayPal invoices
    pending_invoices = [
        {"to": inv.recipient_email, "amount": float(inv.amount), "due": str(inv.due_date), "status": inv.status}
        for inv in invoices
        if inv.status in ["SENT", "DRAFT"]
    ]

    # 4. Strict context injection
    system_instruction = f"""
You are AuraFin AI, a practical financial advisor for independent freelance creators and artists.
Speak concisely, realistically, and directly about cash flow, risk, and pricing.

CREATOR FINANCIAL SNAPSHOT:
- Current Liquid Cash: ${current_cash:.2f}
- Pending PayPal Invoices: {pending_invoices}
- Scheduled Expenses (Next 30 Days): {upcoming_expenses}

RULES:
1. Ground every statement strictly in the numbers above. Never hallucinate balances.
2. If cash risks dropping below $0 or tight margins loom, advise delaying non-essential purchases.
3. Keep responses strictly within 2 to 4 sentences.
"""

    try:
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_prompt}
            ],
            options={"temperature": 0.2}
        )
        return response["message"]["content"]
    except Exception as e:
        return f"Error contacting local Ollama engine: {str(e)}"