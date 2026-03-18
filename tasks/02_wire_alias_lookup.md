TASK: Wire exercise alias DB lookup into ingestion and classification

FILES: ingestion/ingest.py, classification/movements.py

PREREQUISITE: Task 01 must be complete first.

In classification/movements.py, in normalize_exercise_name():
- Add DB lookup BEFORE the existing EXERCISE_ALIASES dict lookup
- Import sqlite3 and DB_PATH
- Open connection, call lookup_exercise_alias, close connection
- If found, return canonical name
- If not found, fall through to existing logic
- Wrap in try/except so DB failures never break parsing

In ingestion/ingest.py, in create_exercise():
- After inserting the exercise, call upsert_exercise_alias
- Pass the raw line (before normalization) as alias_text
- Pass the normalized name as canonical_name
- Wrap in try/except so failures never break ingestion

RULES:
- Do not modify CLI, reports, analytics
- Do not break existing behavior
- All DB calls must be wrapped in try/except
