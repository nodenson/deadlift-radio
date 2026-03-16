import sqlite3
from db.schema import DB_PATH


def format_load(load: float):
    if float(load).is_integer():
        return int(load)
    return round(load, 1)


def estimate_e1rm(load: float, reps: int) -> float:
    if load <= 0 or reps <= 0:
        return 0.0
    return load * (1 + reps / 30.0)


def get_last_session(conn):
    cur = conn.cursor()
    cur.execute("""
        SELECT id, date, bodyweight, notes
        FROM sessions
        ORDER BY id DESC
        LIMIT 1
    """)
    return cur.fetchone()


def get_session_by_id(conn, session_id: int):
    cur = conn.cursor()
    cur.execute("""
        SELECT id, date, bodyweight, notes
        FROM sessions WHERE id = ?
    """, (session_id,))
    return cur.fetchone()


def get_exercises_for_session(conn, session_id: int):
    cur = conn.cursor()
    cur.execute("""
        SELECT id, name FROM exercises
        WHERE session_id = ? ORDER BY id
    """, (session_id,))
    return cur.fetchall()


def get_sets_for_exercise(conn, exercise_id: int):
    cur = conn.cursor()
    cur.execute("""
        SELECT load, reps FROM sets
        WHERE exercise_id = ? ORDER BY id
    """, (exercise_id,))
    return cur.fetchall()


def get_exposures_for_session(conn, session_id: int):
    cur = conn.cursor()
    cur.execute("""
        SELECT movement, implement, reps, seconds, load, notes
        FROM exposures WHERE session_id = ? ORDER BY id
    """, (session_id,))
    return cur.fetchall()


def get_recent_sessions(conn, limit: int = 10):
    cur = conn.cursor()
    cur.execute("""
        SELECT id, date, bodyweight, notes
        FROM sessions ORDER BY id DESC LIMIT ?
    """, (limit,))
    return cur.fetchall()


def find_sessions_by_date(conn, session_date: str):
    cur = conn.cursor()
    cur.execute("""
        SELECT id, date, bodyweight, notes
        FROM sessions WHERE date = ? ORDER BY id DESC
    """, (session_date,))
    return cur.fetchall()


def get_max_session_date(conn):
    cur = conn.cursor()
    cur.execute("SELECT MAX(date) FROM sessions")
    row = cur.fetchone()
    return row[0] if row else None


def get_all_sessions_with_exercises(conn):
    cur = conn.cursor()
    cur.execute("""
        SELECT s.id, s.date, e.name
        FROM sessions s
        LEFT JOIN exercises e ON e.session_id = s.id
        ORDER BY s.date, s.id, e.id
    """)
    rows = cur.fetchall()

    sessions = {}
    for sid, date, name in rows:
        if sid not in sessions:
            sessions[sid] = {"id": sid, "date": date, "exercises": []}
        if name:
            sessions[sid]["exercises"].append(name)
    return list(sessions.values())


def delete_session_by_id(conn, session_id: int) -> bool:
    cur = conn.cursor()
    cur.execute("SELECT id FROM sessions WHERE id = ?", (session_id,))
    if not cur.fetchone():
        return False
    cur.execute("DELETE FROM sets WHERE exercise_id IN (SELECT id FROM exercises WHERE session_id = ?)", (session_id,))
    cur.execute("DELETE FROM exercises WHERE session_id = ?", (session_id,))
    cur.execute("DELETE FROM exposures WHERE session_id = ?", (session_id,))
    cur.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    conn.commit()
    return True


def get_sets_in_date_range(conn, start_date: str, end_date: str):
    cur = conn.cursor()
    cur.execute("""
        SELECT s.date, ex.name, st.load, st.reps
        FROM sets st
        JOIN exercises ex ON ex.id = st.exercise_id
        JOIN sessions s ON s.id = ex.session_id
        WHERE s.date >= ? AND s.date <= ?
        ORDER BY s.date, ex.name, st.id
    """, (start_date, end_date))
    return cur.fetchall()


def get_exposures_in_date_range(conn, start_date: str, end_date: str):
    cur = conn.cursor()
    cur.execute("""
        SELECT s.date, e.movement, e.implement, e.reps, e.seconds, e.load
        FROM exposures e
        JOIN sessions s ON s.id = e.session_id
        WHERE s.date >= ? AND s.date <= ?
        ORDER BY s.date, e.id
    """, (start_date, end_date))
    return cur.fetchall()


def get_bench_sets_all_time(conn):
    cur = conn.cursor()
    cur.execute("""
        SELECT s.date, st.load, st.reps
        FROM sets st
        JOIN exercises ex ON ex.id = st.exercise_id
        JOIN sessions s ON s.id = ex.session_id
        WHERE ex.name = 'Bench'
        ORDER BY s.date, st.id
    """)
    return cur.fetchall()


def get_all_sets_all_time(conn):
    cur = conn.cursor()
    cur.execute("""
        SELECT s.date, st.load, st.reps
        FROM sets st
        JOIN exercises ex ON ex.id = st.exercise_id
        JOIN sessions s ON s.id = ex.session_id
        ORDER BY s.date, st.id
    """)
    return cur.fetchall()


def get_all_sets_with_exercise_all_time(conn):
    cur = conn.cursor()
    cur.execute("""
        SELECT s.date, ex.name, st.load, st.reps
        FROM sets st
        JOIN exercises ex ON ex.id = st.exercise_id
        JOIN sessions s ON s.id = ex.session_id
        ORDER BY s.date, st.id
    """)
    return cur.fetchall()


def get_pr_by_exercise(conn):
    cur = conn.cursor()
    cur.execute("""
        SELECT e.name, MAX(s.load)
        FROM sets s
        JOIN exercises e ON s.exercise_id = e.id
        GROUP BY e.name
        ORDER BY e.name
    """)
    return cur.fetchall()


def get_tonnage_in_date_range(conn, start_date: str, end_date: str) -> float:
    cur = conn.cursor()
    cur.execute("""
        SELECT COALESCE(SUM(st.load * st.reps), 0)
        FROM sets st
        JOIN exercises ex ON st.exercise_id = ex.id
        JOIN sessions sess ON ex.session_id = sess.id
        WHERE date(sess.date) BETWEEN date(?) AND date(?)
    """, (start_date, end_date))
    return float(cur.fetchone()[0] or 0)

def session_has_pr(conn, session_id: int) -> bool:
    """
    Returns True if any set in this session beats the all-time
    max load for that exercise (excluding this session).
    """
    cur = conn.cursor()
    cur.execute("""
        SELECT ex.name, st.load
        FROM sets st
        JOIN exercises ex ON st.exercise_id = ex.id
        WHERE ex.session_id = ?
    """, (session_id,))
    session_sets = cur.fetchall()

    for exercise_name, load in session_sets:
        cur.execute("""
            SELECT MAX(st.load)
            FROM sets st
            JOIN exercises ex ON st.exercise_id = ex.id
            JOIN sessions s ON ex.session_id = s.id
            WHERE ex.name = ? AND s.id != ?
        """, (exercise_name, session_id))
        row = cur.fetchone()
        prev_max = row[0] if row and row[0] is not None else 0
        if load > prev_max:
            return True

    return False
