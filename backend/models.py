from sqlalchemy import Column, Integer, String, Numeric, Enum, Date, Boolean, DateTime, func
from database import Base

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    description = Column(String(255), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    type = Column(Enum("INCOME", "EXPENSE", name="transaction_types"), nullable=False)
    category = Column(String(100), nullable=False)
    status = Column(Enum("CONFIRMED", "PENDING", name="transaction_status"), default="CONFIRMED")
    due_date = Column(Date, nullable=False)
    is_recurring = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())

class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    paypal_invoice_id = Column(String(100), unique=True, index=True)
    recipient_email = Column(String(255), nullable=False)
    item_name = Column(String(255), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    status = Column(Enum("DRAFT", "SENT", "PAID", "CANCELLED", name="invoice_status"), default="DRAFT")
    due_date = Column(Date, nullable=False)
    created_at = Column(DateTime, server_default=func.now())