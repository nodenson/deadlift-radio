from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import queries
import sqlite3
from db.schema import DB_PATH

def get_connection():
    return sqlite3.connect(DB_PATH)

app = FastAPI(title="Deadlift Radio API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _format_session(row):
    return {
        "id": row[0],
        "date": row[1],
        "bodyweight": row[2],
        "notes": row[3],
    }


def _format_session_detail(session_row, conn):
    session = _format_session(session_row)
    exercises_raw = queries.get_exercises_for_session(conn, session["id"])
    exercises = []
    for ex_id, ex_name in exercises_raw:
        sets_raw = queries.get_sets_for_exercise(conn, ex_id)
        sets = [{"load": s[0], "reps": s[1]} for s in sets_raw]
        e1rm = None
        if sets:
            best = max(sets, key=lambda s: queries.estimate_e1rm(s["load"], s["reps"]))
            e1rm = round(queries.estimate_e1rm(best["load"], best["reps"]), 1)
        exercises.append({"id": ex_id, "name": ex_name, "sets": sets, "e1rm": e1rm})
    session["exercises"] = exercises
    return session


class SetIn(BaseModel):
    load: float
    reps: int

class ExerciseIn(BaseModel):
    name: str
    sets: list[SetIn]

class SessionIn(BaseModel):
    date: str
    bodyweight: Optional[float] = None
    notes: Optional[str] = None
    exercises: list[ExerciseIn] = []


@app.get("/api/sessions")
def list_sessions(limit: int = 20):
    conn = get_connection()
    try:
        rows = queries.get_recent_sessions(conn, limit=limit)
        return [_format_session(r) for r in rows]
    finally:
        conn.close()


@app.get("/api/sessions/latest")
def latest_session():
    conn = get_connection()
    try:
        row = queries.get_last_session(conn)
        if not row:
            raise HTTPException(status_code=404, detail="No sessions found")
        return _format_session_detail(row, conn)
    finally:
        conn.close()


@app.get("/api/sessions/date/{date}")
def sessions_by_date(date: str):
    conn = get_connection()
    try:
        rows = queries.find_sessions_by_date(conn, date)
        if not rows:
            raise HTTPException(status_code=404, detail=f"No sessions for {date}")
        return [_format_session(r) for r in rows]
    finally:
        conn.close()


@app.get("/api/sessions/{session_id}")
def session_detail(session_id: int):
    conn = get_connection()
    try:
        row = queries.get_session_by_id(conn, session_id)
        if not row:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
        return _format_session_detail(row, conn)
    finally:
        conn.close()


@app.get("/api/analytics/tonnage")
def tonnage(weeks: int = 4):
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT
                strftime('%Y-W%W', s.date) AS week,
                ROUND(SUM(st.load * st.reps), 1) AS total_tonnage,
                COUNT(DISTINCT s.id) AS session_count
            FROM sessions s
            JOIN exercises e ON e.session_id = s.id
            JOIN sets st ON st.exercise_id = e.id
            WHERE s.date >= date('now', ? || ' weeks')
            GROUP BY week
            ORDER BY week ASC
        """, (f"-{weeks}",)).fetchall()
        return [{"week": r[0], "tonnage": r[1], "sessions": r[2]} for r in rows]
    finally:
        conn.close()


@app.post("/api/sessions", status_code=201)
def create_session(payload: SessionIn):
    conn = get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO sessions (date, bodyweight, notes) VALUES (?, ?, ?)",
            (payload.date, payload.bodyweight, payload.notes),
        )
        session_id = cur.lastrowid
        for ex in payload.exercises:
            ex_cur = conn.execute(
                "INSERT INTO exercises (session_id, name) VALUES (?, ?)",
                (session_id, ex.name),
            )
            ex_id = ex_cur.lastrowid
            conn.executemany(
                "INSERT INTO sets (exercise_id, load, reps) VALUES (?, ?, ?)",
                [(ex_id, s.load, s.reps) for s in ex.sets],
            )
        conn.commit()
        row = queries.get_session_by_id(conn, session_id)
        return _format_session_detail(row, conn)
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@app.get("/health")
def health():
    return {"status": "operational"}


class RawSessionIn(BaseModel):
    raw_text: str
    bodyweight: Optional[float] = None
    session_date: Optional[str] = None


@app.post("/api/log", status_code=201)
def log_raw_session(payload: RawSessionIn):
    try:
        from ingestion.ingest import ingest_workout
        session_id = ingest_workout(
            payload.raw_text,
            bodyweight=payload.bodyweight,
            session_date=payload.session_date,
        )
        conn = get_connection()
        try:
            row = queries.get_session_by_id(conn, session_id)
            return _format_session_detail(row, conn)
        finally:
            conn.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
