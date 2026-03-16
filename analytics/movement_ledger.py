# /home/bune/deadlift_radio/analytics/movement_ledger.py

import sqlite3
import sys
from datetime import datetime, timedelta

sys.path.insert(0, '/home/bune/deadlift_radio')

from db.queries import get_sets_with_movements_in_window
from db.schema import DB_PATH
from classification.movements import classify_exercise_movement


def fmt(n):
    if n is None:
        return "-"
    if isinstance(n, float) and n == int(n):
        return int(n)
    return round(n, 1)


def build_movement_ledger(days=30, db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    end = datetime.today()
    start = end - timedelta(days=days)
    start_str = start.strftime("%Y-%m-%d")
    end_str = end.strftime("%Y-%m-%d")

    rows = get_sets_with_movements_in_window(conn, start_str, end_str)
    conn.close()

    if not rows:
        return {"days": days, "start": start_str, "end": end_str, "movements": []}

    # Aggregate by movement
    movements = {}
    total_tonnage = 0.0

    for row in rows:
        name = row["name"]
        load = row["load"] or 0
        reps = row["reps"] or 0
        movement = classify_exercise_movement(name)
        tonnage = load * reps
        total_tonnage += tonnage

        if movement not in movements:
            movements[movement] = {
                "movement": movement,
                "sets": 0,
                "reps": 0,
                "tonnage": 0.0,
                "exercises": {},
            }

        movements[movement]["sets"] += 1
        movements[movement]["reps"] += reps
        movements[movement]["tonnage"] += tonnage

        ex = movements[movement]["exercises"]
        if name not in ex:
            ex[name] = {"sets": 0, "tonnage": 0.0}
        ex[name]["sets"] += 1
        ex[name]["tonnage"] += tonnage

    # Build ranked list
    ranked = sorted(movements.values(), key=lambda x: x["tonnage"], reverse=True)

    for m in ranked:
        m["tonnage"] = round(m["tonnage"])
        m["share"] = round(m["tonnage"] / total_tonnage * 100, 1) if total_tonnage else 0
        # Top contributing exercises
        top_ex = sorted(m["exercises"].items(), key=lambda x: x[1]["tonnage"], reverse=True)[:3]
        m["top_exercises"] = [ex_name for ex_name, _ in top_ex]
        del m["exercises"]

    return {
        "days": days,
        "start": start_str,
        "end": end_str,
        "total_tonnage": round(total_tonnage),
        "movements": ranked,
    }
