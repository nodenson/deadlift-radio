import re
from datetime import datetime


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
    return [(float(m.group(1)), int(m.group(2)))]


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


def looks_like_set_attempt(line: str) -> bool:
    text = line.strip().lower()
    if not text:
        return False
    return (
        any(ch.isdigit() for ch in text)
        or "x" in text
        or "rep" in text
        or "lb" in text
    )


def looks_like_note_line(line: str) -> bool:
    lower = line.strip().lower()
    note_starts = ("warmup", "maybe ", "front levers", "back levers", "scapular pulls")
    note_contains = ("neutral setting", "seconds", "closes each hand", "palms down", "palms up", "laying face down")
    exact_notes = {"chest expander", "forearm supination pronation device", "captains of crush sport gripper", "2 springs"}
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


def parse_reps_first_exercise_heading(line: str):
    from classification.movements import normalize_exercise_name
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
    if len(exercise_name.split()) < 2:
        return None
    return exercise_name, reps_hint


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


def classify_exposure(line: str):
    text = line.strip()
    lower = text.lower()

    if "front levers" in lower:
        nums = [int(x) for x in re.findall(r"\d+", lower)]
        return {"movement": "lever_front", "implement": "sword grip handle", "reps": nums[0] if nums else None, "seconds": None, "load": None, "notes": text}

    if "back levers" in lower:
        nums = [int(x) for x in re.findall(r"\d+", lower)]
        return {"movement": "lever_back", "implement": "sword grip handle", "reps": nums[0] if nums else None, "seconds": None, "load": None, "notes": text}

    if "neutral setting" in lower and "rep" in lower:
        nums = [int(x) for x in re.findall(r"\d+", lower)]
        return {"movement": "pronation_supination", "implement": "pronation device", "reps": nums[0] if nums else None, "seconds": None, "load": None, "notes": text}

    if "close" in lower and "hand" in lower:
        nums = [int(x) for x in re.findall(r"\d+", lower)]
        return {"movement": "crush_grip", "implement": "captains of crush", "reps": nums[0] if nums else None, "seconds": None, "load": None, "notes": text}

    if "seconds" in lower:
        nums = [int(x) for x in re.findall(r"\d+", lower)]
        return {
            "movement": "extension",
            "implement": "chest expander",
            "reps": None,
            "seconds": nums[0] if nums else None,
            "load": None,
            "notes": text,
        }

    return None