import json
from groq import Groq, RateLimitError
from ..db.scout_schema import get_connection, get_db_path, get_recent_runs, get_items_for_run
from ..config.personas import FALLBACK_CHAIN, build_system_prompt, build_user_prompt


def load_latest_run(db_path=None):
    conn = get_connection(db_path)
    try:
        runs = get_recent_runs(conn, limit=1)
        if not runs:
            return None, None
        run = runs[0]
        items = get_items_for_run(conn, run["run_id"])
        return dict(run), [dict(i) for i in items]
    finally:
        conn.close()


def build_data_payload(run, items):
    top = items[:10]
    lines = []
    lines.append(f"Query: {run['query']}")
    lines.append(f"Run: {run['run_id']}")
    lines.append(f"Total items: {run['total_items']}")
    lines.append("")
    lines.append("TOP SCORED CREATORS:")
    for i, item in enumerate(top, 1):
        tags = item["tags"]
        if isinstance(tags, str):
            try:
                tags = json.loads(tags)
            except Exception:
                tags = [tags]
        lines.append(
            f"  {i}. {item['creator_name']} ({item['platform']}) | "
            f"score: {item['score_total']:.2f} | "
            f"{item['followers']:,} followers | "
            f"tags: {', '.join(tags[:4])} | "
            f"\"{item['content_title']}\""
        )
    return "\n".join(lines)


def call_with_fallback(client, persona_name, task_name, data_payload, force_persona=False):
    """
    Try models in fallback chain.
    If force_persona is True, use only the persona's assigned model then fail.
    If False, fall through chain but keep the original persona's voice.
    """
    from ..config.personas import PERSONAS, get_persona

    if force_persona:
        persona = get_persona(persona_name)
        chain = [(persona["model"], persona_name)]
    else:
        # Start from requested persona's position in chain
        model_names = [m for m, _ in FALLBACK_CHAIN]
        persona_model = PERSONAS[persona_name]["model"]
        try:
            start = model_names.index(persona_model)
        except ValueError:
            start = 0
        # Use original persona's voice throughout fallback
        chain = [(model, persona_name) for model, _ in FALLBACK_CHAIN[start:]]

    system_prompt = build_system_prompt(persona_name)
    user_prompt = build_user_prompt(task_name, data_payload)

    for model, active_persona in chain:
        try:
            print(f"[openclaw] model: {model} | persona: {active_persona.upper()}")
            response = client.chat.completions.create(
                model=model,
                max_tokens=1500,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ]
            )
            return response.choices[0].message.content, model, active_persona
        except RateLimitError:
            print(f"[openclaw] rate limited on {model}, trying next...")
            continue
        except Exception as e:
            print(f"[openclaw] error on {model}: {e}, trying next...")
            continue

    raise RuntimeError("All models failed. Check GROQ_API_KEY and rate limits.")


def generate_brief(db_path=None, run_id=None, persona_name="archivist", task_name=None):
    if run_id:
        db_path = db_path or get_db_path()
        conn = get_connection(db_path)
        try:
            items = get_items_for_run(conn, run_id)
            run = {
                "run_id": run_id,
                "query": items[0]["query"] if items else "",
                "total_items": len(items)
            }
            items = [dict(i) for i in items]
        finally:
            conn.close()
    else:
        run, items = load_latest_run(db_path)
        if not run:
            print("No scout runs found. Run a scout first.")
            return

    print(f"[openclaw] run:     {run['run_id']}")
    print(f"[openclaw] query:   {run['query']}")
    print(f"[openclaw] items:   {len(items)}")
    if task_name is None:
        task_name = "furnace" if persona_name == "furnace" else "brief"
    print(f"[openclaw] persona: {persona_name.upper()}")
    print()

    client = Groq()
    data_payload = build_data_payload(run, items)
    output, model_used, persona_used = call_with_fallback(
        client, persona_name, task_name, data_payload
    )

    from ..config.personas import PERSONAS
    persona_label = PERSONAS[persona_used]["name"]

    print("=" * 60)
    print(f"DEADLIFT RADIO — {persona_label}")
    print(f"Run:    {run['run_id']}")
    print(f"Query:  {run['query']}")
    print(f"Model:  {model_used}")
    print("=" * 60)
    print()
    print(output)
    print()
    print("=" * 60)
