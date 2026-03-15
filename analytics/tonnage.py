import sqlite3
from datetime import datetime, timedelta
from db.schema import DB_PATH
from db.queries import format_load, estimate_e1rm, get_tonnage_in_date_range, get_sets_in_date_range, get_max_session_date


def percent_change(current, previous):
    if previous == 0:
        return None
    return ((current - previous) / previous) * 100.0


def summarize_strength_window(start_date, end_date) -> dict:
    conn = sqlite3.connect(DB_PATH)
    rows = get_sets_in_date_range(conn, start_date.isoformat(), end_date.isoformat())
    conn.close()

    summary = {"sets": 0, "reps": 0, "tonnage": 0.0, "by_exercise": {}}

    for session_date, exercise_name, load, reps in rows:
        if exercise_name not in summary["by_exercise"]:
            summary["by_exercise"][exercise_name] = {"sets": 0, "reps": 0, "tonnage": 0.0}
        tonnage = load * reps
        summary["sets"] += 1
        summary["reps"] += reps
        summary["tonnage"] += tonnage
        summary["by_exercise"][exercise_name]["sets"] += 1
        summary["by_exercise"][exercise_name]["reps"] += reps
        summary["by_exercise"][exercise_name]["tonnage"] += tonnage

    return summary


def get_current_and_previous_strength_windows(days: int = 7) -> dict:
    conn = sqlite3.connect(DB_PATH)
    max_date = get_max_session_date(conn)

    if not max_date:
        conn.close()
        return {
            "current_total_tonnage": 0.0,
            "previous_total_tonnage": 0.0,
            "current_start": None,
            "current_end": None,
            "previous_start": None,
            "previous_end": None,
        }

    end_date = datetime.strptime(max_date, "%Y-%m-%d").date()
    current_start = end_date - timedelta(days=days - 1)
    previous_end = current_start - timedelta(days=1)
    previous_start = previous_end - timedelta(days=days - 1)

    current_total = get_tonnage_in_date_range(conn, current_start.isoformat(), end_date.isoformat())
    previous_total = get_tonnage_in_date_range(conn, previous_start.isoformat(), previous_end.isoformat())
    conn.close()

    return {
        "current_total_tonnage": current_total,
        "previous_total_tonnage": previous_total,
        "current_start": current_start.isoformat(),
        "current_end": end_date.isoformat(),
        "previous_start": previous_start.isoformat(),
        "previous_end": previous_end.isoformat(),
    }


def show_workload_change_report(days: int = 7) -> None:
    conn = sqlite3.connect(DB_PATH)
    max_date = get_max_session_date(conn)
    conn.close()

    if not max_date:
        print("\nNo sessions found.")
        return

    current_end = datetime.strptime(max_date, "%Y-%m-%d").date()
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
    print(f"- current: {current['sets']} sets, {current['reps']} reps, tonnage {format_load(current['tonnage'])}")
    print(f"- previous: {previous['sets']} sets, {previous['reps']} reps, tonnage {format_load(previous['tonnage'])}")

    if total_change is None:
        print("- total tonnage change: no prior workload to compare")
    else:
        print(f"- total tonnage change: {round(total_change, 1)}%")

    exercise_names = sorted(set(current["by_exercise"].keys()) | set(previous["by_exercise"].keys()))
    if exercise_names:
        print("\nBy exercise:")
        for name in exercise_names:
            c = current["by_exercise"].get(name, {"tonnage": 0.0})
            p = previous["by_exercise"].get(name, {"tonnage": 0.0})
            change = percent_change(c["tonnage"], p["tonnage"])
            line = f"- {name}: current {format_load(c['tonnage'])} vs previous {format_load(p['tonnage'])}"
            line += " | change: no prior workload" if change is None else f" | change: {round(change, 1)}%"
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


def show_weekly_strength_report(days: int = 7) -> None:
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

    print("\n+++ WEEKLY IRON REPORT +++")
    print(f"Window: {start_date} to {anchor_date}")

    if not rows:
        print("No strength data found in this window.")
        return

    total_sets = total_reps = 0
    total_tonnage = 0.0
    by_exercise = {}
    daily_totals = {}

    for session_date, exercise_name, load, reps in rows:
        if exercise_name not in by_exercise:
            by_exercise[exercise_name] = {"sets": 0, "reps": 0, "tonnage": 0.0, "top_load": 0.0, "best_e1rm": 0.0, "best_set": None}
        if session_date not in daily_totals:
            daily_totals[session_date] = {"sets": 0, "reps": 0, "tonnage": 0.0}

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

    peak_exercise = peak_e1rm = None
    peak_set = None
    for name, stats in by_exercise.items():
        if stats["best_e1rm"] > (peak_e1rm or 0):
            peak_exercise, peak_e1rm, peak_set = name, stats["best_e1rm"], stats["best_set"]

    print(f"Total sets: {total_sets}")
    print(f"Total reps: {total_reps}")
    print(f"Total iron moved: {format_load(total_tonnage)}")

    print("\nBy exercise:")
    for name, stats in sorted(by_exercise.items()):
        line = f"- {name}: {stats['sets']} sets, {stats['reps']} reps, tonnage {format_load(stats['tonnage'])}, top load {format_load(stats['top_load'])}"
        if stats["best_set"] and stats["best_e1rm"] > 0:
            line += f", best e1rm {format_load(stats['best_e1rm'])} from {format_load(stats['best_set'][0])} x {stats['best_set'][1]}"
        print(line)

    if peak_exercise and peak_set:
        print(f"\nPeak strength signal:")
        print(f"{peak_exercise} — {format_load(peak_set[0])} x {peak_set[1]} -> estimated 1RM {format_load(peak_e1rm)}")

    print("\nDaily iron totals:")
    for d in sorted(daily_totals.keys()):
        s = daily_totals[d]
        print(f"- {d}: {s['sets']} sets, {s['reps']} reps, tonnage {format_load(s['tonnage'])}")