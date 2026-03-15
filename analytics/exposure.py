import sqlite3
from datetime import datetime, timedelta
from db.schema import DB_PATH
from db.queries import get_max_session_date, get_exposures_in_date_range, get_sets_in_date_range
from classification.movements import infer_exposure_movements


def get_current_balance_snapshot(days: int = 7) -> dict:
    conn = sqlite3.connect(DB_PATH)
    max_date = get_max_session_date(conn)
    if not max_date:
        conn.close()
        return {"push_sets": 0, "pull_sets": 0}

    end_date = datetime.strptime(max_date, "%Y-%m-%d").date()
    start_date = end_date - timedelta(days=days - 1)

    cur = conn.cursor()
    cur.execute("""
        SELECT LOWER(COALESCE(movement, '')), COUNT(*)
        FROM exposures e
        JOIN sessions sess ON e.session_id = sess.id
        WHERE date(sess.date) BETWEEN date(?) AND date(?)
        GROUP BY LOWER(COALESCE(movement, ''))
    """, (start_date.isoformat(), end_date.isoformat()))
    rows = cur.fetchall()
    conn.close()

    push_keys = {"horizontal_push", "vertical_push", "push"}
    pull_keys = {"horizontal_pull", "vertical_pull", "pull"}

    push_sets = sum(count for movement, count in rows if movement in push_keys)
    pull_sets = sum(count for movement, count in rows if movement in pull_keys)

    return {"push_sets": int(push_sets), "pull_sets": int(pull_sets)}


def get_current_exposure_snapshot(days: int = 7) -> dict:
    conn = sqlite3.connect(DB_PATH)
    max_date = get_max_session_date(conn)
    if not max_date:
        conn.close()
        return {
            "elbow_extension_score": 0,
            "elbow_flexion_pull_score": 0,
            "forearm_total_score": 0,
            "forearm_max_day_score": 0,
        }

    end_date = datetime.strptime(max_date, "%Y-%m-%d").date()
    start_date = end_date - timedelta(days=days - 1)

    cur = conn.cursor()
    cur.execute("""
        SELECT sess.date, LOWER(COALESCE(e.movement,'')), LOWER(COALESCE(e.implement,'')),
               COALESCE(e.reps,0), COALESCE(e.seconds,0), COALESCE(e.load,0), LOWER(COALESCE(e.notes,''))
        FROM exposures e
        JOIN sessions sess ON e.session_id = sess.id
        WHERE date(sess.date) BETWEEN date(?) AND date(?)
    """, (start_date.isoformat(), end_date.isoformat()))
    rows = cur.fetchall()
    conn.close()

    extension_score = flexion_pull_score = 0
    day_scores = {}

    for session_date, movement, implement, reps, seconds, load, notes in rows:
        if movement in {"horizontal_push", "vertical_push", "push", "elbow_extension"}:
            extension_score += 1
        if "tricep" in implement or "tricep" in notes:
            extension_score += 1
        if "extension" in movement or "extension" in notes:
            extension_score += 1
        if movement in {"horizontal_pull", "vertical_pull", "pull", "elbow_flexion"}:
            flexion_pull_score += 1
        if "bicep" in implement or "bicep" in notes:
            flexion_pull_score += 1
        if "flexion" in movement or "flexion" in notes:
            flexion_pull_score += 1

        forearm_points = 0
        if movement in {"support_grip", "crush_grip", "pronation_supination", "lever"}:
            forearm_points += 1
        if any(t in implement for t in ["grip", "gripper", "pronation", "supination", "lever", "wrist", "forearm"]):
            forearm_points += 1
        if any(t in notes for t in ["grip", "gripper", "pronation", "supination", "lever", "wrist", "forearm"]):
            forearm_points += 1
        if forearm_points:
            day_scores[session_date] = day_scores.get(session_date, 0) + forearm_points

    return {
        "elbow_extension_score": int(extension_score),
        "elbow_flexion_pull_score": int(flexion_pull_score),
        "forearm_total_score": int(sum(day_scores.values())),
        "forearm_max_day_score": int(max(day_scores.values()) if day_scores else 0),
    }


def show_weekly_exposure_report(days: int = 7) -> None:
    conn = sqlite3.connect(DB_PATH)
    max_date = get_max_session_date(conn)

    if not max_date:
        print("\nNo sessions found.")
        conn.close()
        return

    anchor_date = datetime.strptime(max_date, "%Y-%m-%d").date()
    start_date = anchor_date - timedelta(days=days - 1)

    direct_rows = get_exposures_in_date_range(conn, start_date.isoformat(), anchor_date.isoformat())
    inferred_rows = get_sets_in_date_range(conn, start_date.isoformat(), anchor_date.isoformat())
    conn.close()

    print("\n+++ WEEKLY JOINT / TENDON EXPOSURE +++")
    print(f"Window: {start_date} to {anchor_date}")

    if not direct_rows and not inferred_rows:
        print("No exposure data found in this window.")
        return

    movement_totals = {}
    daily_totals = {}

    def ensure_bucket(d, m):
        if m not in movement_totals:
            movement_totals[m] = {"reps": 0, "seconds": 0, "entries": 0, "sources": {"direct": 0, "inferred": 0}}
        if d not in daily_totals:
            daily_totals[d] = {}
        if m not in daily_totals[d]:
            daily_totals[d][m] = {"reps": 0, "seconds": 0, "entries": 0, "sources": {"direct": 0, "inferred": 0}}

    for session_date, movement, implement, reps, seconds, load in direct_rows:
        ensure_bucket(session_date, movement)
        if reps is not None:
            movement_totals[movement]["reps"] += reps
            daily_totals[session_date][movement]["reps"] += reps
        if seconds is not None:
            movement_totals[movement]["seconds"] += seconds
            daily_totals[session_date][movement]["seconds"] += seconds
        movement_totals[movement]["entries"] += 1
        daily_totals[session_date][movement]["entries"] += 1
        movement_totals[movement]["sources"]["direct"] += 1
        daily_totals[session_date][movement]["sources"]["direct"] += 1

    for session_date, exercise_name, load, reps in inferred_rows:
        for movement in infer_exposure_movements(exercise_name):
            ensure_bucket(session_date, movement)
            movement_totals[movement]["reps"] += reps
            daily_totals[session_date][movement]["reps"] += reps
            movement_totals[movement]["entries"] += 1
            daily_totals[session_date][movement]["entries"] += 1
            movement_totals[movement]["sources"]["inferred"] += 1
            daily_totals[session_date][movement]["sources"]["inferred"] += 1

    print("\nTotals by movement:")
    for movement, totals in movement_totals.items():
        bits = []
        if totals["reps"]: bits.append(f"{totals['reps']} reps")
        if totals["seconds"]: bits.append(f"{totals['seconds']} sec")
        bits.append(f"{totals['entries']} exposures")
        src = []
        if totals["sources"]["direct"]: src.append(f"{totals['sources']['direct']} direct")
        if totals["sources"]["inferred"]: src.append(f"{totals['sources']['inferred']} inferred")
        if src: bits.append(", ".join(src))
        print(f"- {movement}: " + ", ".join(bits))

    print("\nDaily breakdown:")
    for d in sorted(daily_totals.keys()):
        print(d)
        for movement, totals in daily_totals[d].items():
            bits = []
            if totals["reps"]: bits.append(f"{totals['reps']} reps")
            if totals["seconds"]: bits.append(f"{totals['seconds']} sec")
            bits.append(f"{totals['entries']} exposures")
            print(f"  - {movement}: " + ", ".join(bits))