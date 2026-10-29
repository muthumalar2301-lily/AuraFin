from pydantic import BaseModel
from datetime import date
from typing import Optional

class PricingRequest(BaseModel):
    materials: float = 0.0
    hours: float = 0.0
    rate: float = 0.0
    packaging: float = 0.0
    shipping: float = 0.0
    overhead: float = 0.0
    target_margin: float = 30.0

class InvoiceCreateRequest(BaseModel):
    recipient_email: str  # Changed from EmailStr to str
    item_name: str
    amount: float
    due_date: date

class ChatQueryRequest(BaseModel):
    query: str