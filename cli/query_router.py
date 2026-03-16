# /home/bune/deadlift_radio/cli/query_router.py

import sys
sys.path.insert(0, '/home/bune/deadlift_radio')

from analytics.dossier import build_exercise_dossier
from analytics.timeline import build_timeline
from analytics.movement_ledger import build_movement_ledger
from reports.exercise_dossier_cli import print_exercise_dossier
from reports.archive_timeline_cli import print_timeline
from reports.movement_ledger_cli import print_movement_ledger

# Movement keyword mapping to movement categories
# Exercise query aliases — map common query phrases to canonical exercise names
QUERY_EXERCISE_ALIASES = {
    "bench press": "Bench",
    "bench": "Bench",
    "incline": "Incline dumbbell",
    "incline press": "Incline dumbbell",
    "hammer curls": "Hammer curls db",
    "tricep extensions": "Triceps extensions ez bar",
    "triceps": "Triceps extensions ez bar",
    "rear delts": "Machine rear deltoids",
    "side delts": "Side deltoid raises machine",
    "t bar rows": "T bar rows empty chest supported",
    "reverse triceps": "reverse triceps extensions cable",
}

MOVEMENT_KEYWORDS = {
    "pressing":        ["horizontal_press", "incline_press"],
    "press":           ["horizontal_press", "incline_press"],
    "push":            ["horizontal_press", "incline_press"],
    "hinge":           ["hinge", "deadlift"],
    "deadlift":        ["hinge"],
    "squat":           ["squat"],
    "pull":            ["row", "rear_delt"],
    "row":             ["row"],
    "arms":            ["elbow_flexion", "elbow_extension"],
    "curl":            ["elbow_flexion"],
    "triceps":         ["elbow_extension"],
    "shoulder":        ["lateral_raise", "rear_delt"],
    "lateral":         ["lateral_raise"],
}

TIMELINE_TRIGGERS = {
    "timeline", "recent sessions", "archive timeline",
    "recent", "session log", "sessions",
}

PR_TRIGGERS = {
    "prs", "recent prs", "records", "pr register",
    "personal records", "bests", "best lifts",
}


def _normalize(text: str) -> str:
    return " ".join(text.strip().lower().split())


def _strip_query_prefix(text: str) -> str:
    if text.startswith("query "):
        return text[6:].strip()
    return text.strip()


def _route_movement_ledger(keyword: str) -> bool:
    """Build and print movement ledger, highlighting matched categories."""
    matched_categories = MOVEMENT_KEYWORDS.get(keyword)
    ledger = build_movement_ledger(days=30)

    if not ledger["movements"]:
        print("\n+++ ARCHIVE QUERY +++")
        print("No movement data found in archive.")
        return True

    if matched_categories:
        # Filter to requested movements only
        filtered = [m for m in ledger["movements"]
                    if m["movement"] in matched_categories]
        if filtered:
            ledger_filtered = dict(ledger)
            ledger_filtered["movements"] = filtered
            print(f"\n+++ ARCHIVE QUERY: {keyword.upper()} MOVEMENTS +++")
            print_movement_ledger(ledger_filtered)
            return True
        else:
            print(f"\n+++ ARCHIVE QUERY +++")
            print(f"No data found for movement category: {keyword}")
            print("Showing full ledger instead.")

    print_movement_ledger(ledger)
    return True


def handle_archive_query(query_text: str) -> bool:
    """
    Routes a query string to the appropriate archive report.
    Returns True if handled, False if no match found.
    """
    raw = _normalize(query_text)
    q = _strip_query_prefix(raw)

    if not q:
        print("\n[query] No input provided.")
        return False

    # Timeline
    if q in TIMELINE_TRIGGERS or any(t in q for t in TIMELINE_TRIGGERS):
        timeline = build_timeline(limit=5)
        print_timeline(timeline)
        return True

    # PR register
    if q in PR_TRIGGERS or any(t in q for t in PR_TRIGGERS):
        # Reuse menu function — import here to avoid circular
        from cli.menu import show_pr_register
        show_pr_register()
        return True

    # Exercise dossier — try the query as an exercise name first
    # (exercise lookup takes priority over movement keywords)
    # Use classification aliases for normalization
    from classification.movements import EXERCISE_MOVEMENTS, EXERCISE_ALIASES
    normalized_name = QUERY_EXERCISE_ALIASES.get(q, None)
    if normalized_name is None:
        normalized_name = EXERCISE_ALIASES.get(q, None)
    if normalized_name is None:
        # Try direct match against known exercises
        for known in EXERCISE_MOVEMENTS.keys():
            if q == known.lower() or q in known.lower():
                normalized_name = known
                break

    if normalized_name:
        dossier = build_exercise_dossier(normalized_name)
        print_exercise_dossier(dossier)
        return True

    # Last attempt — try raw query as exercise name directly
    dossier = build_exercise_dossier(q.title())
    if dossier:
        print_exercise_dossier(dossier)
        return True

    # Movement ledger — check movement keywords
    for keyword, categories in MOVEMENT_KEYWORDS.items():
        if keyword in q:
            return _route_movement_ledger(keyword)

    print(f"\n[query] No match found for: \"{q}\"")
    print("[query] Try: query bench press / query timeline / query prs / query pressing volume")
    return False


def run_query_prompt() -> None:
    print("\n+++ ARCHIVE QUERY ENGINE +++")
    print("Enter a query or type EXIT to return.")
    print("Examples: query bench press | query timeline | query prs | query pressing volume\n")
    while True:
        try:
            raw = input("query> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if raw.lower() in {"exit", "quit", "q", ""}:
            break
        handle_archive_query(raw)
        print()
