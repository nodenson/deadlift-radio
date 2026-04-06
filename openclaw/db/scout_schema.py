import sqlite3
import json
from pathlib import Path

SCOUT_SCHEMA = """
CREATE TABLE IF NOT EXISTS scout_runs (
    run_id       TEXT PRIMARY KEY,
    query        TEXT NOT NULL,
    provider     TEXT NOT NULL,
    generated_at TEXT NOT NULL,
    total_items  INTEGER DEFAULT 0,
    report_json  TEXT
);
CREATE TABLE IF NOT EXISTS scout_items (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id              TEXT NOT NULL,
    query               TEXT NOT NULL,
    creator_handle      TEXT NOT NULL,
    creator_name        TEXT NOT NULL,
    platform            TEXT NOT NULL,
    provider            TEXT NOT NULL,
    content_title       TEXT,
    content_url         TEXT,
    content_description TEXT,
    tags                TEXT,
    likes               INTEGER DEFAULT 0,
    comments            INTEGER DEFAULT 0,
    views               INTEGER DEFAULT 0,
    followers           INTEGER DEFAULT 0,
    published_at        TEXT,
    fetched_at          TEXT,
    score_relevance     REAL DEFAULT 0,
    score_engagement    REAL DEFAULT 0,
    score_recency       REAL DEFAULT 0,
    score_creator_fit   REAL DEFAULT 0,
    score_collab        REAL DEFAULT 0,
    score_total         REAL DEFAULT 0,
    raw_json            TEXT,
    FOREIGN KEY (run_id) REFERENCES scout_runs(run_id)
);
CREATE TABLE IF NOT EXISTS scout_creators (
    handle            TEXT NOT NULL,
    platform          TEXT NOT NULL,
    name              TEXT,
    followers         INTEGER DEFAULT 0,
    total_appearances INTEGER DEFAULT 1,
    avg_score         REAL DEFAULT 0,
    best_score        REAL DEFAULT 0,
    top_tags          TEXT,
    first_seen        TEXT,
    last_seen         TEXT,
    run_ids           TEXT,
    PRIMARY KEY (handle, platform)
);
CREATE INDEX IF NOT EXISTS idx_scout_items_run    ON scout_items(run_id);
CREATE INDEX IF NOT EXISTS idx_scout_items_handle ON scout_items(creator_handle);
CREATE INDEX IF NOT EXISTS idx_scout_items_score  ON scout_items(score_total DESC);
CREATE INDEX IF NOT EXISTS idx_scout_runs_query   ON scout_runs(query);
"""

def get_db_path():
    here = Path(__file__).resolve()
    return here.parent / "scout.db"

def get_connection(db_path=None):
    if db_path is None:
        db_path = get_db_path()
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_schema(db_path=None):
    conn = get_connection(db_path)
    conn.executescript(SCOUT_SCHEMA)
    conn.commit()
    conn.close()

def save_run(conn, run_id, query, provider, generated_at, total_items, report_json=None):
    conn.execute(
        "INSERT OR REPLACE INTO scout_runs (run_id,query,provider,generated_at,total_items,report_json) VALUES (?,?,?,?,?,?)",
        (run_id, query, provider, generated_at, total_items, report_json)
    )

def save_item(conn, run_id, query, item, scored):
    conn.execute("""
        INSERT INTO scout_items (
            run_id,query,creator_handle,creator_name,platform,provider,
            content_title,content_url,content_description,tags,
            likes,comments,views,followers,published_at,fetched_at,
            score_relevance,score_engagement,score_recency,
            score_creator_fit,score_collab,score_total,raw_json
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        run_id, query,
        item.creator_handle, item.creator_name, item.source, item.provider,
        item.content_title, item.content_url, item.content_description,
        json.dumps(item.tags),
        item.likes, item.comments, item.views, item.followers,
        item.published_at, item.fetched_at,
        scored.breakdown.relevance, scored.breakdown.engagement,
        scored.breakdown.recency, scored.breakdown.creator_fit,
        scored.breakdown.collaboration_potential, scored.total_score,
        json.dumps(item.raw)
    ))

def upsert_creator(conn, profile):
    existing = conn.execute(
        "SELECT * FROM scout_creators WHERE handle=? AND platform=?",
        (profile.handle, profile.platform)
    ).fetchone()
    if existing:
        old_ids = json.loads(existing["run_ids"] or "[]")
        merged = list(set(old_ids + profile.run_ids))
        total = existing["total_appearances"] + profile.total_appearances
        best = max(existing["best_score"], profile.best_score)
        avg = ((existing["avg_score"] * existing["total_appearances"]) +
               (profile.avg_score * profile.total_appearances)) / total
        conn.execute("""
            UPDATE scout_creators SET name=?,followers=?,total_appearances=?,avg_score=?,
            best_score=?,top_tags=?,last_seen=?,run_ids=? WHERE handle=? AND platform=?
        """, (profile.name, profile.followers, total, round(avg,4), round(best,4),
              json.dumps(profile.top_tags), profile.last_seen, json.dumps(merged),
              profile.handle, profile.platform))
    else:
        conn.execute("""
            INSERT INTO scout_creators (handle,platform,name,followers,total_appearances,
            avg_score,best_score,top_tags,first_seen,last_seen,run_ids)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (profile.handle, profile.platform, profile.name, profile.followers,
              profile.total_appearances, round(profile.avg_score,4), round(profile.best_score,4),
              json.dumps(profile.top_tags), profile.first_seen, profile.last_seen,
              json.dumps(profile.run_ids)))

def get_recent_runs(conn, limit=10):
    return conn.execute(
        "SELECT run_id,query,provider,generated_at,total_items FROM scout_runs ORDER BY generated_at DESC LIMIT ?",
        (limit,)
    ).fetchall()

def get_top_creators(conn, limit=20):
    return conn.execute(
        "SELECT handle,platform,name,followers,total_appearances,avg_score,best_score,top_tags,last_seen FROM scout_creators ORDER BY avg_score DESC, total_appearances DESC LIMIT ?",
        (limit,)
    ).fetchall()

def get_items_for_run(conn, run_id):
    return conn.execute(
        "SELECT * FROM scout_items WHERE run_id=? ORDER BY score_total DESC", (run_id,)
    ).fetchall()
