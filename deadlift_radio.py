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


def normalize_exercise_name(line: str) -> str:
    return re.sub(r"\s+", " ", line.strip())


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


def ingest_workout(raw_text: str, bodyweight=None, session_date=None) -> int:
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


def main() -> None:
    init_db()

    print("+++ DEADLIFT RADIO ARCHIVE ENGINE +++")
    print("Build → Record → Analyze → Ascend")
    print("1) Log workout")
    print("2) Show last session")
    print("3) Show PRs")
    print("4) Show last session summary")
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
        show_last_session_summary()

    elif choice == "2":
        show_last_session()

    elif choice == "3":
        show_prs()

    elif choice == "4":
        show_last_session_summary()

    else:
        print("Invalid choice.")


if __name__ == "__main__":
    main()
