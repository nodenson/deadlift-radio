# /home/bune/deadlift_radio/assets/backgrounds/loader.py

import random
from pathlib import Path

BACKGROUNDS_ROOT = Path("/home/bune/deadlift_radio/assets/backgrounds")
FALLBACK = BACKGROUNDS_ROOT / "bg_01.png"

CATEGORIES = [
    "cathedral_war",
    "necron",
    "sleeper",
    "machine_priest",
    "data_hall",
    "iron_fool",
]


def get_backgrounds(category: str = None) -> list[Path]:
    if category:
        folder = BACKGROUNDS_ROOT / category
        if not folder.exists():
            return []
        return list(folder.glob("*.png"))
    
    all_files = []
    for cat in CATEGORIES:
        all_files.extend((BACKGROUNDS_ROOT / cat).glob("*.png"))
    all_files.extend(BACKGROUNDS_ROOT.glob("*.png"))
    return all_files


def pick_background(category: str = None) -> str:
    files = get_backgrounds(category)
    if not files:
        if category:
            # fall back to any category
            files = get_backgrounds()
        if not files:
            return str(FALLBACK)
    return str(random.choice(files))


def pick_background_for_session(context: dict) -> str:
    """
    context keys (all optional booleans):
        is_pr       → cathedral_war
        is_heavy    → necron
        is_recovery → sleeper
        is_summary  → data_hall
        is_satire   → iron_fool
        default     → machine_priest
    """
    if context.get("is_pr"):
        category = "cathedral_war"
    elif context.get("is_heavy"):
        category = "necron"
    elif context.get("is_recovery"):
        category = "sleeper"
    elif context.get("is_summary"):
        category = "data_hall"
    elif context.get("is_satire"):
        category = "iron_fool"
    else:
        category = "machine_priest"

    return pick_background(category)


if __name__ == "__main__":
    print("=== BACKGROUND LOADER TEST ===\n")
    print("All backgrounds:")
    for f in sorted(get_backgrounds()):
        print(f"  {f}")

    print("\nCategory picks:")
    contexts = [
        {"is_pr": True},
        {"is_heavy": True},
        {"is_recovery": True},
        {"is_summary": True},
        {"is_satire": True},
        {},
    ]
    labels = ["PR", "Heavy", "Recovery", "Summary", "Satire", "Default"]
    for label, ctx in zip(labels, contexts):
        picked = pick_background_for_session(ctx)
        print(f"  {label:12} → {Path(picked).name}")
