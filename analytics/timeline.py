# /home/bune/deadlift_radio/analytics/timeline.py

import sqlite3
import sys
sys.path.insert(0, '/home/bune/deadlift_radio')

from db.queries import (
    get_timeline_sessions,
    get_top_lifts_for_session,
    session_had_pr,
)
from db.schema import DB_PATH


def fmt(n):
    if n is None:
        return "-"
    if isinstance(n, float) and n == int(n):
        return int(n)
    return round(n, 1)


def build_timeline(limit=5, db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    sessions = get_timeline_sessions(conn, limit=limit)

    entries = []
    for s in sessions:
        sid = s["id"]
        top_lifts = get_top_lifts_for_session(conn, sid)
        pr_flag = session_had_pr(conn, sid)

        lift_strs = []
        for name, top_load, reps in top_lifts:
            lift_strs.append(f"{name} {fmt(top_load)} x {reps}")

        entries.append({
            "session_id": sid,
            "date": s["date"],
            "bodyweight": fmt(s["bodyweight"]) if s["bodyweight"] else None,
            "total_sets": s["total_sets"],
            "total_reps": s["total_reps"],
            "tonnage": round(s["tonnage"]),
            "top_lifts": lift_strs,
            "pr": pr_flag,
        })

    conn.close()

    return {
        "limit": limit,
        "entries": entries,
    }
