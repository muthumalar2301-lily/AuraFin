from sqlalchemy import inspect

from database import Base, engine
from models import Invoice, Transaction
# Import ProductCost too if it is defined in models.py.

try:
    Base.metadata.create_all(bind=engine)

    inspector = inspect(engine)
    tables = inspector.get_table_names()

    print("Tables in PostgreSQL:")
    for table in tables:
        print(f"- {table}")

except Exception as error:
    print("Table creation failed.")
    print(type(error).__name__)
    print(error)