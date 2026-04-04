import os
import sqlite3

DB_PATH = os.getenv("DLR_DB_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "archive_dev.db"))


def init_db() -> None:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        bodyweight REAL,
        notes TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS exercises (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        FOREIGN KEY(session_id) REFERENCES sessions(id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS sets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        exercise_id INTEGER NOT NULL,
        load REAL NOT NULL,
        reps INTEGER NOT NULL,
        effort TEXT,
        pain TEXT,
        FOREIGN KEY(exercise_id) REFERENCES exercises(id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS exposures (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER NOT NULL,
        movement TEXT NOT NULL,
        implement TEXT,
        reps INTEGER,
        seconds INTEGER,
        load REAL,
        notes TEXT,
        FOREIGN KEY(session_id) REFERENCES sessions(id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS personal_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        exercise TEXT NOT NULL,
        load REAL NOT NULL,
        reps INTEGER NOT NULL,
        prev_max REAL,
        FOREIGN KEY(session_id) REFERENCES sessions(id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS exercise_aliases (
        alias_text TEXT PRIMARY KEY,
        canonical_name TEXT NOT NULL,
        seen_count INTEGER DEFAULT 1,
        last_seen TEXT
    );
    """)
    
    conn.commit()
    conn.close()
