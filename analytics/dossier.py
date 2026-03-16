# /home/bune/deadlift_radio/analytics/dossier.py

import sqlite3
import sys
from datetime import datetime, timedelta

sys.path.insert(0, '/home/bune/deadlift_radio')

from db.queries import (
    get_exercise_history,
    get_exercise_30d_stats,
    get_exercise_best_signal,
    get_exercise_last_seen,
)
from db.schema import DB_PATH


def epley_e1rm(load, reps):
    if reps == 1:
        return load
    return round(load * (1 + reps / 30.0), 1)


def classify_status(history_rows):
    """
    history_rows: list of (date, top_load, top_reps, tonnage) ordered newest first
    Returns: rising, flat, volatile, dormant
    """
    if not history_rows:
        return "dormant"

    last_seen = history_rows[0][0]
    days_since = (datetime.today() - datetime.strptime(last_seen, "%Y-%m-%d")).days
    if days_since > 14:
        return "dormant"

    if len(history_rows) < 2:
        return "flat"

    signals = [epley_e1rm(r[1], r[2]) for r in history_rows if r[1] and r[2]]
    if len(signals) < 2:
        return "flat"

    # Volatile: large swings
    max_sig = max(signals)
    min_sig = min(signals)
    if max_sig > 0 and (max_sig - min_sig) / max_sig > 0.15:
        return "volatile"

    # Rising: newest signal meaningfully above oldest
    if signals[0] > signals[-1] * 1.03:
        return "rising"

    return "flat"


def build_exercise_dossier(exercise_name, db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    history = get_exercise_history(conn, exercise_name, limit=5)
    stats_30d = get_exercise_30d_stats(conn, exercise_name)
    best_signals = get_exercise_best_signal(conn, exercise_name)
    last_seen = get_exercise_last_seen(conn, exercise_name)

    conn.close()

    if not history and not last_seen:
        return None

    # Best observed set and e1rm
    best_e1rm = 0.0
    best_set = None
    for load, reps in (best_signals or []):
        if load and reps:
            e = epley_e1rm(load, reps)
            if e > best_e1rm:
                best_e1rm = e
                best_set = {"load": load, "reps": reps}

    # Recent appearances
    recent = []
    for row in history:
        date, top_load, top_reps, tonnage = row["date"], row["top_load"], row["top_reps"], row["tonnage"]
        e1rm = epley_e1rm(top_load, top_reps) if top_load and top_reps else 0
        recent.append({
            "date": date,
            "top_load": top_load,
            "top_reps": top_reps,
            "tonnage": round(tonnage) if tonnage else 0,
            "e1rm": e1rm,
        })

    status = classify_status([(r["date"], r["top_load"], r["top_reps"], r["tonnage"]) for r in recent])

    appearances_30d = stats_30d["appearances"] if stats_30d else 0
    volume_30d = round(stats_30d["volume"]) if stats_30d else 0

    return {
        "exercise_name": exercise_name,
        "last_seen": last_seen,
        "appearances_30d": appearances_30d,
        "volume_30d": volume_30d,
        "best_set": best_set,
        "best_e1rm": best_e1rm,
        "status": status,
        "recent": recent,
    }
