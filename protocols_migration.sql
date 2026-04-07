CREATE TABLE IF NOT EXISTS protocols (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    weeks INTEGER NOT NULL DEFAULT 10,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS protocol_days (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    protocol_id INTEGER NOT NULL REFERENCES protocols(id) ON DELETE CASCADE,
    week_number INTEGER NOT NULL,
    day_label TEXT NOT NULL,
    sort_order INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS prescribed_sets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    protocol_day_id INTEGER NOT NULL REFERENCES protocol_days(id) ON DELETE CASCADE,
    exercise TEXT NOT NULL,
    load_pct REAL,
    reps TEXT NOT NULL,
    sets INTEGER NOT NULL,
    rest TEXT,
    notes TEXT,
    sort_order INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS protocol_enrollments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    protocol_id INTEGER NOT NULL REFERENCES protocols(id),
    start_date TEXT NOT NULL,
    current_max REAL NOT NULL,
    active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_protocol_days_protocol ON protocol_days(protocol_id);
CREATE INDEX IF NOT EXISTS idx_prescribed_sets_day ON prescribed_sets(protocol_day_id);
CREATE INDEX IF NOT EXISTS idx_enrollments_active ON protocol_enrollments(active);
