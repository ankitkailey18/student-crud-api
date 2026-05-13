from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    try:
        conn.execute(text("ALTER TABLE courses ADD COLUMN description TEXT"))
        conn.commit()
        print("Added description column to courses")
    except Exception as e:
        if "duplicate" in str(e).lower() or "already exists" in str(e).lower():
            print("Column already exists, skipping")
        else:
            print(f"Error: {e}")
print("Done!")