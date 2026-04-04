import requests

def generate_workout_sonnet(session_data: dict) -> str:
    date = session_data.get('date', 'Unknown')
    exercises = session_data.get('exercises', 'Unknown')
    tonnage = session_data.get('tonnage', '0')
    top_set = session_data.get('top_set', 'Unknown')
    prs = session_data.get('prs', 'None')

    prompt = (
        f"You are a grimdark poet. Write a 14-line Shakespearean sonnet "
        f"summarizing this workout. Tone: iron, suffering, glory. "
        f"Date: {date}. Exercises: {exercises}. Tonnage: {tonnage} lbs. "
        f"Top set: {top_set}. PRs: {prs}. Return only the sonnet, no preamble."
    )

    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": "llama3.2:latest", "prompt": prompt, "stream": False},
            timeout=(5, 180)
        )
        response.raise_for_status()
        return response.json().get("response", "").strip()
    except Exception:
        return (
            "In iron halls where shadows never sleep,\n"
            "The barbell calls, the plates demand their due,\n"
            "We lift the weight that mortals dare not keep,\n"
            "And forge our worth in pain, the whole day through."
        )
