from sqlalchemy import text

from database import engine

try:
    with engine.connect() as connection:
        result = connection.execute(text("SELECT version()"))
        version = result.scalar()

        print("PostgreSQL connection successful!")
        print(version)

except Exception as error:
    print("PostgreSQL connection failed.")
    print(type(error).__name__)
    print(error)