# engine.py
from datetime import date, timedelta
from typing import List, Dict

PAYPAL_FIXED_FEE = 0.49
PAYPAL_PERCENT_FEE = 0.0349  # 3.49% standard US merchant rate

def compute_product_price(materials: float, hours: float, rate: float, packaging: float, shipping: float, overhead: float, target_margin_pct: float) -> Dict[str, float]:
    labor = hours * rate
    base_cost = materials + labor + packaging + shipping + overhead
    margin_decimal = target_margin_pct / 100.0
    
    # Formula accounting for target margin and PayPal merchant fee deductions
    # Price = (Base Cost + Fixed Fee) / (1 - (Target Margin + Percent Fee))
    denominator = 1.0 - (margin_decimal + PAYPAL_PERCENT_FEE)
    if denominator <= 0:
        denominator = 0.01  # Guard against division by zero or invalid margins
    
    suggested_price = (base_cost + PAYPAL_FIXED_FEE) / denominator
    net_profit = suggested_price - base_cost - (suggested_price * PAYPAL_PERCENT_FEE + PAYPAL_FIXED_FEE)
    
    return {
        "base_cost": round(base_cost, 2),
        "suggested_price": round(suggested_price, 2),
        "estimated_net_profit": round(net_profit, 2),
        "effective_margin_pct": round((net_profit / suggested_price) * 100, 2)
    }

def project_cash_flow(starting_balance: float, days: int, transactions: List[dict], invoices: List[dict], delay_invoices_by_days: int = 0) -> List[dict]:
    timeline = []
    current_bal = starting_balance
    today = date.today()

    for d in range(days + 1):
        day_date = today + timedelta(days=d)
        inflows = sum(t['amount'] for t in transactions if t['due_date'] == day_date and t['type'] == 'INCOME')
        outflows = sum(t['amount'] for t in transactions if t['due_date'] == day_date and t['type'] == 'EXPENSE')
        
        # Add invoice payments based on simulated or scheduled receipt dates
        for inv in invoices:
            effective_due = inv['due_date'] + timedelta(days=delay_invoices_by_days)
            if effective_due == day_date and inv['status'] in ['SENT', 'PAID']:
                inflows += inv['amount']

        current_bal += (inflows - outflows)
        timeline.append({
            "date": day_date.isoformat(),
            "inflows": round(inflows, 2),
            "outflows": round(outflows, 2),
            "projected_balance": round(current_bal, 2)
        })
    return timeline