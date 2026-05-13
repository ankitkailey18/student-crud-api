from database import engine
from sqlalchemy import text

columns = [
    ("content", "TEXT"),
    ("file_name", "VARCHAR"),
    ("file_path", "VARCHAR"),
    ("status", "VARCHAR DEFAULT 'submitted'"),
]

with engine.connect() as conn:
    for col, col_type in columns:
        try:
            conn.execute(text(f"ALTER TABLE submissions ADD COLUMN {col} {col_type}"))
            print(f"Added {col}")
        except Exception as e:
            if "duplicate" in str(e).lower() or "already exists" in str(e).lower():
                print(f"{col} already exists")
            else:
                print(f"Error: {e}")
    conn.commit()
print("Done!")