from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    try:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS announcements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title VARCHAR NOT NULL,
                body TEXT,
                course_id INTEGER REFERENCES courses(id),
                author_id INTEGER REFERENCES users(id),
                created_at TIMESTAMP
            )
        """))
        conn.commit()
        print("Created announcements table")
    except Exception as e:
        print(f"Error: {e}")

print("Done!")