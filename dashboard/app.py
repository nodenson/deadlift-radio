import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlite3
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from db.queries import get_recent_sessions, get_top_lifts_for_session, session_had_pr
from db.schema import DB_PATH

app = FastAPI()

def get_conn():
    return sqlite3.connect(DB_PATH)

@app.get("/", response_class=HTMLResponse)
def dashboard():
    conn = get_conn()
    sessions = get_recent_sessions(conn, limit=20)
    conn.close()

    rows = ""
    conn = get_conn()
    for s in sessions:
        sid, date, bw, notes = s
        pr = session_had_pr(conn, sid)
        lifts = get_top_lifts_for_session(conn, sid, top_n=3)
        lift_str = " &nbsp;|&nbsp; ".join(f"{n} {int(l)}×{r}" for n, l, r in lifts)
        pr_badge = ' <span style="color:#ff2200;font-size:10px;letter-spacing:2px;">◆ PR</span>' if pr else ''
        bw_str = f"{int(bw)} lb" if bw else "—"
        rows += f"""
        <tr onclick="location.href='/session/{sid}'" style="cursor:pointer;">
          <td style="color:#555;font-family:monospace;">#{sid}</td>
          <td>{date}{pr_badge}</td>
          <td style="color:#aaa;">{bw_str}</td>
          <td style="color:#888;font-size:12px;">{lift_str}</td>
        </tr>"""
    conn.close()

    return f"""<!DOCTYPE html>
<html>
<head>
  <title>DEADLIFT RADIO — ARCHIVE</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link href="https://fonts.googleapis.com/css2?family=Cinzel+Decorative:wght@700&family=Share+Tech+Mono&display=swap" rel="stylesheet">
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ background: #080808; color: #ccc; font-family: 'Share Tech Mono', monospace; padding: 24px; }}
    h1 {{ font-family: 'Cinzel Decorative', serif; color: #fff; font-size: 22px; letter-spacing: 4px; margin-bottom: 4px; }}
    .sub {{ color: #444; font-size: 11px; letter-spacing: 3px; margin-bottom: 32px; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th {{ text-align: left; color: #333; font-size: 10px; letter-spacing: 3px; text-transform: uppercase; padding: 8px 12px; border-bottom: 1px solid #1a1a1a; }}
    td {{ padding: 12px 12px; border-bottom: 1px solid #111; font-size: 13px; vertical-align: middle; }}
    tr:hover td {{ background: #0f0f0f; }}
  </style>
</head>
<body>
  <h1>DEADLIFT RADIO</h1>
  <div class="sub">TRANSMISSION ARCHIVE — LAST 20 SESSIONS</div>
  <table>
    <thead><tr><th>#</th><th>DATE</th><th>BW</th><th>TOP LIFTS</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
</body>
</html>"""

@app.get("/session/{session_id}", response_class=HTMLResponse)
def session_detail(session_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, date, bodyweight, notes FROM sessions WHERE id = ?", (session_id,))
    s = cur.fetchone()
    if not s:
        return HTMLResponse("<h1>Not found</h1>", status_code=404)
    sid, date, bw, notes = s

    cur.execute("""
        SELECT ex.name, MAX(st.load), st.reps, SUM(st.load * st.reps)
        FROM sets st JOIN exercises ex ON st.exercise_id = ex.id
        WHERE ex.session_id = ? GROUP BY ex.name ORDER BY MAX(st.load) DESC
    """, (sid,))
    exercises = cur.fetchall()
    conn.close()

    rows = ""
    for name, top_load, reps, tonnage in exercises:
        rows += f"<tr><td>{name}</td><td>{int(top_load)} lb × {reps}</td><td style='color:#555'>{int(tonnage or 0):,} lb</td></tr>"

    bw_str = f"{int(bw)} lb" if bw else "—"
    notes_str = f'<p style="color:#555;font-size:12px;margin-top:16px;">{notes}</p>' if notes else ""

    return f"""<!DOCTYPE html>
<html>
<head>
  <title>SESSION #{sid}</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link href="https://fonts.googleapis.com/css2?family=Cinzel+Decorative:wght@700&family=Share+Tech+Mono&display=swap" rel="stylesheet">
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ background: #080808; color: #ccc; font-family: 'Share Tech Mono', monospace; padding: 24px; }}
    h1 {{ font-family: 'Cinzel Decorative', serif; color: #fff; font-size: 18px; letter-spacing: 4px; margin-bottom: 4px; }}
    .sub {{ color: #444; font-size: 11px; letter-spacing: 2px; margin-bottom: 28px; }}
    a {{ color: #333; text-decoration: none; font-size: 11px; letter-spacing: 2px; display: block; margin-bottom: 24px; }}
    a:hover {{ color: #888; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th {{ text-align: left; color: #333; font-size: 10px; letter-spacing: 3px; text-transform: uppercase; padding: 8px 12px; border-bottom: 1px solid #1a1a1a; }}
    td {{ padding: 10px 12px; border-bottom: 1px solid #111; font-size: 13px; }}
  </style>
</head>
<body>
  <a href="/">← ARCHIVE</a>
  <h1>SESSION #{sid}</h1>
  <div class="sub">{date} &nbsp;·&nbsp; BW: {bw_str}</div>
  <table>
    <thead><tr><th>EXERCISE</th><th>TOP SET</th><th>TONNAGE</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
  {notes_str}
<div style="margin-top:32px;"><img src="/card/{sid}" onerror="this.style.display='none'" style="width:100%;max-width:540px;display:block;border:1px solid #1a1a1a;" /></div>
</body>
</html>"""

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


from fastapi.responses import FileResponse
from datetime import datetime

EXPORT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "exports")

@app.get("/card/{session_id}")
def serve_card(session_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT date FROM sessions WHERE id = ?", (session_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return HTMLResponse("Not found", status_code=404)
    date_raw = row[0]
    try:
        dated_slug = datetime.strptime(date_raw, "%Y-%m-%d").strftime("%B %d, %Y").upper().replace(" ", "_").replace(",", "")
    except Exception:
        dated_slug = date_raw
    card_path = os.path.join(EXPORT_DIR, f"session_card_{dated_slug}.png")
    if not os.path.exists(card_path):
        return HTMLResponse("No card for this session", status_code=404)
    return FileResponse(card_path, media_type="image/png")

