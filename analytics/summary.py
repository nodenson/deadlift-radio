import os
import random

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")


# Banned from all templates:
# forge, crucible, resolve, unyielding, emerge, stronger,
# journey, potential, victory, battle, hero, conquer, vanquish

TEMPLATES = [
    # 1 — Clinical record
    "Archive entry {date}. Operative bodyweight registered at {bodyweight} lbs. "
    "{exercise} peak load reached {peak_load} lbs across {top_set}, "
    "with a secondary volume set of {top_vol}. Total tonnage logged: {tonnage} lbs.",

    # 2 — Transmission style
    "Transmission received {date}. Subject mass: {bodyweight} lbs. "
    "Primary movement: {exercise}, top set {top_set}. "
    "{tonnage} lbs of total load displaced. Record filed.",

    # 3 — Cold procedural
    "{date}. {exercise} — {top_set}. Peak load: {peak_load} lbs. "
    "Volume set: {top_vol}. "
    "Total tonnage: {tonnage} lbs. Operative weight: {bodyweight} lbs. Logged.",

    # 4 — Machine cult ritual
    "The archive machine records {date}. "
    "{exercise} was performed to peak load {peak_load} lbs, set notation {top_set}. "
    "Cumulative iron displaced: {tonnage} lbs. The record is sealed.",

    # 5 — Intelligence report
    "Operative log {date}. Bodyweight {bodyweight} lbs. "
    "{exercise} primary lift, peak set {top_set}. "
    "Volume ceiling: {top_vol}. Session tonnage: {tonnage} lbs. Transmission complete.",

    # 6 — Sparse archival
    "{date} — {exercise}. {top_set}. "
    "{tonnage} lbs moved. Bodyweight {bodyweight} lbs. "
    "No anomalies recorded. Entry closed.",

    # 7 — Sacred industrial
    "The iron was weighed on {date}. "
    "{exercise} registered {top_set} at peak. "
    "Total displacement: {tonnage} lbs. Operative mass: {bodyweight} lbs. "
    "The machine has recorded this.",

    # 8 — Classified dossier
    "Classification: session record. Date: {date}. "
    "Primary movement {exercise}, peak load {peak_load} lbs, set {top_set}. "
    "Aggregate tonnage: {tonnage} lbs. Subject bodyweight: {bodyweight} lbs.",

    # 9 — Terse field report
    "{date}. {bodyweight} lbs on the scales. "
    "{exercise} at {top_set} — peak load {peak_load} lbs. "
    "{tonnage} lbs total. Record transmitted.",

    # 10 — Ceremonial
    "On {date} the operative reported to the archive. "
    "{exercise} was the primary instrument — {top_set} at peak load. "
    "The cumulative weight of {tonnage} lbs has been inscribed. The session is closed.",
]


def _clean(val) -> str:
    """Strip .0 from whole number floats."""
    if isinstance(val, float) and val == int(val):
        return str(int(val))
    return str(val)


def _try_ollama(prompt: str) -> str:
    import subprocess
    result = subprocess.run(
        ["ollama", "run", "llama3.2", prompt],
        capture_output=True, text=True, timeout=30
    )
    if result.returncode != 0:
        raise RuntimeError(f"Ollama error: {result.stderr}")
    return result.stdout.strip()


def _try_anthropic(prompt: str) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    message = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=256,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text.strip()


def _try_openai(prompt: str) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
        model="gpt-4o",
        max_tokens=256,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()


def _template_summary(data: dict) -> str:
    template = random.choice(TEMPLATES)
    return template.format(
        date=data.get("date", "UNKNOWN DATE"),
        bodyweight=_clean(data.get("bodyweight", "—")),
        exercise=data.get("top_set_exercise", "UNKNOWN LIFT"),
        top_set=data.get("top_set", "—"),
        peak_load=_clean(data.get("peak_load", "—")),
        top_vol=data.get("top_vol", "—"),
        tonnage=data.get("tonnage", "—"),
    )


def generate_session_summary(data: dict, force_api: bool = False) -> str:
    if force_api:
        if ANTHROPIC_API_KEY:
            try:
                from analytics.summary import _build_api_prompt
                result = _try_anthropic(_build_api_prompt(data))
                print("[summary] Generated via Anthropic")
                return result
            except Exception as e:
                print(f"[summary] Anthropic failed: {e}")

        if OPENAI_API_KEY:
            try:
                from analytics.summary import _build_api_prompt
                result = _try_openai(_build_api_prompt(data))
                print("[summary] Generated via OpenAI")
                return result
            except Exception as e:
                print(f"[summary] OpenAI failed: {e}")

    result = _template_summary(data)
    print("[summary] Generated via template engine")
    return result
