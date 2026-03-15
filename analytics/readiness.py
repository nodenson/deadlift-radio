import datetime
import sqlite3
from db.schema import DB_PATH
from db.queries import get_all_sessions_with_exercises


def parse_session_date(value):
    try:
        return datetime.date.fromisoformat(str(value)[:10])
    except Exception:
        return None


def estimate_session_workload(session) -> int:
    return len(session.get("exercises", []))


def classify_session(session) -> str:
    names = [str(x).lower() for x in session.get("exercises", [])]
    if not names:
        return "other"
    if any("deadlift" in n for n in names):
        return "deadlift"
    if sum(1 for n in names if any(k in n for k in (
        "squat", "leg press", "leg curl", "romanian",
        "rdl", "lunge", "hamstring", "quad", "calf"
    ))) >= 2:
        return "lower"
    if any(any(k in n for k in (
        "bench", "incline", "pushup", "dip", "chest press", "triceps"
    )) for n in names):
        return "bench"
    return "upper"


def show_readiness_score() -> None:
    print("\n+++ TRAINING READINESS +++")

    conn = sqlite3.connect(DB_PATH)
    sessions = get_all_sessions_with_exercises(conn)
    conn.close()

    if not sessions:
        print("No sessions logged yet.")
        return

    today = datetime.date.today()
    current_start = today - datetime.timedelta(days=7)
    prior_start = today - datetime.timedelta(days=14)

    current_sessions = []
    prior_sessions = []

    for session in sessions:
        session_date = parse_session_date(session["date"])
        if session_date is None:
            continue
        if prior_start <= session_date < current_start:
            prior_sessions.append(session)
        elif current_start <= session_date <= today:
            current_sessions.append(session)

    if not current_sessions:
        print(f"No sessions found in current window: {current_start} to {today}")
        return

    current_load = sum(estimate_session_workload(s) for s in current_sessions)
    prior_load = sum(estimate_session_workload(s) for s in prior_sessions)

    movement_counts = {}
    for session in current_sessions:
        movement = classify_session(session)
        movement_counts[movement] = movement_counts.get(movement, 0) + 1

    signals = []
    recommendations = []
    score = 0

    if prior_load > 0:
        change_pct = ((current_load - prior_load) / prior_load) * 100
        if change_pct >= 25:
            score += 2
            signals.append(f"Workload increased {change_pct:.1f}% from prior week.")
            recommendations.append("Reduce volume or intensity today.")
        elif change_pct >= 10:
            score += 1
            signals.append(f"Workload increased {change_pct:.1f}% from prior week.")
            recommendations.append("Train, but avoid unnecessary max effort.")
        else:
            signals.append(f"Workload change is {change_pct:.1f}% from prior week.")
    else:
        signals.append("No prior workload week available yet.")

    upper_count = (
        movement_counts.get("upper", 0)
        + movement_counts.get("push", 0)
        + movement_counts.get("bench", 0)
    )
    lower_count = (
        movement_counts.get("lower", 0)
        + movement_counts.get("squat", 0)
        + movement_counts.get("deadlift", 0)
    )

    if upper_count >= 4:
        score += 1
        signals.append(f"High upper-body frequency detected ({upper_count} sessions).")
        recommendations.append("Consider back, legs, or recovery work.")
    if lower_count >= 4:
        score += 1
        signals.append(f"High lower-body frequency detected ({lower_count} sessions).")
        recommendations.append("Consider upper body or lighter movement work.")
    if len(current_sessions) >= 6:
        score += 1
        signals.append(f"High session density detected ({len(current_sessions)} sessions in 7 days).")
        recommendations.append("Consider a lighter day or full rest.")

    if score <= 0:
        status = "GREEN"
        recommendations.append("Proceed with normal training.")
    elif score <= 2:
        status = "YELLOW"
        recommendations.append("Train normally, but keep 1-2 reps in reserve.")
    else:
        status = "RED"
        recommendations.append("Strongly consider recovery, technique work, or rest.")

    print(f"\nWindow: {current_start} to {today}")
    print(f"Status: {status}")

    print("\nSignals:")
    for signal in signals:
        print(f"- {signal}")

    print("\nMovement distribution:")
    for movement, count in sorted(movement_counts.items()):
        print(f"- {movement}: {count}")

    print("\nRecommendations:")
    seen = set()
    for rec in recommendations:
        if rec not in seen:
            print(f"- {rec}")
            seen.add(rec)