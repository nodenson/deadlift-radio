import sqlite3
from datetime import datetime
from db.schema import DB_PATH
from db.queries import find_sessions_by_date, format_load
from ingestion.parser import (
    parse_log_date, extract_bodyweight_from_line, parse_standard_set_line,
    parse_weight_then_reps_no_x, parse_weight_only_line, parse_rep_only_line,
    looks_like_note_line, looks_like_set_attempt, parse_reps_first_exercise_heading,
    is_normal_exercise_heading, classify_exposure,
)
from classification.movements import normalize_exercise_name


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


def warn_if_duplicate_session_date(session_date: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    matches = find_sessions_by_date(conn, session_date)
    conn.close()

    if not matches:
        return True

    print("\n+++ DUPLICATE DATE WARNING +++")
    print(f"Existing sessions found for {session_date}:")
    for session_id, date, bodyweight, notes in matches:
        first_note = (notes.splitlines()[0] if notes else "").strip()
        print(f"  #{session_id} | {date} | bw={bodyweight} | first note: {first_note if first_note else '(none)'}")

    confirm = input("Log another session for this date? (y/n): ").strip().lower()
    return confirm == "y"


def ingest_workout(raw_text: str, bodyweight=None, session_date=None) -> int:
    lines, bodyweight, session_date = infer_session_metadata(raw_text, bodyweight=bodyweight, session_date=session_date)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("INSERT INTO sessions (date, bodyweight, notes) VALUES (?, ?, ?)", (session_date, bodyweight, ""))
    session_id = cur.lastrowid

    current_exercise_id = None
    current_exercise_name = None
    session_notes = []
    current_load_hint = None
    pending_reps_hint = None

    def create_exercise(name: str):
        nonlocal current_exercise_id, current_exercise_name, current_load_hint, pending_reps_hint
        cur.execute("INSERT INTO exercises (session_id, name) VALUES (?, ?)", (session_id, name))
        current_exercise_id = cur.lastrowid
        current_exercise_name = name
        current_load_hint = None
        pending_reps_hint = None

    def insert_exposure(exposure: dict):
        cur.execute(
            "INSERT INTO exposures (session_id, movement, implement, reps, seconds, load, notes) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (session_id, exposure["movement"], exposure.get("implement"), exposure.get("reps"), exposure.get("seconds"), exposure.get("load"), exposure.get("notes")),
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

        if current_exercise_id is not None and looks_like_set_attempt(line):
            print("\n+++ LOG VALIDATION WARNING +++")
            print(f"Exercise: {current_exercise_name}")
            print(f"Line ignored: {line}")
            session_notes.append(f"Validation warning for {current_exercise_name}: ignored line: {line}")
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
    cur.execute("UPDATE sessions SET notes = ? WHERE id = ?", (final_notes, session_id))
    conn.commit()
    conn.close()
    return session_id