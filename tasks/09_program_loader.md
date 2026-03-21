# TASK: Program Loader — Guided Training Programs

## Priority: High
## Module: programs/ (NEW)
## Status: Not started

---

## Goal
Load structured training programs into deadlift-radio so users can see
what they are supposed to do today, track completion against prescribed
work, and generate a post-session card comparing prescribed vs actual.

---

## New Files to Create

### programs/__init__.py
Empty init file.

### programs/schema.py
Add these tables to init_db():

```sql
CREATE TABLE IF NOT EXISTS programs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    source TEXT,
    created_at TEXT DEFAULT (date('now'))
);

CREATE TABLE IF NOT EXISTS program_weeks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    program_id INTEGER NOT NULL,
    week_number INTEGER NOT NULL,
    FOREIGN KEY(program_id) REFERENCES programs(id)
);

CREATE TABLE IF NOT EXISTS program_days (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    week_id INTEGER NOT NULL,
    day_number INTEGER NOT NULL,
    label TEXT,
    FOREIGN KEY(week_id) REFERENCES program_weeks(id)
);

CREATE TABLE IF NOT EXISTS prescribed_sets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    day_id INTEGER NOT NULL,
    exercise TEXT NOT NULL,
    sets INTEGER,
    reps TEXT,
    load TEXT,
    notes TEXT,
    FOREIGN KEY(day_id) REFERENCES program_days(id)
);

CREATE TABLE IF NOT EXISTS program_enrollments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    program_id INTEGER NOT NULL,
    start_date TEXT NOT NULL,
    active INTEGER DEFAULT 1,
    FOREIGN KEY(program_id) REFERENCES programs(id)
);
```

### programs/importer.py
- Function: `import_from_csv(filepath, program_name) -> int`
- Accepts a CSV exported from Google Sheets
- Expected columns: week, day, exercise, sets, reps, load, notes
- Returns program_id
- Wrap in try/except, never crash on bad rows
- Print import summary on completion

### programs/today.py
- Function: `get_todays_prescription(db_path) -> list`
- Looks up active enrollment, calculates current week/day based on start_date
- Returns list of prescribed_sets for today
- Function: `print_todays_workout()` — CLI-friendly formatted output

### programs/completion.py
- Function: `compare_session_to_program(session_id, db_path) -> dict`
- Compares actual sets logged in session against prescribed sets for that day
- Returns: prescribed count, completed count, match percentage, missing exercises
- Wrap all DB calls in try/except

---

## CLI Integration (main.py)
Add menu option:
- "View today's program" → calls print_todays_workout()
- "Import program (CSV)" → prompts for filepath, calls import_from_csv()

---

## Google Sheets Import Instructions
1. Open Joe's program in Google Sheets
2. File → Download → CSV
3. Make sure columns are: week, day, exercise, sets, reps, load, notes
4. Run: python main.py → Import program

---

## RULES
- No new dependencies (use sqlite3, csv, datetime only)
- All DB calls wrapped in try/except
- Do not modify existing sessions/exercises/sets tables
- Keep each file under 80 lines
- CLI output should be clean and readable

---

## Future
- Auto-detect current day based on enrollment start date
- Compare prescribed vs actual in post-session card
- Multi-user program assignment (ties into Warrior/Command roles in mobile app)
