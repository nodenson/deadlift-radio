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

EXERCISE_ALIASES = {
    "incline db": "Incline dumbbell",
    "incline dumbbells": "Incline dumbbell",
    "incline db press": "Incline dumbbell",
    "hammer curls": "Hammer curls db",
    "db hammer curls": "Hammer curls db",
    "standing hammer strength hamstring mts kneeling leg curl": "Hamstring curl",
    "hamstring curl": "Hamstring curl",
    "leg curl": "Hamstring curl",
    "kneeling leg curl": "Hamstring curl",
    "rear delt machine": "Machine rear deltoids",
    "rear delts machine": "Machine rear deltoids",
    "side delt machine": "Side deltoid raises machine",
    "side delt raises machine": "Side deltoid raises machine",
    "ez bar triceps": "Triceps extensions ez bar",
    "ez bar tricep extension": "Triceps extensions ez bar",
    "t bar rows": "T bar rows empty chest supported",
}

EXPOSURE_MAP = {
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


def classify_exercise_movement(name: str) -> str:
    return EXERCISE_MOVEMENTS.get(name, "other")


def normalize_exercise_name(line: str) -> str:
    import re
    cleaned = re.sub(r"\s+", " ", line.strip())
    key = cleaned.lower()
    return EXERCISE_ALIASES.get(key, cleaned)


def infer_exposure_movements(exercise_name: str) -> list:
    return EXPOSURE_MAP.get(exercise_name.strip().lower(), [])


def show_classification_audit(db_path: str) -> None:
    import sqlite3
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT name FROM exercises ORDER BY name")
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