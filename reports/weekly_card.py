# /home/bune/deadlift_radio/reports/weekly_card.py

import os
import sys
import shutil
import sqlite3
import base64
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright

sys.path.insert(0, '/home/bune/deadlift_radio')
DB_PATH = os.environ.get("DLR_DB_PATH", "archive_dev.db")

from db.queries import get_recent_sessions, get_sets_in_date_range, get_tonnage_in_date_range
from assets.backgrounds.loader import pick_background_for_session

EXPORT_DIR = "/home/bune/deadlift_radio/exports"
INBOX_PATH = "/home/bune/ai_lab/inbox"
OUTPUT_PATH = "/home/bune/deadlift_radio/exports/weekly_card_latest.png"

with open("/home/bune/deadlift_radio/assets/logo_transparent.png", "rb") as _f:
    LOGO_B64 = base64.b64encode(_f.read()).decode()


def get_weekly_data(db_path=DB_PATH, days=7):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    end = datetime.today()
    start = end - timedelta(days=days)
    start_str = start.strftime("%Y-%m-%d")
    end_str = end.strftime("%Y-%m-%d")

    all_sessions = get_recent_sessions(conn, limit=50)
    week_sessions = [s for s in all_sessions if start_str <= s["date"] <= end_str]
    session_count = len(week_sessions)

    tonnage = get_tonnage_in_date_range(conn, start_str, end_str)
    sets = get_sets_in_date_range(conn, start_str, end_str)

    top_row = max(
        [r for r in sets if r["load"] and r["load"] > 0],
        key=lambda r: r["load"],
        default=None,
    )
    if top_row:
        top_exercise = top_row["name"].upper()
        top_load = int(top_row["load"]) if float(top_row["load"]).is_integer() else top_row["load"]
        top_set_str = f"{top_load} lbs x {top_row['reps']}"
    else:
        top_exercise = "N/A"
        top_set_str = "-"
        top_load = 0

    seen = set()
    exercises = []
    for r in sets:
        n = r["name"]
        if n not in seen:
            seen.add(n)
            exercises.append(n)

    start_label = start.strftime("%b %d").upper()
    end_label = end.strftime("%b %d, %Y").upper()
    date_range = f"{start_label} - {end_label}"

    conn.close()

    return {
        "date_range": date_range,
        "session_count": session_count,
        "tonnage": f"{int(tonnage):,}",
        "top_exercise": top_exercise,
        "top_set": top_set_str,
        "peak_load": str(top_load),
        "exercises": exercises,
    }


def get_background_base64(context):
    path = pick_background_for_session(context)
    if path and os.path.exists(path):
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""


def build_weekly_html(data, bg_b64):
    bg_style = f'background-image:url("data:image/png;base64,{bg_b64}");' if bg_b64 else ""
    exercise_items = "".join(
        f'<div class="ex-item">&#9632; {ex}</div>' for ex in data["exercises"]
    )

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Cinzel+Decorative:wght@700&family=Cinzel:wght@400;600;700&family=Share+Tech+Mono&display=swap" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box;}}
body{{width:1080px;height:1080px;overflow:hidden;background:#000;font-family:'Cinzel',serif;}}
.card{{width:1080px;height:1080px;display:grid;grid-template-rows:80px 1fr 440px;position:relative;overflow:hidden;}}
.header{{position:relative;z-index:10;display:flex;align-items:center;justify-content:space-between;padding:0 56px;background:rgba(0,0,0,0.7);border-bottom:2px solid #8b0000;}}
.header-left{{font-family:'Share Tech Mono',monospace;font-size:22px;letter-spacing:5px;color:#cc2200;display:flex;align-items:center;gap:16px;}}
.header-right{{font-family:'Share Tech Mono',monospace;font-size:18px;letter-spacing:3px;color:#555;}}
.art-zone{{position:relative;overflow:hidden;}}
.art{{position:absolute;inset:0;{bg_style}background-size:cover;background-position:center top;background-color:#0a0a0a;}}
.art-mask{{position:absolute;inset:0;background:linear-gradient(to bottom,rgba(0,0,0,0.05) 0%,rgba(0,0,0,0.3) 50%,rgba(0,0,0,0.92) 90%,rgba(0,0,0,1) 100%);}}
.data-zone{{position:relative;z-index:10;display:flex;flex-direction:column;align-items:flex-start;justify-content:center;padding:20px 56px 32px 56px;gap:12px;background:rgba(0,0,0,0.6);border-top:1px solid rgba(139,0,0,0.4);}}
.week-label{{font-family:'Share Tech Mono',monospace;font-size:20px;letter-spacing:6px;color:#cc2200;}}
.week-range{{font-family:'Cinzel Decorative',serif;font-size:42px;color:#e8e0d0;line-height:1;letter-spacing:2px;}}
.divider{{width:100%;height:1px;background:linear-gradient(to right,rgba(139,0,0,0.6),rgba(139,0,0,0.1));margin:4px 0;}}
.stats{{display:grid;grid-template-columns:repeat(3,1fr);width:100%;}}
.stat{{text-align:center;}}
.stat-label{{font-family:'Share Tech Mono',monospace;font-size:19px;letter-spacing:4px;color:#555;text-transform:uppercase;margin-bottom:4px;}}
.stat-value{{font-family:'Cinzel',serif;font-size:56px;color:#d4c9b0;letter-spacing:1px;}}
.stat-value.red{{color:#cc2200;}}
.top-lift-label{{font-family:'Share Tech Mono',monospace;font-size:19px;letter-spacing:5px;color:#cc2200;margin-top:4px;}}
.top-lift{{font-family:'Cinzel Decorative',serif;font-size:56px;color:#e8e0d0;line-height:1.1;}}
.top-set{{font-family:'Cinzel',serif;font-size:40px;font-weight:600;color:#cc2200;}}
.ex-grid{{display:flex;flex-wrap:wrap;gap:6px 24px;margin-top:4px;}}
.ex-item{{font-family:'Share Tech Mono',monospace;font-size:17px;color:#555;letter-spacing:2px;}}
.footer{{font-family:'Share Tech Mono',monospace;font-size:19px;letter-spacing:4px;color:#333;text-align:center;width:100%;margin-top:4px;}}
.footer::before{{content:"◆  ";}}
.footer::after{{content:"  ◆";}}
.bar-top{{position:absolute;top:0;left:0;right:0;height:5px;background:linear-gradient(to right,#6b0000,#cc2200,#6b0000);z-index:20;}}
.bar-bottom{{position:absolute;bottom:0;left:0;right:0;height:5px;background:linear-gradient(to right,#6b0000,#cc2200,#6b0000);z-index:20;}}
.corner{{position:absolute;width:36px;height:36px;border-color:rgba(180,30,30,0.5);border-style:solid;z-index:15;}}
.corner.tl{{top:90px;left:48px;border-width:2px 0 0 2px;}}
.corner.tr{{top:90px;right:48px;border-width:2px 2px 0 0;}}
</style>
</head>
<body>
<div class="card">
  <div class="bar-top"></div>
  <div class="bar-bottom"></div>
  <div class="corner tl"></div>
  <div class="corner tr"></div>
  <div class="header">
    <div class="header-left">
      <img src="data:image/png;base64,{LOGO_B64}" style="height:64px;width:64px;border-radius:50%;vertical-align:middle;"/>
      <span>WEEKLY RECORD</span>
    </div>
    <div class="header-right">DEADLIFT RADIO</div>
  </div>
  <div class="art-zone">
    <div class="art"></div>
    <div class="art-mask"></div>
  </div>
  <div class="data-zone">
    <div class="week-label">&#9632; WEEK IN REVIEW</div>
    <div class="week-range">{data['date_range']}</div>
    <div class="divider"></div>
    <div class="stats">
      <div class="stat">
        <div class="stat-label">Sessions</div>
        <div class="stat-value red">{data['session_count']}</div>
      </div>
      <div class="stat">
        <div class="stat-label">Tonnage</div>
        <div class="stat-value">{data['tonnage']} lbs</div>
      </div>
      <div class="stat">
        <div class="stat-label">Peak Load</div>
        <div class="stat-value">{data['peak_load']} lbs</div>
      </div>
    </div>
    <div class="divider"></div>
    <div class="top-lift-label">&#9632; TOP LIFT</div>
    <div class="top-lift">{data['top_exercise']}</div>
    <div class="top-set">{data['top_set']}</div>
    <div class="divider"></div>
    <div class="ex-grid">{exercise_items}</div>
    <div class="footer">TRANSMISSION LOGGED</div>
  </div>
</div>
</body>
</html>"""


def generate_weekly_card(db_path=DB_PATH, days=7):
    os.makedirs(EXPORT_DIR, exist_ok=True)
    data = get_weekly_data(db_path, days)

    end = datetime.today()
    slug = end.strftime("%Y_W%U")
    card_path = os.path.join(EXPORT_DIR, f"weekly_card_{slug}.png")
    caption_path = os.path.join(EXPORT_DIR, f"weekly_caption_{slug}.txt")

    context = {"is_summary": True}
    bg_b64 = get_background_base64(context)
    html = build_weekly_html(data, bg_b64)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1080, "height": 1080})
        page.set_content(html, wait_until="networkidle")
        page.screenshot(path=card_path, clip={"x": 0, "y": 0, "width": 1080, "height": 1080})
        browser.close()

    shutil.copy2(card_path, OUTPUT_PATH)
    print(f"[weekly card] Saved -> {card_path}")

    caption_lines = [
        f"Week of {data['date_range']}",
        f"{data['session_count']} session(s) logged",
        f"Tonnage: {data['tonnage']} lbs",
        f"Top lift: {data['top_exercise']} - {data['top_set']}",
        "",
        "Exercises: " + ", ".join(data["exercises"]),
        "",
        "#DeadliftRadio #WeeklyRecord #StrengthTraining #ArchiveEngine",
    ]
    with open(caption_path, "w") as f:
        f.write("\n".join(caption_lines))
    print(f"[weekly caption] Saved -> {caption_path}")

    if os.path.isdir(INBOX_PATH):
        shutil.copy2(card_path, os.path.join(INBOX_PATH, os.path.basename(card_path)))
        shutil.copy2(caption_path, os.path.join(INBOX_PATH, os.path.basename(caption_path)))
        print(f"[delivery] -> {INBOX_PATH}")
    else:
        print(f"[delivery] Inbox not mounted, skipping")

    return card_path


if __name__ == "__main__":
    generate_weekly_card()
