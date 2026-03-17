import sqlite3
from datetime import datetime
from db.schema import DB_PATH


def get_bodyweight_trend():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT date, bodyweight FROM sessions WHERE bodyweight IS NOT NULL ORDER BY date ASC")
    rows = cur.fetchall()
    conn.close()
    return [(date, float(bw)) for date, bw in rows]


def show_bodyweight_trend():
    rows = get_bodyweight_trend()
    if not rows:
        print("No bodyweight data logged yet.")
        return

    print("\n+++ BODYWEIGHT TREND ++")
    print(f"{'Date':<14} {'Weight':>8}  Change")
    print("-" * 32)

    prev = None
    for date, bw in rows:
        if prev is None:
            change = "--"
        else:
            diff = bw - prev
            change = f"+{diff:.1f}" if diff > 0 else f"{diff:.1f}"
        print(f"{date:<14} {bw:>7.1f}  {change}")
        prev = bw

    weights = [bw for _, bw in rows]
    avg = sum(weights) / len(weights)
    trend = weights[-1] - weights[0] if len(weights) > 1 else 0.0
    direction = "up" if trend > 0 else "down" if trend < 0 else "stable"

    print("-" * 32)
    print(f"Average:  {avg:.1f} lbs")
    print(f"Trend:    {abs(trend):.1f} lbs {direction} over {len(rows)} sessions")
