TASK: Add exercise alias DB table

FILES: db/schema.py, db/queries.py

In db/schema.py, add to init_db():
CREATE TABLE IF NOT EXISTS exercise_aliases (
    alias_text TEXT PRIMARY KEY,
    canonical_name TEXT NOT NULL,
    seen_count INTEGER DEFAULT 1,
    last_seen TEXT
);

In db/queries.py, add two functions:

def upsert_exercise_alias(conn, alias_text: str, canonical_name: str):
    from datetime import datetime
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO exercise_aliases (alias_text, canonical_name, last_seen)
        VALUES (?, ?, ?)
        ON CONFLICT(alias_text) DO UPDATE SET
            seen_count = seen_count + 1,
            last_seen = excluded.last_seen
    """, (alias_text.lower().strip(), canonical_name, datetime.now().strftime("%Y-%m-%d")))
    conn.commit()

def lookup_exercise_alias(conn, alias_text: str):
    cur = conn.cursor()
    cur.execute("SELECT canonical_name FROM exercise_aliases WHERE alias_text = ?", (alias_text.lower().strip(),))
    row = cur.fetchone()
    return row[0] if row else None

RULES:
- Only modify db/schema.py and db/queries.py
- Do not touch CLI, reports, or analytics
- Do not break existing functions
