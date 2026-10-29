from datetime import date, timedelta
from database import SessionLocal, engine, Base
from models import Transaction

Base.metadata.create_all(bind=engine)
db = SessionLocal()

today = date.today()

sample_data = [
    Transaction(description="Initial Bank Balance", amount=850.00, type="INCOME", category="Opening Balance", status="CONFIRMED", due_date=today - timedelta(days=5)),
    Transaction(description="Adobe Creative Cloud", amount=54.99, type="EXPENSE", category="Software", status="CONFIRMED", due_date=today + timedelta(days=3), is_recurring=True),
    Transaction(description="Midjourney Subscription", amount=30.00, type="EXPENSE", category="Software", status="CONFIRMED", due_date=today + timedelta(days=10), is_recurring=True),
    Transaction(description="Figma Professional", amount=15.00, type="EXPENSE", category="Software", status="CONFIRMED", due_date=today + timedelta(days=12), is_recurring=True),
    Transaction(description="Art Print Packaging Materials", amount=45.00, type="EXPENSE", category="Supplies", status="CONFIRMED", due_date=today + timedelta(days=7)),
]

db.add_all(sample_data)
db.commit()
db.close()
print("Demo transactions seeded successfully.")