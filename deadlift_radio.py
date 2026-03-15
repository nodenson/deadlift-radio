from pathlib import Path


# --- Movement classification system ---

EXERCISE_MOVEMENTS = {
    "Bench": "horizontal_press",
    "Incline dumbbell": "incline_press",

    "Hammer curls db": "elbow_flexion",

    "Triceps extensions ez bar": "elbow_extension",
    "reverse triceps extensions cable": "elbow_extension",

    "T bar rows empty chest supported": "row",

    "Machine rear deltoids": "rear_delt",

    "Side deltoid raises machine": "lateral_raise",

    "Pushups": "horizontal_press",
}


def classify_exercise_movement(name: str) -> str:
    return EXERCISE_MOVEMENTS.get(name, "other")

import sqlite3

# --- Grimdark Spinner -------------------------------------------------

import sys
import time
import threading

def grimdark_spinner(message: str, stop_event) -> None:
    symbols = ["[☠]", "[⚙]", "[✠]", "[☢]"]
    i = 0
    while not stop_event.is_set():
        sys.stdout.write(f"\r+++ {message} +++ {symbols[i % len(symbols)]}")
        sys.stdout.flush()
        time.sleep(0.12)
        i += 1
    sys.stdout.write("\r" + " " * (len(message) + 25) + "\r")
    sys.stdout.flush()

def run_with_grimdark_spinner(message: str, fn, *args, **kwargs):
    stop_event = threading.Event()
    thread = threading.Thread(target=grimdark_spinner, args=(message, stop_event))
    thread.start()
    try:
        return fn(*args, **kwargs)
    finally:
        stop_event.set()
        thread.join()

# ----------------------------------------------------------------------

import re
from datetime import datetime, timedelta
import os
import shutil

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

    conn.commit()
    conn.close()


def format_load(load: float):
    if float(load).is_integer():
        return int(load)
    return round(load, 1)


def estimate_e1rm(load: float, reps: int) -> float:
    if load <= 0 or reps <= 0:
        return 0.0
    return load * (1 + reps / 30.0)


def parse_log_date(line: str):
    text = line.strip()
    for fmt in ("%B %d %Y", "%b %d %Y"):
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return None


def parse_standard_set_line(line: str):
    text = line.strip().lower()
    text = re.sub(r"\bthen\b", ",", text)
    text = re.sub(r"\s+", " ", text)

    m = re.match(
        r"^\s*(\d+(?:\.\d+)?)(?:\s*(?:lbs?|lb|s))?\s*[xX]\s*([\d,\s]+?)(?:\s*[xX]\s*(\d+))?\s*(?:reps?)?\s*$",
        text,
    )
    if not m:
        return None

    load = float(m.group(1))
    reps_blob = m.group(2).strip()
    set_count = int(m.group(3)) if m.group(3) else None

    rep_values = [int(x) for x in re.findall(r"\d+", reps_blob)]
    if not rep_values:
        return None

    if set_count is not None and len(rep_values) == 1:
        return [(load, rep_values[0]) for _ in range(set_count)]

    return [(load, reps) for reps in rep_values]


def parse_weight_then_reps_no_x(line: str):
    text = line.strip().lower()
    text = re.sub(r"\s+", " ", text)

    m = re.match(r"^\s*(\d+(?:\.\d+)?)\s*(?:lbs?|lb)\s*(\d+)\s*(?:reps?)?\s*$", text)
    if not m:
        return None

    load = float(m.group(1))
    reps = int(m.group(2))
    return [(load, reps)]


def parse_rep_only_line(line: str, current_load_hint):
    text = line.strip().lower()

    m = re.match(r"^\s*(\d+)\s*(?:reps?)?\s*$", text)
    if not m:
        return None

    reps = int(m.group(1))
    load = current_load_hint if current_load_hint is not None else 0.0
    return [(float(load), reps)]


def parse_weight_only_line(line: str, pending_reps_hint):
    text = line.strip().lower()
    m = re.match(r"^\s*(\d+(?:\.\d+)?)\s*(?:lbs?|lb)\s*$", text)
    if not m:
        return None

    load = float(m.group(1))

    if pending_reps_hint is not None:
        return [(load, int(pending_reps_hint))]

    return ("LOAD_HINT", load)


def looks_like_metadata(line: str) -> bool:
    lower = line.strip().lower()
    month_prefixes = (
        "january ", "february ", "march ", "april ", "may ", "june ",
        "july ", "august ", "september ", "october ", "november ", "december "
    )
    return lower.startswith(month_prefixes) or lower.startswith("bw") or lower.startswith("bodyweight")


def looks_like_note_line(line: str) -> bool:
    lower = line.strip().lower()

    note_starts = (
        "warmup",
        "maybe ",
        "front levers",
        "back levers",
        "scapular pulls",
    )

    note_contains = (
        "neutral setting",
        "seconds",
        "closes each hand",
        "palms down",
        "palms up",
        "laying face down",
    )

    exact_notes = {
        "chest expander",
        "forearm supination pronation device",
        "captains of crush sport gripper",
        "2 springs",
    }

    return (
        lower in exact_notes
        or lower.startswith(note_starts)
        or any(token in lower for token in note_contains)
    )


def extract_bodyweight_from_line(line: str):
    m = re.search(r"bw\.?\s*(\d+(?:\.\d+)?)", line.strip().lower())
    if m:
        return float(m.group(1))
    return None


EXERCISE_ALIASES = {
    "incline db": "Incline dumbbell",
    "incline dumbbells": "Incline dumbbell",
    "incline db press": "Incline dumbbell",

    "hammer curls": "Hammer curls db",
    "db hammer curls": "Hammer curls db",

    "rear delt machine": "Machine rear deltoids",
    "rear delts machine": "Machine rear deltoids",

    "side delt machine": "Side deltoid raises machine",
    "side delt raises machine": "Side deltoid raises machine",

    "ez bar triceps": "Triceps extensions ez bar",
    "ez bar tricep extension": "Triceps extensions ez bar",

    "t bar rows": "T bar rows empty chest supported",
}


def normalize_exercise_name(line: str) -> str:
    cleaned = re.sub(r"\s+", " ", line.strip())
    key = cleaned.lower()
    return EXERCISE_ALIASES.get(key, cleaned)


def is_normal_exercise_heading(line: str) -> bool:
    if any(ch.isdigit() for ch in line):
        return False

    lower = line.strip().lower()
    if lower in {"bar"}:
        return False

    if looks_like_note_line(line):
        return False

    word_count = len(line.split())
    return 1 <= word_count <= 6 and len(line.strip()) <= 50


def parse_reps_first_exercise_heading(line: str):
    m = re.match(r"^\s*(\d+)\s+([a-zA-Z].+?)\s*$", line)
    if not m:
        return None

    reps_hint = int(m.group(1))
    exercise_name = normalize_exercise_name(m.group(2))
    lower_name = exercise_name.lower()

    banned_starts = ("rep", "reps", "lb", "lbs", "spring", "springs", "close", "closes")
    banned_contains = ("setting", "each hand", "seconds")

    if lower_name.startswith(banned_starts):
        return None
    if any(token in lower_name for token in banned_contains):
        return None

    word_count = len(exercise_name.split())
    if word_count < 2:
        return None

    return exercise_name, reps_hint


def classify_exposure(line: str):
    text = line.strip()
    lower = text.lower()

    if "front levers" in lower:
        nums = [int(x) for x in re.findall(r"\d+", lower)]
        reps = nums[0] if nums else None
        return {
            "movement": "lever_front",
            "implement": "sword grip handle",
            "reps": reps,
            "seconds": None,
            "load": None,
            "notes": text,
        }

    if "back levers" in lower:
        nums = [int(x) for x in re.findall(r"\d+", lower)]
        reps = nums[0] if nums else None
        return {
            "movement": "lever_back",
            "implement": "sword grip handle",
            "reps": reps,
            "seconds": None,
            "load": None,
            "notes": text,
        }

    if "neutral setting" in lower and "rep" in lower:
        nums = [int(x) for x in re.findall(r"\d+", lower)]
        reps = nums[0] if nums else None
        return {
            "movement": "pronation_supination",
            "implement": "pronation device",
            "reps": reps,
            "seconds": None,
            "load": None,
            "notes": text,
        }

    if "close" in lower and "hand" in lower:
        nums = [int(x) for x in re.findall(r"\d+", lower)]
        reps = nums[0] if nums else None
        return {
            "movement": "crush_grip",
            "implement": "captains of crush",
            "reps": reps,
            "seconds": None,
            "load": None,
            "notes": text,
        }

    if "seconds" in lower:
        nums = [int(x) for x in re.findall(r"\d+", lower)]
        seconds = nums[0] if nums else None
        return {
            "movement": "extension",
            "implement": "chest expander",
            "reps": None,
            "seconds": seconds,
            "load": None,
            "notes": text,
        }

    return None


def infer_exposure_movements(exercise_name: str):
    name = exercise_name.strip().lower()

    exposure_map = {
        "bench": ["wrist_extension_stability", "elbow_extension", "support_grip"],
        "incline dumbbell": ["support_grip", "wrist_stability", "elbow_extension"],
        "hammer curls db": ["elbow_flexion", "support_grip", "radial_deviation_bias"],
        "t bar rows empty chest supported": ["support_grip", "elbow_flexion"],
        "pushups": ["wrist_extension_stability", "elbow_extension"],
        "triceps extensions ez bar": ["elbow_extension"],
        "reverse triceps extensions cable": ["elbow_extension"],
        "side deltoid raises machine": ["support_grip"],
        "machine rear deltoids": ["support_grip"],
    }

    return exposure_map.get(name, [])


def show_classification_audit() -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        SELECT DISTINCT name
        FROM exercises
        ORDER BY name
    """)
    rows = cur.fetchall()
    conn.close()

    print("\n+++ CLASSIFICATION AUDIT +++")

    if not rows:
        print("No exercises found.")
        return

    for (exercise_name,) in rows:
        movement = classify_exercise_movement(exercise_name)
        inferred = infer_exposure_movements(exercise_name)

        inferred_text = ", ".join(inferred) if inferred else "(none)"

        print(f"- {exercise_name}")
        print(f"    movement: {movement}")
        print(f"    inferred exposure: {inferred_text}")


def export_session_to_markdown(session_id: int) -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        SELECT id, date, bodyweight, notes
        FROM sessions
        WHERE id = ?
    """, (session_id,))
    session = cur.fetchone()

    if not session:
        print(f"\nSession #{session_id} not found.")
        conn.close()
        return

    session_id, date, bodyweight, notes = session

    cur.execute("""
        SELECT movement, implement, reps, seconds, load
        FROM exposures
        WHERE session_id = ?
        ORDER BY id
    """, (session_id,))
    exposures = cur.fetchall()

    cur.execute("""
        SELECT id, name
        FROM exercises
        WHERE session_id = ?
        ORDER BY id
    """, (session_id,))
    exercises = cur.fetchall()

    lines = []
    lines.append(f"# Deadlift Radio Session {session_id}")
    lines.append("")
    lines.append(f"- Date: {date}")
    lines.append(f"- Bodyweight: {bodyweight}")
    lines.append("")

    if notes:
        lines.append("## Notes")
        lines.append("")
        for line in notes.splitlines():
            lines.append(f"- {line}")
        lines.append("")

    if exposures:
        lines.append("## Exposure")
        lines.append("")
        for movement, implement, reps, seconds, load in exposures:
            parts = [movement]
            if implement:
                parts.append(f"via {implement}")
            if reps is not None:
                parts.append(f"{reps} reps")
            if seconds is not None:
                parts.append(f"{seconds} sec")
            if load is not None:
                parts.append(f"load {format_load(load)}")
            lines.append(f"- {' | '.join(parts)}")
        lines.append("")

    if exercises:
        lines.append("## Exercises")
        lines.append("")
        for ex_id, ex_name in exercises:
            lines.append(f"### {ex_name}")
            lines.append("")
            cur.execute("""
                SELECT load, reps
                FROM sets
                WHERE exercise_id = ?
                ORDER BY id
            """, (ex_id,))
            sets = cur.fetchall()

            for load, reps in sets:
                lines.append(f"- {format_load(load)} x {reps}")
            lines.append("")

    conn.close()

    safe_date = date.replace("-", "")
    output_name = f"session_{session_id}_{safe_date}.md"
    output_path = Path(output_name)
    output_path.write_text("\n".join(lines), encoding="utf-8")

    print("\n+++ SESSION MARKDOWN EXPORTED +++")
    print(f"Session ID: {session_id}")
    print(f"File: {output_path}")


def export_session_to_markdown_prompt() -> None:
    raw = input("Enter session ID to export: ").strip()
    if not raw.isdigit():
        print("Invalid session ID.")
        return
    export_session_to_markdown(int(raw))


def _generate_training_graphs_inner() -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Bench progress
    cur.execute("""
        SELECT s.date, st.load, st.reps
        FROM sets st
        JOIN exercises ex ON ex.id = st.exercise_id
        JOIN sessions s ON s.id = ex.session_id
        WHERE ex.name = 'Bench'
        ORDER BY s.date, st.id
    """)
    bench_rows = cur.fetchall()

    if bench_rows:
        dates = []
        e1rms = []
        for session_date, load, reps in bench_rows:
            dates.append(session_date)
            e1rms.append(estimate_e1rm(load, reps))

        plt.figure(figsize=(10, 5))
        plt.plot(dates, e1rms, marker='o')
        plt.title("Bench Estimated 1RM Over Time")
        plt.xlabel("Date")
        plt.ylabel("Estimated 1RM")
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig("bench_progress.png")
        plt.close()

    # Weekly tonnage
    cur.execute("""
        SELECT s.date, st.load, st.reps
        FROM sets st
        JOIN exercises ex ON ex.id = st.exercise_id
        JOIN sessions s ON s.id = ex.session_id
        ORDER BY s.date, st.id
    """)
    all_rows = cur.fetchall()

    weekly_tonnage = {}
    for session_date, load, reps in all_rows:
        dt = datetime.strptime(session_date, "%Y-%m-%d").date()
        week_start = dt - timedelta(days=dt.weekday())
        weekly_tonnage.setdefault(str(week_start), 0.0)
        weekly_tonnage[str(week_start)] += load * reps

    if weekly_tonnage:
        weeks = sorted(weekly_tonnage.keys())
        tonnages = [weekly_tonnage[w] for w in weeks]

        plt.figure(figsize=(10, 5))
        plt.bar(weeks, tonnages)
        plt.title("Weekly Tonnage")
        plt.xlabel("Week Starting")
        plt.ylabel("Tonnage")
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig("weekly_tonnage.png")
        plt.close()

    # Push vs pull balance by week
    cur.execute("""
        SELECT s.date, ex.name, st.load, st.reps
        FROM sets st
        JOIN exercises ex ON ex.id = st.exercise_id
        JOIN sessions s ON s.id = ex.session_id
        ORDER BY s.date, st.id
    """)
    movement_rows = cur.fetchall()

    weekly_push = {}
    weekly_pull = {}

    for session_date, exercise_name, load, reps in movement_rows:
        dt = datetime.strptime(session_date, "%Y-%m-%d").date()
        week_start = str(dt - timedelta(days=dt.weekday()))
        movement = classify_exercise_movement(exercise_name)

        weekly_push.setdefault(week_start, 0)
        weekly_pull.setdefault(week_start, 0)

        if movement in {"horizontal_press", "incline_press", "elbow_extension", "lateral_raise"}:
            weekly_push[week_start] += 1

        if movement in {"row", "rear_delt", "elbow_flexion"}:
            weekly_pull[week_start] += 1

    weeks = sorted(set(weekly_push.keys()) | set(weekly_pull.keys()))
    if weeks:
        push_values = [weekly_push.get(w, 0) for w in weeks]
        pull_values = [weekly_pull.get(w, 0) for w in weeks]

        x = range(len(weeks))
        width = 0.4

        plt.figure(figsize=(10, 5))
        plt.bar([i - width / 2 for i in x], push_values, width=width, label="Push")
        plt.bar([i + width / 2 for i in x], pull_values, width=width, label="Pull")
        plt.title("Weekly Push vs Pull Set Count")
        plt.xlabel("Week Starting")
        plt.ylabel("Set Count")
        plt.xticks(list(x), weeks, rotation=45)
        plt.legend()
        plt.tight_layout()
        plt.savefig("push_pull_balance.png")
        plt.close()

    conn.close()

    print("\n+++ TRAINING GRAPHS GENERATED +++")
    for name in ["bench_progress.png", "weekly_tonnage.png", "push_pull_balance.png"]:
        if Path(name).exists():
            print(f"- {name}")

def generate_training_graphs() -> None:
    run_with_grimdark_spinner("FORGING IRON RECORDS", _generate_training_graphs_inner)



def infer_session_metadata(raw_text: str, bodyweight=None, session_date=None):
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    if not lines:
        raise ValueError("Workout log was empty.")

    inferred_bw = None
    inferred_date = None

    for line in lines:
        if inferred_date is None:
            maybe_date = parse_log_date(line)
            if maybe_date is not None:
                inferred_date = maybe_date

        if inferred_bw is None:
            maybe_bw = extract_bodyweight_from_line(line)
            if maybe_bw is not None:
                inferred_bw = maybe_bw

    if bodyweight is None and inferred_bw is not None:
        bodyweight = inferred_bw

    if session_date is None:
        session_date = inferred_date or datetime.now().strftime("%Y-%m-%d")

    return lines, bodyweight, session_date


def find_sessions_by_date(session_date: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        SELECT id, date, bodyweight, notes
        FROM sessions
        WHERE date = ?
        ORDER BY id DESC
    """, (session_date,))
    rows = cur.fetchall()
    conn.close()
    return rows


def warn_if_duplicate_session_date(session_date: str) -> bool:
    matches = find_sessions_by_date(session_date)

    if not matches:
        return True

    print("\n+++ DUPLICATE DATE WARNING +++")
    print(f"Existing sessions found for {session_date}:")
    for session_id, date, bodyweight, notes in matches:
        first_note = (notes.splitlines()[0] if notes else "").strip()
        print(
            f"  #{session_id} | {date} | bw={bodyweight} | "
            f"first note: {first_note if first_note else '(none)'}"
        )

    confirm = input("Log another session for this date? (y/n): ").strip().lower()
    return confirm == "y"


def ingest_workout(raw_text: str, bodyweight=None, session_date=None) -> int:
    lines, bodyweight, session_date = infer_session_metadata(
        raw_text,
        bodyweight=bodyweight,
        session_date=session_date,
    )

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO sessions (date, bodyweight, notes) VALUES (?, ?, ?)",
        (session_date, bodyweight, "")
    )
    session_id = cur.lastrowid

    current_exercise_id = None
    session_notes = []
    current_load_hint = None
    pending_reps_hint = None

    def create_exercise(name: str):
        nonlocal current_exercise_id, current_load_hint, pending_reps_hint
        cur.execute(
            "INSERT INTO exercises (session_id, name) VALUES (?, ?)",
            (session_id, name)
        )
        current_exercise_id = cur.lastrowid
        current_load_hint = None
        pending_reps_hint = None

    def insert_exposure(exposure: dict):
        cur.execute(
            """
            INSERT INTO exposures (session_id, movement, implement, reps, seconds, load, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                exposure["movement"],
                exposure.get("implement"),
                exposure.get("reps"),
                exposure.get("seconds"),
                exposure.get("load"),
                exposure.get("notes"),
            ),
        )

    def insert_sets(parsed_sets):
        nonlocal current_load_hint, pending_reps_hint
        if current_exercise_id is None:
            for load, reps in parsed_sets:
                session_notes.append(f"Orphan set ignored: {format_load(load)} x {reps}")
            return

        for load, reps in parsed_sets:
            cur.execute(
                "INSERT INTO sets (exercise_id, load, reps, effort, pain) VALUES (?, ?, ?, ?, ?)",
                (current_exercise_id, load, reps, None, None)
            )
            current_load_hint = load

        pending_reps_hint = None

    for line in lines:
        lower_line = line.lower().strip()

        if parse_log_date(line) is not None:
            session_notes.append(line)
            continue

        if lower_line.startswith("bw") or lower_line.startswith("bodyweight"):
            session_notes.append(line)
            continue

        exposure = classify_exposure(line)
        if exposure is not None:
            insert_exposure(exposure)
            session_notes.append(line)
            continue

        if looks_like_note_line(line):
            session_notes.append(line)
            continue

        if lower_line == "bar":
            current_load_hint = 45.0
            session_notes.append("Bar")
            continue

        parsed_sets = (
            parse_standard_set_line(line)
            or parse_weight_then_reps_no_x(line)
            or parse_weight_only_line(line, pending_reps_hint)
            or parse_rep_only_line(line, current_load_hint)
        )

        if parsed_sets:
            if isinstance(parsed_sets, tuple) and parsed_sets[0] == "LOAD_HINT":
                current_load_hint = float(parsed_sets[1])
            else:
                insert_sets(parsed_sets)
            continue

        reps_first_heading = parse_reps_first_exercise_heading(line)
        if reps_first_heading:
            exercise_name, reps_hint = reps_first_heading
            create_exercise(exercise_name)
            pending_reps_hint = reps_hint
            continue

        if is_normal_exercise_heading(line):
            create_exercise(normalize_exercise_name(line))
            continue

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
    print(f"\n+++ DEADLIFT RADIO ARCHIVE ENGINE +++")
    print("Build → Record → Analyze → Ascend")
    print(f"\n=== LAST SESSION ===")
    print(f"Session ID: {session_id}")
    print(f"Date: {date}")
    print(f"Bodyweight: {bodyweight}")
    print(f"Notes: {notes if notes else '(none)'}")

    cur.execute("""
        SELECT movement, implement, reps, seconds, load, notes
        FROM exposures
        WHERE session_id = ?
        ORDER BY id
    """, (session_id,))
    exposures = cur.fetchall()

    if exposures:
        print("\n+++ FOREARM / REHAB EXPOSURE +++")
        for movement, implement, reps, seconds, load, exposure_notes in exposures:
            parts = [movement]
            if implement:
                parts.append(f"via {implement}")
            if reps is not None:
                parts.append(f"{reps} reps")
            if seconds is not None:
                parts.append(f"{seconds} sec")
            if load is not None:
                parts.append(f"load {format_load(load)}")
            print("  - " + " | ".join(parts))

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
            print(f"  {format_load(load)} x {reps}")

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

    print("\n+++ PR REGISTER +++")
    if not rows:
        print("No data yet.")
    else:
        for name, max_load in rows:
            print(f"{name}: {format_load(max_load)}")

    conn.close()


def show_last_session_summary() -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        SELECT id, date
        FROM sessions
        ORDER BY id DESC
        LIMIT 1
    """)
    session = cur.fetchone()

    if not session:
        print("\nNo sessions found.")
        conn.close()
        return

    session_id, date = session

    cur.execute("""
        SELECT e.name, s.load, s.reps
        FROM exercises e
        JOIN sets s ON s.exercise_id = e.id
        WHERE e.session_id = ?
        ORDER BY e.id, s.id
    """, (session_id,))
    rows = cur.fetchall()

    cur.execute("""
        SELECT movement, implement, reps, seconds, load
        FROM exposures
        WHERE session_id = ?
        ORDER BY id
    """, (session_id,))
    exposure_rows = cur.fetchall()

    if not rows and not exposure_rows:
        print("\n=== SESSION SUMMARY ===")
        print("No data found for last session.")
        conn.close()
        return

    per_exercise = {}
    total_sets = 0
    total_reps = 0
    total_tonnage = 0.0

    for name, load, reps in rows:
        if name not in per_exercise:
            per_exercise[name] = {
                "sets": 0,
                "reps": 0,
                "tonnage": 0.0,
                "top_set": 0.0,
            }

        per_exercise[name]["sets"] += 1
        per_exercise[name]["reps"] += reps
        per_exercise[name]["tonnage"] += load * reps
        per_exercise[name]["top_set"] = max(per_exercise[name]["top_set"], load)

        total_sets += 1
        total_reps += reps
        total_tonnage += load * reps

    best_e1rm = 0.0
    best_e1rm_exercise = None
    best_e1rm_set = None

    print("\n+++ IRON RECORD +++")
    print(f"Date: {date}")
    print(f"Total sets: {total_sets}")
    print(f"Total reps: {total_reps}")
    print(f"Total iron moved: {format_load(total_tonnage)}")

    if per_exercise:
        print("\nBy exercise:")
        for name, stats in per_exercise.items():
            exercise_rows = [(load, reps) for ex_name, load, reps in rows if ex_name == name]
            top_e1rm = 0.0
            top_e1rm_set = None

            for load, reps in exercise_rows:
                e1rm = estimate_e1rm(load, reps)
                if e1rm > top_e1rm:
                    top_e1rm = e1rm
                    top_e1rm_set = (load, reps)

                if e1rm > best_e1rm:
                    best_e1rm = e1rm
                    best_e1rm_exercise = name
                    best_e1rm_set = (load, reps)

            line = (
                f"- {name}: "
                f"{stats['sets']} sets, "
                f"{stats['reps']} reps, "
                f"top set {format_load(stats['top_set'])}, "
                f"tonnage {format_load(stats['tonnage'])}"
            )

            if top_e1rm_set is not None and top_e1rm > 0:
                line += (
                    f", best e1rm {format_load(top_e1rm)} "
                    f"from {format_load(top_e1rm_set[0])} x {top_e1rm_set[1]}"
                )

            print(line)

    if best_e1rm_set is not None and best_e1rm_exercise is not None:
        print("\nPeak strength signal:")
        print(
            f"{best_e1rm_exercise} — "
            f"{format_load(best_e1rm_set[0])} x {best_e1rm_set[1]} "
            f"-> estimated 1RM {format_load(best_e1rm)}"
        )

    if exposure_rows:
        movement_totals = {}
        print("\n+++ JOINT / TENDON EXPOSURE +++")
        for movement, implement, reps, seconds, load in exposure_rows:
            if movement not in movement_totals:
                movement_totals[movement] = {"reps": 0, "seconds": 0}
            if reps is not None:
                movement_totals[movement]["reps"] += reps
            if seconds is not None:
                movement_totals[movement]["seconds"] += seconds

            parts = [movement]
            if implement:
                parts.append(f"via {implement}")
            if reps is not None:
                parts.append(f"{reps} reps")
            if seconds is not None:
                parts.append(f"{seconds} sec")
            if load is not None:
                parts.append(f"load {format_load(load)}")
            print("  - " + " | ".join(parts))

        print("\nExposure totals by movement:")
        for movement, totals in movement_totals.items():
            bits = []
            if totals["reps"]:
                bits.append(f"{totals['reps']} reps")
            if totals["seconds"]:
                bits.append(f"{totals['seconds']} sec")
            print(f"- {movement}: " + ", ".join(bits))

    conn.close()


def show_weekly_exposure_report(days: int = 7) -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT MAX(date) FROM sessions")
    max_date_row = cur.fetchone()
    if not max_date_row or not max_date_row[0]:
        print("\nNo sessions found.")
        conn.close()
        return

    anchor_date = datetime.strptime(max_date_row[0], "%Y-%m-%d").date()
    start_date = anchor_date - timedelta(days=days - 1)

    cur.execute("""
        SELECT s.date, e.movement, e.implement, e.reps, e.seconds, e.load
        FROM exposures e
        JOIN sessions s ON s.id = e.session_id
        WHERE s.date >= ? AND s.date <= ?
        ORDER BY s.date, e.id
    """, (start_date.isoformat(), anchor_date.isoformat()))
    direct_rows = cur.fetchall()

    cur.execute("""
        SELECT s.date, ex.name, st.load, st.reps
        FROM sets st
        JOIN exercises ex ON ex.id = st.exercise_id
        JOIN sessions s ON s.id = ex.session_id
        WHERE s.date >= ? AND s.date <= ?
        ORDER BY s.date, st.id
    """, (start_date.isoformat(), anchor_date.isoformat()))
    inferred_rows = cur.fetchall()

    print("\n+++ WEEKLY JOINT / TENDON EXPOSURE +++")
    print(f"Window: {start_date.isoformat()} to {anchor_date.isoformat()}")

    if not direct_rows and not inferred_rows:
        print("No exposure data found in this window.")
        conn.close()
        return

    movement_totals = {}
    daily_totals = {}

    def ensure_bucket(session_date, movement):
        if movement not in movement_totals:
            movement_totals[movement] = {
                "reps": 0,
                "seconds": 0,
                "entries": 0,
                "sources": {"direct": 0, "inferred": 0},
            }
        if session_date not in daily_totals:
            daily_totals[session_date] = {}
        if movement not in daily_totals[session_date]:
            daily_totals[session_date][movement] = {
                "reps": 0,
                "seconds": 0,
                "entries": 0,
                "sources": {"direct": 0, "inferred": 0},
            }

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
        inferred_movements = infer_exposure_movements(exercise_name)
        for movement in inferred_movements:
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
        if totals["reps"]:
            bits.append(f"{totals['reps']} reps")
        if totals["seconds"]:
            bits.append(f"{totals['seconds']} sec")
        bits.append(f"{totals['entries']} exposures")
        source_bits = []
        if totals["sources"]["direct"]:
            source_bits.append(f"{totals['sources']['direct']} direct")
        if totals["sources"]["inferred"]:
            source_bits.append(f"{totals['sources']['inferred']} inferred")
        if source_bits:
            bits.append(", ".join(source_bits))
        print(f"- {movement}: " + ", ".join(bits))

    print("\nDaily breakdown:")
    for session_date in sorted(daily_totals.keys()):
        print(f"{session_date}")
        for movement, totals in daily_totals[session_date].items():
            bits = []
            if totals["reps"]:
                bits.append(f"{totals['reps']} reps")
            if totals["seconds"]:
                bits.append(f"{totals['seconds']} sec")
            bits.append(f"{totals['entries']} exposures")
            source_bits = []
            if totals["sources"]["direct"]:
                source_bits.append(f"{totals['sources']['direct']} direct")
            if totals["sources"]["inferred"]:
                source_bits.append(f"{totals['sources']['inferred']} inferred")
            if source_bits:
                bits.append(", ".join(source_bits))
            print(f"  - {movement}: " + ", ".join(bits))

    conn.close()


def show_weekly_strength_report(days: int = 7) -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT MAX(date) FROM sessions")
    max_date_row = cur.fetchone()
    if not max_date_row or not max_date_row[0]:
        print("\nNo sessions found.")
        conn.close()
        return

    anchor_date = datetime.strptime(max_date_row[0], "%Y-%m-%d").date()
    start_date = anchor_date - timedelta(days=days - 1)

    cur.execute("""
        SELECT s.date, ex.name, st.load, st.reps
        FROM sets st
        JOIN exercises ex ON ex.id = st.exercise_id
        JOIN sessions s ON s.id = ex.session_id
        WHERE s.date >= ? AND s.date <= ?
        ORDER BY s.date, ex.name, st.id
    """, (start_date.isoformat(), anchor_date.isoformat()))
    rows = cur.fetchall()

    print("\n+++ WEEKLY IRON REPORT +++")
    print(f"Window: {start_date.isoformat()} to {anchor_date.isoformat()}")

    if not rows:
        print("No strength data found in this window.")
        conn.close()
        return

    total_sets = 0
    total_reps = 0
    total_tonnage = 0.0
    by_exercise = {}
    daily_totals = {}

    for session_date, exercise_name, load, reps in rows:
        if exercise_name not in by_exercise:
            by_exercise[exercise_name] = {
                "sets": 0,
                "reps": 0,
                "tonnage": 0.0,
                "top_load": 0.0,
                "best_e1rm": 0.0,
                "best_set": None,
            }

        if session_date not in daily_totals:
            daily_totals[session_date] = {
                "sets": 0,
                "reps": 0,
                "tonnage": 0.0,
            }

        tonnage = load * reps
        e1rm = estimate_e1rm(load, reps)

        by_exercise[exercise_name]["sets"] += 1
        by_exercise[exercise_name]["reps"] += reps
        by_exercise[exercise_name]["tonnage"] += tonnage
        by_exercise[exercise_name]["top_load"] = max(by_exercise[exercise_name]["top_load"], load)

        if e1rm > by_exercise[exercise_name]["best_e1rm"]:
            by_exercise[exercise_name]["best_e1rm"] = e1rm
            by_exercise[exercise_name]["best_set"] = (load, reps)

        total_sets += 1
        total_reps += reps
        total_tonnage += tonnage

        daily_totals[session_date]["sets"] += 1
        daily_totals[session_date]["reps"] += reps
        daily_totals[session_date]["tonnage"] += tonnage

    peak_exercise = None
    peak_e1rm = 0.0
    peak_set = None

    for exercise_name, stats in by_exercise.items():
        if stats["best_e1rm"] > peak_e1rm:
            peak_exercise = exercise_name
            peak_e1rm = stats["best_e1rm"]
            peak_set = stats["best_set"]

    print(f"Total sets: {total_sets}")
    print(f"Total reps: {total_reps}")
    print(f"Total iron moved: {format_load(total_tonnage)}")

    print("\nBy exercise:")
    for exercise_name, stats in sorted(by_exercise.items()):
        line = (
            f"- {exercise_name}: "
            f"{stats['sets']} sets, "
            f"{stats['reps']} reps, "
            f"tonnage {format_load(stats['tonnage'])}, "
            f"top load {format_load(stats['top_load'])}"
        )

        if stats["best_set"] is not None and stats["best_e1rm"] > 0:
            load, reps = stats["best_set"]
            line += (
                f", best e1rm {format_load(stats['best_e1rm'])} "
                f"from {format_load(load)} x {reps}"
            )

        print(line)

    if peak_exercise and peak_set:
        print("\nPeak strength signal:")
        print(
            f"{peak_exercise} — "
            f"{format_load(peak_set[0])} x {peak_set[1]} "
            f"-> estimated 1RM {format_load(peak_e1rm)}"
        )

    print("\nDaily iron totals:")
    for session_date in sorted(daily_totals.keys()):
        stats = daily_totals[session_date]
        print(
            f"- {session_date}: "
            f"{stats['sets']} sets, "
            f"{stats['reps']} reps, "
            f"tonnage {format_load(stats['tonnage'])}"
        )

    conn.close()


def summarize_strength_window(start_date, end_date):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        SELECT ex.name, st.load, st.reps
        FROM sets st
        JOIN exercises ex ON ex.id = st.exercise_id
        JOIN sessions s ON s.id = ex.session_id
        WHERE s.date >= ? AND s.date <= ?
        ORDER BY ex.name, st.id
    """, (start_date.isoformat(), end_date.isoformat()))
    rows = cur.fetchall()
    conn.close()

    summary = {
        "sets": 0,
        "reps": 0,
        "tonnage": 0.0,
        "by_exercise": {},
    }

    for exercise_name, load, reps in rows:
        if exercise_name not in summary["by_exercise"]:
            summary["by_exercise"][exercise_name] = {
                "sets": 0,
                "reps": 0,
                "tonnage": 0.0,
            }

        tonnage = load * reps
        summary["sets"] += 1
        summary["reps"] += reps
        summary["tonnage"] += tonnage

        summary["by_exercise"][exercise_name]["sets"] += 1
        summary["by_exercise"][exercise_name]["reps"] += reps
        summary["by_exercise"][exercise_name]["tonnage"] += tonnage

    return summary


def percent_change(current, previous):
    if previous == 0:
        return None
    return ((current - previous) / previous) * 100.0


def show_workload_change_report(days: int = 7) -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT MAX(date) FROM sessions")
    row = cur.fetchone()
    conn.close()

    if not row or not row[0]:
        print("\nNo sessions found.")
        return

    current_end = datetime.strptime(row[0], "%Y-%m-%d").date()
    current_start = current_end - timedelta(days=days - 1)
    previous_end = current_start - timedelta(days=1)
    previous_start = previous_end - timedelta(days=days - 1)

    current = summarize_strength_window(current_start, current_end)
    previous = summarize_strength_window(previous_start, previous_end)

    print("\n+++ WORKLOAD CHANGE REPORT +++")
    print(f"Current window: {current_start} to {current_end}")
    print(f"Previous window: {previous_start} to {previous_end}")

    if current["sets"] == 0 and previous["sets"] == 0:
        print("No strength data found in either window.")
        return

    total_change = percent_change(current["tonnage"], previous["tonnage"])

    print("\nOverall:")
    print(
        f"- current: {current['sets']} sets, {current['reps']} reps, "
        f"tonnage {format_load(current['tonnage'])}"
    )
    print(
        f"- previous: {previous['sets']} sets, {previous['reps']} reps, "
        f"tonnage {format_load(previous['tonnage'])}"
    )

    if total_change is None:
        print("- total tonnage change: no prior workload to compare")
    else:
        print(f"- total tonnage change: {round(total_change, 1)}%")

    exercise_names = sorted(set(current["by_exercise"].keys()) | set(previous["by_exercise"].keys()))

    if exercise_names:
        print("\nBy exercise:")
        for exercise_name in exercise_names:
            current_stats = current["by_exercise"].get(
                exercise_name, {"sets": 0, "reps": 0, "tonnage": 0.0}
            )
            previous_stats = previous["by_exercise"].get(
                exercise_name, {"sets": 0, "reps": 0, "tonnage": 0.0}
            )

            change = percent_change(current_stats["tonnage"], previous_stats["tonnage"])

            line = (
                f"- {exercise_name}: "
                f"current {format_load(current_stats['tonnage'])} vs "
                f"previous {format_load(previous_stats['tonnage'])}"
            )

            if change is None:
                line += " | change: no prior workload"
            else:
                line += f" | change: {round(change, 1)}%"

            print(line)

    print("\nWorkload signals:")
    if total_change is None:
        print("- No previous window available for total workload comparison.")
    elif total_change >= 30:
        print("- Warning: total workload increased by 30% or more.")
    elif total_change <= -30:
        print("- Workload dropped by 30% or more.")
    else:
        print("- Total workload change is within a moderate range.")


def delete_session_by_id(session_id: int) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT id, date FROM sessions WHERE id = ?", (session_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return False

    cur.execute("DELETE FROM sets WHERE exercise_id IN (SELECT id FROM exercises WHERE session_id = ?)", (session_id,))
    cur.execute("DELETE FROM exercises WHERE session_id = ?", (session_id,))
    cur.execute("DELETE FROM exposures WHERE session_id = ?", (session_id,))
    cur.execute("DELETE FROM sessions WHERE id = ?", (session_id,))

    conn.commit()
    conn.close()
    return True


def undo_last_session() -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        SELECT id, date, bodyweight, notes
        FROM sessions
        ORDER BY id DESC
        LIMIT 1
    """)
    row = cur.fetchone()
    conn.close()

    if not row:
        print("\nNo sessions found.")
        return

    session_id, date, bodyweight, notes = row
    first_note = (notes.splitlines()[0] if notes else "").strip()

    print("\n+++ UNDO LAST LOG +++")
    print(f"Session ID: {session_id}")
    print(f"Date: {date}")
    print(f"Bodyweight: {bodyweight}")
    print(f"First note line: {first_note if first_note else '(none)'}")

    confirm = input("Type DELETE to remove this session: ").strip()
    if confirm != "DELETE":
        print("Undo cancelled.")
        return

    deleted = delete_session_by_id(session_id)
    if deleted:
        print(f"Deleted session #{session_id}.")
    else:
        print("Could not delete session.")


def show_recent_sessions(limit: int = 10) -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        SELECT id, date, bodyweight, notes
        FROM sessions
        ORDER BY id DESC
        LIMIT ?
    """, (limit,))
    rows = cur.fetchall()

    if not rows:
        print("\nNo sessions found.")
        conn.close()
        return

    print("\n+++ RECENT SESSIONS +++")
    for session_id, date, bodyweight, notes in rows:
        first_note = (notes.splitlines()[0] if notes else "").strip()
        print(
            f"#{session_id} | {date} | bw={bodyweight} | "
            f"first note: {first_note if first_note else '(none)'}"
        )

    conn.close()


def inspect_session_by_id(session_id: int) -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        SELECT id, date, bodyweight, notes
        FROM sessions
        WHERE id = ?
    """, (session_id,))
    session = cur.fetchone()

    if not session:
        print(f"\nSession #{session_id} not found.")
        conn.close()
        return

    session_id, date, bodyweight, notes = session

    print("\n+++ SESSION INSPECTOR +++")
    print(f"Session ID: {session_id}")
    print(f"Date: {date}")
    print(f"Bodyweight: {bodyweight}")
    print(f"Notes: {notes if notes else '(none)'}")

    cur.execute("""
        SELECT movement, implement, reps, seconds, load, notes
        FROM exposures
        WHERE session_id = ?
        ORDER BY id
    """, (session_id,))
    exposures = cur.fetchall()

    if exposures:
        print("\nExposure:")
        for movement, implement, reps, seconds, load, exposure_notes in exposures:
            parts = [movement]
            if implement:
                parts.append(f"via {implement}")
            if reps is not None:
                parts.append(f"{reps} reps")
            if seconds is not None:
                parts.append(f"{seconds} sec")
            if load is not None:
                parts.append(f"load {format_load(load)}")
            print("  - " + " | ".join(parts))

    cur.execute("""
        SELECT id, name
        FROM exercises
        WHERE session_id = ?
        ORDER BY id
    """, (session_id,))
    exercises = cur.fetchall()

    if exercises:
        print("\nExercises:")
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
                print(f"  {format_load(load)} x {reps}")

    if not exposures and not exercises:
        print("\nNo exercises or exposures recorded for this session.")

    conn.close()


def inspect_session_prompt() -> None:
    raw = input("Enter session ID: ").strip()
    if not raw.isdigit():
        print("Invalid session ID.")
        return
    inspect_session_by_id(int(raw))


def delete_session_prompt() -> None:
    raw = input("Enter session ID to delete: ").strip()
    if not raw.isdigit():
        print("Invalid session ID.")
        return

    session_id = int(raw)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT id, date, bodyweight, notes
        FROM sessions
        WHERE id = ?
    """, (session_id,))
    row = cur.fetchone()
    conn.close()

    if not row:
        print(f"Session #{session_id} not found.")
        return

    _, date, bodyweight, notes = row
    first_note = (notes.splitlines()[0] if notes else "").strip()

    print("\n+++ DELETE SESSION BY ID +++")
    print(f"Session ID: {session_id}")
    print(f"Date: {date}")
    print(f"Bodyweight: {bodyweight}")
    print(f"First note line: {first_note if first_note else '(none)'}")

    confirm = input("Type DELETE to remove this session: ").strip()
    if confirm != "DELETE":
        print("Delete cancelled.")
        return

    deleted = delete_session_by_id(session_id)
    if deleted:
        print(f"Deleted session #{session_id}.")
    else:
        print("Could not delete session.")


def _backup_database_inner() -> None:
    db_file = Path(DB_PATH)
    if not db_file.exists():
        print(f"\nDatabase file not found: {DB_PATH}")
        return

    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    backup_name = f"{db_file.stem}_backup_{timestamp}{db_file.suffix}"
    backup_path = db_file.parent / backup_name

    shutil.copy2(db_file, backup_path)

    print("\n+++ DATABASE BACKUP CREATED +++")
    print(f"Source: {db_file}")
    print(f"Backup: {backup_path}")

def backup_database() -> None:
    run_with_grimdark_spinner("SANCTIFYING DATA-SLATES", _backup_database_inner)



def main() -> None:
    init_db()

    print("+++ DEADLIFT RADIO ARCHIVE ENGINE +++")
    print("Build → Record → Analyze → Ascend")
    print("1) Log workout")
    print("2) Show last session")
    print("3) Show PRs")
    print("4) Show last session summary")
    print("5) Show weekly exposure report")
    print("6) Undo last log")
    print("7) Show recent sessions")
    print("8) Inspect session by ID")
    print("9) Delete session by ID")
    print("10) Show weekly strength report")
    print("11) Show weekly movement report")
    print("12) Show training balance report")
    print("13) Backup database")
    print("14) Show workload change report")
    print("15) Show classification audit")
    print("16) Export session to Markdown")
    print("17) Generate training graphs")
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
        _, inferred_bodyweight, inferred_session_date = infer_session_metadata(
            raw_text,
            bodyweight=bodyweight,
            session_date=None,
        )

        if not warn_if_duplicate_session_date(inferred_session_date):
            print("Log cancelled.")
            return

        session_id = ingest_workout(
            raw_text,
            bodyweight=inferred_bodyweight,
            session_date=inferred_session_date,
        )
        print(f"\nLogged session #{session_id}")
        show_last_session()
        show_last_session_summary()

    elif choice == "2":
        show_last_session()

    elif choice == "3":
        show_prs()

    elif choice == "4":
        show_last_session_summary()

    elif choice == "5":
        show_weekly_exposure_report()

    elif choice == "6":
        undo_last_session()

    elif choice == "7":
        show_recent_sessions()

    elif choice == "8":
        inspect_session_prompt()

    elif choice == "9":
        delete_session_prompt()

    elif choice == "10":
        show_weekly_strength_report()

    elif choice == "11":
        show_weekly_movement_report()

    elif choice == "12":
        show_training_balance_report()

    elif choice == "13":
        backup_database()

    elif choice == "14":
        show_workload_change_report()

    elif choice == "15":
        show_classification_audit()

    elif choice == "16":
        export_session_to_markdown_prompt()

    elif choice == "17":
        generate_training_graphs()

    else:
        print("Invalid choice.")


def show_weekly_movement_report(days: int = 7) -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT MAX(date) FROM sessions")
    row = cur.fetchone()

    if not row or not row[0]:
        print("\nNo sessions found.")
        conn.close()
        return

    anchor_date = datetime.strptime(row[0], "%Y-%m-%d").date()
    start_date = anchor_date - timedelta(days=days - 1)

    cur.execute("""
        SELECT s.date, ex.name, st.load, st.reps
        FROM sets st
        JOIN exercises ex ON ex.id = st.exercise_id
        JOIN sessions s ON s.id = ex.session_id
        WHERE s.date >= ? AND s.date <= ?
    """, (start_date.isoformat(), anchor_date.isoformat()))

    rows = cur.fetchall()

    print("\n+++ WEEKLY MOVEMENT REPORT +++")
    print(f"Window: {start_date} to {anchor_date}")

    movement_totals = {}

    for session_date, exercise_name, load, reps in rows:
        movement = classify_exercise_movement(exercise_name)

        if movement not in movement_totals:
            movement_totals[movement] = {
                "sets": 0,
                "reps": 0,
                "tonnage": 0
            }

        movement_totals[movement]["sets"] += 1
        movement_totals[movement]["reps"] += reps
        movement_totals[movement]["tonnage"] += load * reps

    for movement, stats in sorted(movement_totals.items()):
        print(
            f"- {movement}: "
            f"{stats['sets']} sets, "
            f"{stats['reps']} reps, "
            f"tonnage {format_load(stats['tonnage'])}"
        )

    conn.close()


def show_training_balance_report(days: int = 7) -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT MAX(date) FROM sessions")
    row = cur.fetchone()

    if not row or not row[0]:
        print("\nNo sessions found.")
        conn.close()
        return

    anchor_date = datetime.strptime(row[0], "%Y-%m-%d").date()
    start_date = anchor_date - timedelta(days=days - 1)

    cur.execute("""
        SELECT ex.name, st.load, st.reps
        FROM sets st
        JOIN exercises ex ON ex.id = st.exercise_id
        JOIN sessions s ON s.id = ex.session_id
        WHERE s.date >= ? AND s.date <= ?
    """, (start_date.isoformat(), anchor_date.isoformat()))

    rows = cur.fetchall()
    conn.close()

    print("\n+++ TRAINING BALANCE REPORT +++")
    print(f"Window: {start_date} to {anchor_date}")

    if not rows:
        print("No strength data found in this window.")
        return

    buckets = {
        "push": {"sets": 0, "reps": 0, "tonnage": 0.0},
        "pull": {"sets": 0, "reps": 0, "tonnage": 0.0},
        "arms": {"sets": 0, "reps": 0, "tonnage": 0.0},
        "shoulders": {"sets": 0, "reps": 0, "tonnage": 0.0},
    }

    for exercise_name, load, reps in rows:
        movement = classify_exercise_movement(exercise_name)
        tonnage = load * reps

        if movement in {"horizontal_press", "incline_press", "elbow_extension", "lateral_raise"}:
            buckets["push"]["sets"] += 1
            buckets["push"]["reps"] += reps
            buckets["push"]["tonnage"] += tonnage

        if movement in {"row", "rear_delt", "elbow_flexion"}:
            buckets["pull"]["sets"] += 1
            buckets["pull"]["reps"] += reps
            buckets["pull"]["tonnage"] += tonnage

        if movement in {"elbow_flexion", "elbow_extension"}:
            buckets["arms"]["sets"] += 1
            buckets["arms"]["reps"] += reps
            buckets["arms"]["tonnage"] += tonnage

        if movement in {"horizontal_press", "incline_press", "lateral_raise", "rear_delt"}:
            buckets["shoulders"]["sets"] += 1
            buckets["shoulders"]["reps"] += reps
            buckets["shoulders"]["tonnage"] += tonnage

    for bucket_name, stats in buckets.items():
        print(
            f"- {bucket_name}: "
            f"{stats['sets']} sets, "
            f"{stats['reps']} reps, "
            f"tonnage {format_load(stats['tonnage'])}"
        )

    push_sets = buckets["push"]["sets"]
    pull_sets = buckets["pull"]["sets"]

    print("\nBalance signals:")
    if push_sets > 0 and pull_sets > 0:
        ratio = push_sets / pull_sets
        print(f"- push:pull set ratio = {round(ratio, 2)}")
        if ratio > 2.0:
            print("- Warning: push volume is more than 2x pull volume.")
        elif ratio < 0.5:
            print("- Warning: pull volume is more than 2x push volume.")
        else:
            print("- Push/pull balance is within a reasonable range.")
    elif push_sets > 0 and pull_sets == 0:
        print("- Warning: push work logged with no pull work.")
    elif pull_sets > 0 and push_sets == 0:
        print("- Warning: pull work logged with no push work.")
    else:
        print("- No push or pull work found.")

if __name__ == "__main__":
    main()
