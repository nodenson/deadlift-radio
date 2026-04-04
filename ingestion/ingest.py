import sqlite3
from datetime import datetime
from db.schema import DB_PATH
from db.queries import find_sessions_by_date, format_load, upsert_exercise_alias
from ingestion.parser import (
    parse_log_date, extract_bodyweight_from_line, parse_standard_set_line,
    parse_weight_then_reps_no_x, parse_weight_only_line, parse_rep_only_line,
    looks_like_note_line, looks_like_set_attempt, parse_reps_first_exercise_heading,
    is_normal_exercise_heading, classify_exposure, parse_plate_notation,
    parse_bodyweight_set_line,
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
    pending_exposure = None
    pending_reps_hint = None
    # Auto-detect where preamble ends by finding first heading followed by a set line
    SESSION_META_WORDS = ("at ", "gym", "session", "day", "morning", "evening", "night", "legs", "push", "pull", "arms", "chest", "back", "shoulders")
    def looks_like_session_meta(l):
        low = l.lower()
        return any(w in low for w in SESSION_META_WORDS)
    first_exercise_line = None
    for i, l in enumerate(lines):
        stripped = l.split("-")[0].strip()
        if (is_normal_exercise_heading(stripped) or is_normal_exercise_heading(l)) and not looks_like_session_meta(stripped) and not classify_exposure(l):
            for j in lines[i+1:i+4]:
                if (parse_plate_notation(j) or parse_standard_set_line(j) or
                    parse_bodyweight_set_line(j) or parse_weight_then_reps_no_x(j)):
                    first_exercise_line = l
                    break
        if first_exercise_line:
            break
    in_preamble = True

    def create_exercise(name: str):
        nonlocal current_exercise_id, current_exercise_name, current_load_hint, pending_reps_hint
        cur.execute("INSERT INTO exercises (session_id, name) VALUES (?, ?)", (session_id, name))
        current_exercise_id = cur.lastrowid
        current_exercise_name = name
        current_load_hint = None
        pending_reps_hint = None
        try:
            upsert_exercise_alias(conn, alias_text=name, canonical_name=normalize_exercise_name(name))
        except Exception as e:
            print(f"Failed to upsert exercise alias: {e}")

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
            bw_sets = parse_bodyweight_set_line(line)
            if bw_sets and current_exercise_id is not None:
                bw_sets = [(bodyweight or 0.0, reps) for _, reps in bw_sets]
                insert_sets(bw_sets)
            else:
                session_notes.append(line)
            continue
        if line.startswith("#"):
            session_notes.append(line)
            continue
        stripped_early = line.split("-")[0].strip()
        if is_normal_exercise_heading(stripped_early):
            early_exposure = classify_exposure(line)
            if early_exposure is not None:
                if pending_exposure is not None:
                    insert_exposure(pending_exposure)
                if early_exposure.get("reps") is None:
                    pending_exposure = early_exposure
                else:
                    insert_exposure(early_exposure)
                    pending_exposure = None
                session_notes.append(line)
                continue
        exposure = classify_exposure(line)
        if exposure is not None:
            if pending_exposure is not None:
                insert_exposure(pending_exposure)
            if exposure.get("reps") is None:
                pending_exposure = exposure
            else:
                insert_exposure(exposure)
                pending_exposure = None
            session_notes.append(line)
            continue
        if pending_exposure is not None:
            import re as _re
            nums = [int(x) for x in _re.findall(r"\d+", line)]
            if nums and ("rep" in line.lower() or line.strip().isdigit()) and not is_normal_exercise_heading(line):
                pending_exposure["reps"] = nums[0]
                insert_exposure(pending_exposure)
                pending_exposure = None
                session_notes.append(line)
                continue
            else:
                insert_exposure(pending_exposure)
                pending_exposure = None
        if looks_like_note_line(line):
            session_notes.append(line)
            continue
        if lower_line == "bar":
            current_load_hint = 45.0
            session_notes.append("Bar")
            continue
        parsed_sets = (
            parse_plate_notation(line)
            or parse_bodyweight_set_line(line)
            or parse_standard_set_line(line)
            or parse_weight_then_reps_no_x(line)
            or parse_weight_only_line(line, pending_reps_hint)
            or parse_rep_only_line(line, current_load_hint)
        )
        if parsed_sets:
            if isinstance(parsed_sets, tuple) and parsed_sets[0] == "LOAD_HINT":
                current_load_hint = float(parsed_sets[1])
            else:
                in_preamble = False
                insert_sets(parsed_sets)
            continue
        reps_first_heading = parse_reps_first_exercise_heading(line)
        if reps_first_heading:
            exercise_name, reps_hint = reps_first_heading
            create_exercise(exercise_name)
            pending_reps_hint = reps_hint
            continue
        stripped = line.split("-")[0].strip()
        if is_normal_exercise_heading(stripped) or is_normal_exercise_heading(line):
            exposure_check = classify_exposure(line)
            if exposure_check is not None:
                if pending_exposure is not None:
                    insert_exposure(pending_exposure)
                if exposure_check.get("reps") is None:
                    pending_exposure = exposure_check
                else:
                    insert_exposure(exposure_check)
                    pending_exposure = None
                session_notes.append(line)
                continue
            if first_exercise_line and line != first_exercise_line and in_preamble:
                session_notes.append(line)
            else:
                in_preamble = False
                exercise_name_src = line if is_normal_exercise_heading(line) and not is_normal_exercise_heading(stripped) else stripped
                create_exercise(normalize_exercise_name(exercise_name_src))
            continue
        if current_exercise_id is not None and looks_like_set_attempt(line):
            print("\n+++ LOG VALIDATION WARNING +++")
            print(f"Exercise: {current_exercise_name}")
            print(f"Line ignored: {line}")
            session_notes.append(f"Validation warning for {current_exercise_name}: ignored line: {line}")
            continue
        session_notes.append(line)

    final_notes = "\n".join(session_notes).strip()
    cur.execute("UPDATE sessions SET notes = ? WHERE id = ?", (final_notes, session_id))
    conn.commit()
    conn.close()
    return session_id
