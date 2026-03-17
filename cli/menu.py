from ingestion.ingest import infer_session_metadata, warn_if_duplicate_session_date, ingest_workout
import sqlite3
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from db.schema import DB_PATH
from db.queries import (
    get_last_session, get_session_by_id, get_exercises_for_session,
    get_sets_for_exercise, get_exposures_for_session, get_recent_sessions,
    get_pr_by_exercise, get_sets_in_date_range, get_max_session_date,
    delete_session_by_id, format_load, estimate_e1rm, get_tonnage_in_date_range,
    get_pr_register,
)
from reports.card import generate_session_card
from cli.query_router import run_query_prompt
from reports.movement_ledger_cli import print_movement_ledger
from reports.movement_ledger_card import render_movement_ledger_card
from analytics.movement_ledger import build_movement_ledger
from reports.archive_timeline_cli import print_timeline
from reports.archive_timeline_card import render_archive_timeline_card
from analytics.timeline import build_timeline
from reports.exercise_dossier_cli import print_exercise_dossier
from reports.exercise_dossier_card import render_exercise_dossier_card
from analytics.dossier import build_exercise_dossier
from reports.weekly_card import generate_weekly_card
from reports.graphs import generate_training_graphs
from reports.card import generate_session_card
from classification.movements import classify_exercise_movement, show_classification_audit
from utils.spinner import run_with_grimdark_spinner


def show_last_session() -> None:
    conn = sqlite3.connect(DB_PATH)
    session = get_last_session(conn)
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

    for movement, implement, reps, seconds, load, exposure_notes in get_exposures_for_session(conn, session_id):
        parts = [movement]
        if implement: parts.append(f"via {implement}")
        if reps is not None: parts.append(f"{reps} reps")
        if seconds is not None: parts.append(f"{seconds} sec")
        if load is not None: parts.append(f"load {format_load(load)}")
        print("  - " + " | ".join(parts))

    for ex_id, ex_name in get_exercises_for_session(conn, session_id):
        print(f"\n{ex_name}")
        for load, reps in get_sets_for_exercise(conn, ex_id):
            print(f"  {format_load(load)} x {reps}")

    conn.close()


def show_pr_register() -> None:
    conn = sqlite3.connect(DB_PATH)
    rows = get_pr_register(conn)
    conn.close()
    print("\n+++ PR REGISTER +++")
    if not rows:
        print("No personal records logged yet.")
        return
    current_date = None
    for date, exercise, load, reps, prev_max in rows:
        if date != current_date:
            print(f"\n{date}")
            current_date = date
        prev = f"{format_load(prev_max)} lbs" if prev_max else "first log"
        improvement = f" (+{format_load(round(load - prev_max, 1))} lbs)" if prev_max else ""
        print(f"  {exercise}: {format_load(load)} lbs x {reps}  [prev: {prev}{improvement}]")


def show_last_session_summary() -> None:
    conn = sqlite3.connect(DB_PATH)
    session = get_last_session(conn)
    if not session:
        print("\nNo sessions found.")
        conn.close()
        return

    session_id, date, *_ = session
    rows = []
    for ex_id, ex_name in get_exercises_for_session(conn, session_id):
        for load, reps in get_sets_for_exercise(conn, ex_id):
            rows.append((ex_name, load, reps))

    exposure_rows = get_exposures_for_session(conn, session_id)
    conn.close()

    if not rows and not exposure_rows:
        print("\n=== SESSION SUMMARY ===")
        print("No data found for last session.")
        return

    per_exercise = {}
    total_sets = total_reps = 0
    total_tonnage = 0.0

    for name, load, reps in rows:
        if name not in per_exercise:
            per_exercise[name] = {"sets": 0, "reps": 0, "tonnage": 0.0, "top_set": 0.0}
        per_exercise[name]["sets"] += 1
        per_exercise[name]["reps"] += reps
        per_exercise[name]["tonnage"] += load * reps
        per_exercise[name]["top_set"] = max(per_exercise[name]["top_set"], load)
        total_sets += 1
        total_reps += reps
        total_tonnage += load * reps

    print("\n+++ IRON RECORD +++")
    print(f"Date: {date}")
    print(f"Total sets: {total_sets}")
    print(f"Total reps: {total_reps}")
    print(f"Total iron moved: {format_load(total_tonnage)}")

    best_e1rm = 0.0
    best_e1rm_exercise = best_e1rm_set = None

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
            line = f"- {name}: {stats['sets']} sets, {stats['reps']} reps, top set {format_load(stats['top_set'])}, tonnage {format_load(stats['tonnage'])}"
            if top_e1rm_set and top_e1rm > 0:
                line += f", best e1rm {format_load(top_e1rm)} from {format_load(top_e1rm_set[0])} x {top_e1rm_set[1]}"
            print(line)

    if best_e1rm_set and best_e1rm_exercise:
        print(f"\nPeak strength signal:")
        print(f"{best_e1rm_exercise} — {format_load(best_e1rm_set[0])} x {best_e1rm_set[1]} -> estimated 1RM {format_load(best_e1rm)}")

    if exposure_rows:
        movement_totals = {}
        print("\n+++ JOINT / TENDON EXPOSURE +++")
        for movement, implement, reps, seconds, load, *_ in exposure_rows:
            if movement not in movement_totals:
                movement_totals[movement] = {"reps": 0, "seconds": 0}
            if reps is not None: movement_totals[movement]["reps"] += reps
            if seconds is not None: movement_totals[movement]["seconds"] += seconds
            parts = [movement]
            if implement: parts.append(f"via {implement}")
            if reps is not None: parts.append(f"{reps} reps")
            if seconds is not None: parts.append(f"{seconds} sec")
            if load is not None: parts.append(f"load {format_load(load)}")
            print("  - " + " | ".join(parts))

        print("\nExposure totals by movement:")
        for movement, totals in movement_totals.items():
            bits = []
            if totals["reps"]: bits.append(f"{totals['reps']} reps")
            if totals["seconds"]: bits.append(f"{totals['seconds']} sec")
            print(f"- {movement}: " + ", ".join(bits))


def show_prs() -> None:
    conn = sqlite3.connect(DB_PATH)
    rows = get_pr_by_exercise(conn)
    conn.close()
    print("\n+++ PR REGISTER +++")
    if not rows:
        print("No data yet.")
    else:
        for name, max_load in rows:
            print(f"{name}: {format_load(max_load)}")


def show_recent_sessions(limit: int = 10) -> None:
    conn = sqlite3.connect(DB_PATH)
    rows = get_recent_sessions(conn, limit)
    conn.close()
    if not rows:
        print("\nNo sessions found.")
        return
    print("\n+++ RECENT SESSIONS +++")
    for session_id, date, bodyweight, notes in rows:
        first_note = (notes.splitlines()[0] if notes else "").strip()
        print(f"#{session_id} | {date} | bw={bodyweight} | first note: {first_note if first_note else '(none)'}")


def inspect_session_by_id(session_id: int) -> None:
    conn = sqlite3.connect(DB_PATH)
    session = get_session_by_id(conn, session_id)
    if not session:
        print(f"\nSession #{session_id} not found.")
        conn.close()
        return

    sid, date, bodyweight, notes = session
    print("\n+++ SESSION INSPECTOR +++")
    print(f"Session ID: {sid} | Date: {date} | Bodyweight: {bodyweight}")
    print(f"Notes: {notes if notes else '(none)'}")

    exposures = get_exposures_for_session(conn, sid)
    if exposures:
        print("\nExposure:")
        for movement, implement, reps, seconds, load, *_ in exposures:
            parts = [movement]
            if implement: parts.append(f"via {implement}")
            if reps is not None: parts.append(f"{reps} reps")
            if seconds is not None: parts.append(f"{seconds} sec")
            if load is not None: parts.append(f"load {format_load(load)}")
            print("  - " + " | ".join(parts))

    exercises = get_exercises_for_session(conn, sid)
    if exercises:
        print("\nExercises:")
        for ex_id, ex_name in exercises:
            print(f"\n{ex_name}")
            for load, reps in get_sets_for_exercise(conn, ex_id):
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


def undo_last_session() -> None:
    conn = sqlite3.connect(DB_PATH)
    session = get_last_session(conn)
    conn.close()
    if not session:
        print("\nNo sessions found.")
        return

    session_id, date, bodyweight, notes = session
    first_note = (notes.splitlines()[0] if notes else "").strip()
    print(f"\n+++ UNDO LAST LOG +++")
    print(f"Session #{session_id} | {date} | bw={bodyweight} | {first_note or '(none)'}")
    confirm = input("Type DELETE to remove this session: ").strip()
    if confirm != "DELETE":
        print("Undo cancelled.")
        return

    conn = sqlite3.connect(DB_PATH)
    deleted = delete_session_by_id(conn, session_id)
    conn.close()
    print(f"Deleted session #{session_id}." if deleted else "Could not delete session.")


def delete_session_prompt() -> None:
    raw = input("Enter session ID to delete: ").strip()
    if not raw.isdigit():
        print("Invalid session ID.")
        return
    session_id = int(raw)
    conn = sqlite3.connect(DB_PATH)
    session = get_session_by_id(conn, session_id)
    conn.close()
    if not session:
        print(f"Session #{session_id} not found.")
        return

    _, date, bodyweight, notes = session
    first_note = (notes.splitlines()[0] if notes else "").strip()
    print(f"\n+++ DELETE SESSION BY ID +++")
    print(f"#{session_id} | {date} | bw={bodyweight} | {first_note or '(none)'}")
    confirm = input("Type DELETE to remove this session: ").strip()
    if confirm != "DELETE":
        print("Delete cancelled.")
        return

    conn = sqlite3.connect(DB_PATH)
    deleted = delete_session_by_id(conn, session_id)
    conn.close()
    print(f"Deleted session #{session_id}." if deleted else "Could not delete session.")


def show_weekly_movement_report(days: int = 7) -> None:
    conn = sqlite3.connect(DB_PATH)
    max_date = get_max_session_date(conn)
    if not max_date:
        print("\nNo sessions found.")
        conn.close()
        return

    anchor_date = datetime.strptime(max_date, "%Y-%m-%d").date()
    start_date = anchor_date - timedelta(days=days - 1)
    rows = get_sets_in_date_range(conn, start_date.isoformat(), anchor_date.isoformat())
    conn.close()

    print("\n+++ WEEKLY MOVEMENT REPORT +++")
    print(f"Window: {start_date} to {anchor_date}")

    movement_totals = {}
    for session_date, exercise_name, load, reps in rows:
        movement = classify_exercise_movement(exercise_name)
        if movement not in movement_totals:
            movement_totals[movement] = {"sets": 0, "reps": 0, "tonnage": 0}
        movement_totals[movement]["sets"] += 1
        movement_totals[movement]["reps"] += reps
        movement_totals[movement]["tonnage"] += load * reps

    for movement, stats in sorted(movement_totals.items()):
        print(f"- {movement}: {stats['sets']} sets, {stats['reps']} reps, tonnage {format_load(stats['tonnage'])}")


def show_training_balance_report(days: int = 7) -> None:
    conn = sqlite3.connect(DB_PATH)
    max_date = get_max_session_date(conn)
    if not max_date:
        print("\nNo sessions found.")
        conn.close()
        return

    anchor_date = datetime.strptime(max_date, "%Y-%m-%d").date()
    start_date = anchor_date - timedelta(days=days - 1)
    rows = get_sets_in_date_range(conn, start_date.isoformat(), anchor_date.isoformat())
    conn.close()

    print("\n+++ TRAINING BALANCE REPORT +++")
    print(f"Window: {start_date} to {anchor_date}")

    if not rows:
        print("No strength data found in this window.")
        return

    buckets = {
        "push":      {"sets": 0, "reps": 0, "tonnage": 0.0},
        "pull":      {"sets": 0, "reps": 0, "tonnage": 0.0},
        "arms":      {"sets": 0, "reps": 0, "tonnage": 0.0},
        "shoulders": {"sets": 0, "reps": 0, "tonnage": 0.0},
    }

    for _, exercise_name, load, reps in rows:
        movement = classify_exercise_movement(exercise_name)
        tonnage = load * reps
        if movement in {"horizontal_press", "incline_press", "elbow_extension", "lateral_raise"}:
            buckets["push"]["sets"] += 1; buckets["push"]["reps"] += reps; buckets["push"]["tonnage"] += tonnage
        if movement in {"row", "rear_delt", "elbow_flexion"}:
            buckets["pull"]["sets"] += 1; buckets["pull"]["reps"] += reps; buckets["pull"]["tonnage"] += tonnage
        if movement in {"elbow_flexion", "elbow_extension"}:
            buckets["arms"]["sets"] += 1; buckets["arms"]["reps"] += reps; buckets["arms"]["tonnage"] += tonnage
        if movement in {"horizontal_press", "incline_press", "lateral_raise", "rear_delt"}:
            buckets["shoulders"]["sets"] += 1; buckets["shoulders"]["reps"] += reps; buckets["shoulders"]["tonnage"] += tonnage

    for name, stats in buckets.items():
        print(f"- {name}: {stats['sets']} sets, {stats['reps']} reps, tonnage {format_load(stats['tonnage'])}")

    push_sets = buckets["push"]["sets"]
    pull_sets = buckets["pull"]["sets"]
    print("\nBalance signals:")
    if push_sets > 0 and pull_sets > 0:
        ratio = push_sets / pull_sets
        print(f"- push:pull set ratio = {round(ratio, 2)}")
        if ratio > 2.0: print("- Warning: push volume is more than 2x pull volume.")
        elif ratio < 0.5: print("- Warning: pull volume is more than 2x push volume.")
        else: print("- Push/pull balance is within a reasonable range.")
    elif push_sets > 0: print("- Warning: push work logged with no pull work.")
    elif pull_sets > 0: print("- Warning: pull work logged with no push work.")
    else: print("- No push or pull work found.")


def _backup_database_inner() -> None:
    db_file = Path(DB_PATH)
    if not db_file.exists():
        print(f"\nDatabase file not found: {DB_PATH}")
        return
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    backup_path = db_file.parent / f"{db_file.stem}_backup_{timestamp}{db_file.suffix}"
    shutil.copy2(db_file, backup_path)
    print(f"\n+++ DATABASE BACKUP CREATED +++")
    print(f"Backup: {backup_path}")


def backup_database() -> None:
    run_with_grimdark_spinner("SANCTIFYING DATA-SLATES", _backup_database_inner)


def run_menu() -> None:
    print("+++ DEADLIFT RADIO ARCHIVE ENGINE +++")
    print("Build → Record → Analyze → Ascend")
    print("1)  Log workout")
    print("2)  Show last session")
    print("3)  Show PRs")
    print("4)  Show last session summary")
    print("5)  Show weekly exposure report")
    print("6)  Undo last log")
    print("7)  Show recent sessions")
    print("8)  Inspect session by ID")
    print("9)  Delete session by ID")
    print("10) Show weekly strength report")
    print("11) Show weekly movement report")
    print("12) Show training balance report")
    print("13) Backup database")
    print("14) Show workload change report")
    print("15) Show classification audit")
    print("16) Export session to Markdown")
    print("17) Training graphs")
    print("18) Show fatigue analysis")
    print("19) Show readiness score")
    print("20) Generate session card")
    print("21) Generate weekly card")
    print("22) PR register")
    print("23) Show exercise dossier")
    print("24) Show archive timeline")
    print("25) Show movement ledger")
    print("26) Archive query")
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
        _, inferred_bw, inferred_date = infer_session_metadata(raw_text, bodyweight=bodyweight, session_date=None)
        if not warn_if_duplicate_session_date(inferred_date):
            print("Log cancelled.")
            return
        session_id = ingest_workout(raw_text, bodyweight=inferred_bw, session_date=inferred_date)
        print(f"\nLogged session #{session_id}")
        show_last_session()
        show_last_session_summary()
        generate_session_card()
    elif choice == "2":  show_last_session()
    elif choice == "3":  show_prs()
    elif choice == "4":  show_last_session_summary()
    elif choice == "5":  show_weekly_exposure_report()
    elif choice == "6":  undo_last_session()
    elif choice == "7":  show_recent_sessions()
    elif choice == "8":  inspect_session_prompt()
    elif choice == "9":  delete_session_prompt()
    elif choice == "10": show_weekly_strength_report()
    elif choice == "11": show_weekly_movement_report()
    elif choice == "12": show_training_balance_report()
    elif choice == "13": backup_database()
    elif choice == "14": show_workload_change_report()
    elif choice == "15": show_classification_audit(DB_PATH)
    elif choice == "16": export_session_to_markdown_prompt()
    elif choice == "17": generate_training_graphs()
    elif choice == "18": show_fatigue_analysis()
    elif choice == "19": show_readiness_score()
    elif choice == "20": generate_session_card()
    elif choice == "21": generate_weekly_card()
    elif choice == "22": show_pr_register()
    elif choice == "26": run_query_prompt()
    elif choice == "25":
        raw = input("Window in days? (default 30): ").strip()
        days = int(raw) if raw.isdigit() else 30
        ledger = build_movement_ledger(days=days)
        print_movement_ledger(ledger)
        gen = input("\nGenerate ledger card? (y/n): ").strip().lower()
        if gen == "y":
            render_movement_ledger_card(days=days)
    elif choice == "24":
        raw = input("How many sessions? (default 5): ").strip()
        limit = int(raw) if raw.isdigit() else 5
        timeline = build_timeline(limit=limit)
        print_timeline(timeline)
        gen = input("\nGenerate timeline card? (y/n): ").strip().lower()
        if gen == "y":
            render_archive_timeline_card(limit=limit)
    elif choice == "23":
        name = input("Exercise name: ").strip()
        if name:
            dossier = build_exercise_dossier(name)
            print_exercise_dossier(dossier)
            if dossier:
                gen = input("\nGenerate dossier card? (y/n): ").strip().lower()
                if gen == "y":
                    render_exercise_dossier_card(name)
        else:
            print("No exercise name entered.")
    else: print("Invalid choice.")
