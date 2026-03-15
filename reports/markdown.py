import sqlite3
from pathlib import Path
from db.schema import DB_PATH
from db.queries import (
    get_session_by_id, get_exercises_for_session,
    get_sets_for_exercise, get_exposures_for_session, format_load
)


def export_session_to_markdown(session_id: int) -> None:
    conn = sqlite3.connect(DB_PATH)
    session = get_session_by_id(conn, session_id)

    if not session:
        print(f"\nSession #{session_id} not found.")
        conn.close()
        return

    sid, date, bodyweight, notes = session
    exposures = get_exposures_for_session(conn, sid)
    exercises = get_exercises_for_session(conn, sid)

    lines = [f"# Deadlift Radio Session {sid}", "", f"- Date: {date}", f"- Bodyweight: {bodyweight}", ""]

    if notes:
        lines += ["## Notes", ""]
        for line in notes.splitlines():
            lines.append(f"- {line}")
        lines.append("")

    if exposures:
        lines += ["## Exposure", ""]
        for movement, implement, reps, seconds, load, *_ in exposures:
            parts = [movement]
            if implement: parts.append(f"via {implement}")
            if reps is not None: parts.append(f"{reps} reps")
            if seconds is not None: parts.append(f"{seconds} sec")
            if load is not None: parts.append(f"load {format_load(load)}")
            lines.append(f"- {' | '.join(parts)}")
        lines.append("")

    if exercises:
        lines += ["## Exercises", ""]
        for ex_id, ex_name in exercises:
            lines.append(f"### {ex_name}")
            lines.append("")
            for load, reps in get_sets_for_exercise(conn, ex_id):
                lines.append(f"- {format_load(load)} x {reps}")
            lines.append("")

    conn.close()

    safe_date = date.replace("-", "")
    output_path = Path(f"exports/session_{sid}_{safe_date}.md")
    output_path.parent.mkdir(exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")

    print("\n+++ SESSION MARKDOWN EXPORTED +++")
    print(f"Session ID: {sid}")
    print(f"File: {output_path}")


def export_session_to_markdown_prompt() -> None:
    raw = input("Enter session ID to export: ").strip()
    if not raw.isdigit():
        print("Invalid session ID.")
        return
    export_session_to_markdown(int(raw))