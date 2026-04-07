import os, sys, sqlite3
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db.schema import DB_PATH

HEAVY_BENCH = {
    1:  [(0.75, "5", 3), (0.63, "10", 2)],
    2:  [(0.775, "5", 3), (0.65, "10", 2)],
    3:  [(0.80, "4", 3), (0.67, "8", 2)],
    4:  [(0.825, "4", 3), (0.69, "8", 2)],
    5:  [(0.85, "3", 3), (0.71, "5", 3)],
    6:  [(0.875, "3", 3), (0.73, "5", 3)],
    7:  [(0.90, "2", 2), (0.75, "3", 3)],
    8:  [(0.925, "2", 2), (0.77, "3", 3)],
    9:  [(0.95, "1", 2), (0.79, "2", 3)],
    10: [(0.85, "1", 1), (0.93, "1", 1), (1.0, "1", 1)],
}
HIGHER_REP_BENCH = {
    1:  [(0.57, "15", 1), (0.43, "20", 2)],
    2:  [(0.59, "15", 1), (0.45, "20", 2)],
    3:  [(0.61, "15", 1), (0.47, "20", 2)],
    4:  [(0.63, "15", 1), (0.49, "20", 2)],
    5:  [(0.65, "15", 1), (0.51, "20", 2)],
    6:  [(0.67, "12", 1), (0.53, "15", 3)],
    7:  [(0.69, "12", 1), (0.55, "15", 3)],
    8:  [(0.71, "10", 1), (0.57, "15", 2)],
    9:  [(0.73, "10", 1), (0.59, "15", 2)],
    10: [(0.75, "8", 1),  (0.61, "15", 2)],
}
HEAVY_ACC = [
    ("Tricep Pushdowns", None, "12", 4, "1 min"),
    ("Rear Delt Pec Dec", None, "12", 4, "1 min"),
    ("Incline Y Delt Raise", None, "12", 4, "1 min"),
]
HIGHER_ACC = [
    ("Incline Dumbbell Press", None, "12", 4, "1 min"),
    ("Dumbbell Skull Crushers", None, "12", 4, "1 min"),
    ("Incline Side Delt Raise", None, "12", 4, "1 min"),
]
BACK_DAY = [
    ("Chest Supported Row Machine", None, "6", 6, "75 seconds", "Sets 1-4: 4-7/10 RPE. Sets 5-6: 8-9/10. Final: top set x70% to failure."),
    ("Neutral Grip Pulldowns", None, "15", 4, "1 min", None),
    ("Seated Cable Row (bench grip)", None, "10", 4, "1 min", None),
    ("Straight Arm Pulldowns", None, "15", 4, "1 min", None),
    ("Kelso Shrugs", None, "10", 4, "1-2 mins", None),
    ("Dumbbell Hammer Curls", None, "12", 4, "1-2 mins", None),
]
REST = "5-10 minutes"

conn = sqlite3.connect(DB_PATH)
conn.executescript(open(os.path.join(os.path.dirname(__file__), "protocols_migration.sql")).read())
conn.commit()

existing = conn.execute("SELECT id FROM protocols WHERE title = 'Joey T Training Method Bench'").fetchone()
if existing:
    print(f"Already imported (id={existing[0]})")
    conn.close()
    raise SystemExit(0)

cur = conn.execute("INSERT INTO protocols (title, description, weeks) VALUES (?, ?, ?)",
    ("Joey T Training Method Bench",
     "10-week bench program. Heavy + Higher Rep days. Goal: 10-15 lbs above current max.", 10))
pid = cur.lastrowid
print(f"Protocol id={pid}")

for week in range(1, 11):
    cur = conn.execute("INSERT INTO protocol_days (protocol_id, week_number, day_label, sort_order) VALUES (?,?,?,?)", (pid, week, "Heavy Bench", 1))
    hid = cur.lastrowid
    for i, (pct, reps, sets) in enumerate(HEAVY_BENCH[week]):
        label = "Top Set" if i == 0 else "Backdown"
        conn.execute("INSERT INTO prescribed_sets (protocol_day_id, exercise, load_pct, reps, sets, rest, sort_order) VALUES (?,?,?,?,?,?,?)",
            (hid, f"Bench Press ({label})", pct, reps, sets, REST, i+1))
    for i, (ex, lp, reps, sets, rest) in enumerate(HEAVY_ACC):
        conn.execute("INSERT INTO prescribed_sets (protocol_day_id, exercise, load_pct, reps, sets, rest, sort_order) VALUES (?,?,?,?,?,?,?)",
            (hid, ex, lp, reps, sets, rest, len(HEAVY_BENCH[week])+i+1))
    cur = conn.execute("INSERT INTO protocol_days (protocol_id, week_number, day_label, sort_order) VALUES (?,?,?,?)", (pid, week, "Higher Rep Bench", 2))
    rid = cur.lastrowid
    for i, (pct, reps, sets) in enumerate(HIGHER_REP_BENCH[week]):
        label = "Top Set" if i == 0 else "Backdown"
        conn.execute("INSERT INTO prescribed_sets (protocol_day_id, exercise, load_pct, reps, sets, rest, sort_order) VALUES (?,?,?,?,?,?,?)",
            (rid, f"Bench Press ({label})", pct, reps, sets, REST, i+1))
    for i, (ex, lp, reps, sets, rest) in enumerate(HIGHER_ACC):
        conn.execute("INSERT INTO prescribed_sets (protocol_day_id, exercise, load_pct, reps, sets, rest, sort_order) VALUES (?,?,?,?,?,?,?)",
            (rid, ex, lp, reps, sets, rest, len(HIGHER_REP_BENCH[week])+i+1))

cur = conn.execute("INSERT INTO protocol_days (protocol_id, week_number, day_label, sort_order) VALUES (?,?,?,?)", (pid, 0, "Back Day", 3))
bid = cur.lastrowid
for i, row in enumerate(BACK_DAY):
    conn.execute("INSERT INTO prescribed_sets (protocol_day_id, exercise, load_pct, reps, sets, rest, notes, sort_order) VALUES (?,?,?,?,?,?,?,?)",
        (bid, row[0], row[1], row[2], row[3], row[4], row[5] if len(row)>5 else None, i+1))

conn.commit()
days = conn.execute("SELECT pd.week_number, pd.day_label, COUNT(*) FROM protocol_days pd JOIN prescribed_sets ps ON ps.protocol_day_id=pd.id WHERE pd.protocol_id=? GROUP BY pd.id ORDER BY pd.week_number, pd.sort_order", (pid,)).fetchall()
print(f"\n{len(days)} days loaded:")
for w, l, c in days:
    print(f"  Week {w} | {l} | {c} sets")
conn.close()
print("Done.")
