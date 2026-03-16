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


def log_prs(conn, session_id: int, db_path: str, log_path: str = "/home/bune/deadlift_radio/logs/pr_history.log") -> list:
    """
    Detects PRs in the session, writes them to the personal_records table
    and appends to the flat log file. Returns list of PR dicts.
    """
    import os
    from datetime import datetime

    cur = conn.cursor()

    # Get session date
    cur.execute("SELECT date FROM sessions WHERE id = ?", (session_id,))
    row = cur.fetchone()
    if not row:
        return []
    session_date = row[0]

    # Get all sets for this session
    cur.execute("""
        SELECT ex.name, st.load, st.reps
        FROM sets st
        JOIN exercises ex ON st.exercise_id = ex.id
        WHERE ex.session_id = ?
    """, (session_id,))
    session_sets = cur.fetchall()

    # Find top load+reps per exercise in this session
    session_tops = {}
    for exercise_name, load, reps in session_sets:
        if exercise_name not in session_tops or load > session_tops[exercise_name][0]:
            session_tops[exercise_name] = (load, reps)

    prs = []
    for exercise_name, (load, reps) in session_tops.items():
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
            prs.append({
                "exercise": exercise_name,
                "load": load,
                "reps": reps,
                "prev_max": prev_max,
                "date": session_date,
            })

    for pr in prs:
        cur.execute(
            "SELECT id FROM personal_records WHERE session_id = ? AND exercise = ?",
            (session_id, pr["exercise"])
        )
        if cur.fetchone():
            continue
        cur.execute(
            "INSERT INTO personal_records (session_id, date, exercise, load, reps, prev_max) VALUES (?, ?, ?, ?, ?, ?)",
            (session_id, pr["date"], pr["exercise"], pr["load"], pr["reps"], pr["prev_max"])
        )
    conn.commit()

    # Append to flat log — only write entries not already in the file
    if prs:
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        existing = open(log_path).read() if os.path.exists(log_path) else ""
        with open(log_path, "a") as f:
            for pr in prs:
                prev = f"{pr['prev_max']} lbs" if pr['prev_max'] else "no prior record"
                line = f"[{pr['date']}] PR — {pr['exercise']} — {pr['load']} lbs x {pr['reps']} (prev: {prev})\n"
                if line not in existing:
                    f.write(line)

    return prs


def get_pr_register(conn):
    cur = conn.cursor()
    cur.execute("""
        SELECT date, exercise, load, reps, prev_max
        FROM personal_records
        ORDER BY date DESC, exercise
    """)
    return cur.fetchall()


def get_exercise_history(conn, exercise_name, limit=5):
    cur = conn.cursor()
    cur.execute("""
        SELECT s.date,
               MAX(st.load) as top_load,
               (SELECT reps FROM sets st2
                JOIN exercises ex2 ON st2.exercise_id = ex2.id
                JOIN sessions s2 ON ex2.session_id = s2.id
                WHERE ex2.name = ex.name AND s2.date = s.date
                ORDER BY st2.load DESC LIMIT 1) as top_reps,
               SUM(st.load * st.reps) as tonnage
        FROM sets st
        JOIN exercises ex ON st.exercise_id = ex.id
        JOIN sessions s ON ex.session_id = s.id
        WHERE ex.name = ?
        GROUP BY s.date
        ORDER BY s.date DESC
        LIMIT ?
    """, (exercise_name, limit))
    return cur.fetchall()


def get_exercise_30d_stats(conn, exercise_name):
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(DISTINCT s.date) as appearances,
               COALESCE(SUM(st.load * st.reps), 0) as volume
        FROM sets st
        JOIN exercises ex ON st.exercise_id = ex.id
        JOIN sessions s ON ex.session_id = s.id
        WHERE ex.name = ?
        AND date(s.date) >= date('now', '-30 days')
    """, (exercise_name,))
    return cur.fetchone()


def get_exercise_best_signal(conn, exercise_name):
    cur = conn.cursor()
    cur.execute("""
        SELECT st.load, st.reps
        FROM sets st
        JOIN exercises ex ON st.exercise_id = ex.id
        WHERE ex.name = ?
        ORDER BY st.load DESC
        LIMIT 20
    """, (exercise_name,))
    return cur.fetchall()


def get_exercise_last_seen(conn, exercise_name):
    cur = conn.cursor()
    cur.execute("""
        SELECT MAX(s.date)
        FROM exercises ex
        JOIN sessions s ON ex.session_id = s.id
        WHERE ex.name = ?
    """, (exercise_name,))
    row = cur.fetchone()
    return row[0] if row else None


def get_timeline_sessions(conn, limit=5):
    cur = conn.cursor()
    cur.execute("""
        SELECT s.id, s.date, s.bodyweight,
               COUNT(DISTINCT st.id) as total_sets,
               COALESCE(SUM(st.reps), 0) as total_reps,
               COALESCE(SUM(st.load * st.reps), 0) as tonnage
        FROM sessions s
        LEFT JOIN exercises ex ON ex.session_id = s.id
        LEFT JOIN sets st ON st.exercise_id = ex.id
        GROUP BY s.id
        ORDER BY s.date DESC
        LIMIT ?
    """, (limit,))
    return cur.fetchall()


def get_top_lifts_for_session(conn, session_id, top_n=3):
    cur = conn.cursor()
    cur.execute("""
        SELECT ex.name, MAX(st.load) as top_load, st.reps
        FROM sets st
        JOIN exercises ex ON st.exercise_id = ex.id
        WHERE ex.session_id = ?
        AND st.load > 0
        GROUP BY ex.name
        ORDER BY top_load DESC
        LIMIT ?
    """, (session_id, top_n))
    return cur.fetchall()


def session_had_pr(conn, session_id):
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*) FROM personal_records WHERE session_id = ?
    """, (session_id,))
    return cur.fetchone()[0] > 0


def get_sets_with_movements_in_window(conn, start_date, end_date):
    cur = conn.cursor()
    cur.execute("""
        SELECT s.date, ex.name, st.load, st.reps
        FROM sets st
        JOIN exercises ex ON st.exercise_id = ex.id
        JOIN sessions s ON ex.session_id = s.id
        WHERE date(s.date) BETWEEN date(?) AND date(?)
        ORDER BY s.date, ex.name
    """, (start_date, end_date))
    return cur.fetchall()
