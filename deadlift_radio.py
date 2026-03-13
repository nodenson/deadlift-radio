import sqlite3
import re
from datetime import datetime

import os
DB_PATH = os.getenv("DLR_DB_PATH", "archive_dev.db")

def init_db() -> None:
    conn = sqlite3.connect(DB_PATH)
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

    conn.commit()
    conn.close()


def parse_set_line(line: str):
    """
    Supports:
      315 x 5
      275 x 8 x 2
      365x1
      225 X 10 X 3
    Returns list of (load, reps)
    """
    pattern = r"^\s*(\d+(?:\.\d+)?)\s*[xX]\s*(\d+)(?:\s*[xX]\s*(\d+))?\s*$"
    match = re.match(pattern, line)
    if not match:
        return None

    load = float(match.group(1))
    reps = int(match.group(2))
    set_count = int(match.group(3)) if match.group(3) else 1

    return [(load, reps) for _ in range(set_count)]


def ingest_workout(raw_text: str, bodyweight=None, session_date=None) -> int:
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    if not lines:
        raise ValueError("Workout log was empty.")

    if session_date is None:
        session_date = datetime.now().strftime("%Y-%m-%d")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO sessions (date, bodyweight, notes) VALUES (?, ?, ?)",
        (session_date, bodyweight, "")
    )
    session_id = cur.lastrowid

    current_exercise_id = None
    session_notes = []
    exercise_names = []

    for line in lines:
        parsed_sets = parse_set_line(line)

        if parsed_sets:
            if current_exercise_id is None:
                session_notes.append(f"Orphan set ignored: {line}")
                continue

            for load, reps in parsed_sets:
                cur.execute(
                    "INSERT INTO sets (exercise_id, load, reps, effort, pain) VALUES (?, ?, ?, ?, ?)",
                    (current_exercise_id, load, reps, None, None)
                )
        else:
            looks_like_exercise = not any(ch.isdigit() for ch in line)

            if looks_like_exercise:
                cur.execute(
                    "INSERT INTO exercises (session_id, name) VALUES (?, ?)",
                    (session_id, line)
                )
                current_exercise_id = cur.lastrowid
                exercise_names.append(line)
            else:
                session_notes.append(line)

    final_notes = "\n".join(session_notes).strip()
    cur.execute(
        "UPDATE sessions SET notes = ? WHERE id = ?",
        (final_notes, session_id)
    )

    conn.commit()
    conn.close()
    return session_id


def show_last_session() -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        SELECT id, date, bodyweight, notes
        FROM sessions
        ORDER BY id DESC
        LIMIT 1
    """)
    session = cur.fetchone()

    if not session:
        print("No sessions found.")
        conn.close()
        return

    session_id, date, bodyweight, notes = session
    print(f"\n=== LAST SESSION ===")
    print(f"Session ID: {session_id}")
    print(f"Date: {date}")
    print(f"Bodyweight: {bodyweight}")
    print(f"Notes: {notes if notes else '(none)'}")

    cur.execute("""
        SELECT id, name
        FROM exercises
        WHERE session_id = ?
        ORDER BY id
    """, (session_id,))
    exercises = cur.fetchall()

    for ex_id, ex_name in exercises:
        print(f"\n{ex_name}")
        cur.execute("""
            SELECT load, reps
            FROM sets
            WHERE exercise_id = ?
            ORDER BY id
        """, (ex_id,))
        sets = cur.fetchall()

        for load, reps in sets:
            if float(load).is_integer():
                load_display = int(load)
            else:
                load_display = load
            print(f"  {load_display} x {reps}")

    conn.close()


def show_prs() -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        SELECT e.name, MAX(s.load)
        FROM sets s
        JOIN exercises e ON s.exercise_id = e.id
        GROUP BY e.name
        ORDER BY e.name
    """)
    rows = cur.fetchall()

    print("\n=== PRs BY EXERCISE ===")
    if not rows:
        print("No data yet.")
    else:
        for name, max_load in rows:
            if float(max_load).is_integer():
                max_load = int(max_load)
            print(f"{name}: {max_load}")

    conn.close()


def main() -> None:
    init_db()

    print("Deadlift Radio Archive Engine")
    print("1) Log workout")
    print("2) Show last session")
    print("3) Show PRs")
    choice = input("Choose an option: ").strip()

    if choice == "1":
        bodyweight_raw = input("Bodyweight (optional): ").strip()
        bodyweight = float(bodyweight_raw) if bodyweight_raw else None

        print("\nPaste workout log. End with a single line containing only END\n")
        buffer = []
        while True:
            line = input()
            if line.strip().upper() == "END":
                break
            buffer.append(line)

        raw_text = "\n".join(buffer)
        session_id = ingest_workout(raw_text, bodyweight=bodyweight)
        print(f"\nLogged session #{session_id}")
        show_last_session()

    elif choice == "2":
        show_last_session()

    elif choice == "3":
        show_prs()

    else:
        print("Invalid choice.")


if __name__ == "__main__":
    main()
