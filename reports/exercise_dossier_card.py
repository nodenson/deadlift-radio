# /home/bune/deadlift_radio/reports/exercise_dossier_card.py

import os
import sys
import shutil
import base64
from datetime import datetime
from playwright.sync_api import sync_playwright

sys.path.insert(0, '/home/bune/deadlift_radio')

from analytics.dossier import build_exercise_dossier
from assets.backgrounds.loader import pick_background_for_session
from db.schema import DB_PATH

EXPORT_DIR = "/home/bune/deadlift_radio/exports"
INBOX_PATH = "/home/bune/ai_lab/inbox"

with open("/home/bune/deadlift_radio/assets/logo_transparent.png", "rb") as _f:
    LOGO_B64 = base64.b64encode(_f.read()).decode()


def fmt(n):
    if n is None:
        return "-"
    return int(n) if isinstance(n, float) and n == int(n) else round(n, 1)


def get_background_base64(context):
    path = pick_background_for_session(context)
    if path and os.path.exists(path):
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""


def build_exercise_dossier_card_html(dossier, bg_b64=""):
    bg_style = f'background-image:url("data:image/png;base64,{bg_b64}");' if bg_b64 else ""

    bs = dossier.get("best_set")
    best_set_str = f'{fmt(bs["load"])} lbs x {bs["reps"]}' if bs else "-"

    recent_rows = ""
    for r in dossier.get("recent", []):
        recent_rows += (
            f'<div class="rec-row">' +
            f'<span class="rec-date">{r["date"]}</span>' +
            f'<span class="rec-data">top {fmt(r["top_load"])} x {r["top_reps"]}' +
            f' &nbsp;|&nbsp; tonnage {fmt(r["tonnage"])}' +
            f' &nbsp;|&nbsp; e1RM {fmt(r["e1rm"])}</span>' +
            f'</div>'
        )

    status = dossier.get("status", "unknown").upper()
    status_color = {
        "RISING": "#cc2200",
        "FLAT": "#666",
        "VOLATILE": "#cc7700",
        "DORMANT": "#333",
    }.get(status, "#555")

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Cinzel+Decorative:wght@700&family=Cinzel:wght@400;600;700&family=Share+Tech+Mono&display=swap" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box;}}
body{{width:1080px;height:1080px;overflow:hidden;background:#000;font-family:'Cinzel',serif;}}
.card{{width:1080px;height:1080px;display:grid;grid-template-rows:80px 1fr 480px;position:relative;overflow:hidden;}}
.header{{position:relative;z-index:10;display:flex;align-items:center;justify-content:space-between;padding:0 56px;background:rgba(0,0,0,0.7);border-bottom:2px solid #8b0000;}}
.header-left{{font-family:'Share Tech Mono',monospace;font-size:22px;letter-spacing:5px;color:#cc2200;display:flex;align-items:center;gap:16px;}}
.header-right{{font-family:'Share Tech Mono',monospace;font-size:18px;letter-spacing:3px;color:#555;}}
.art-zone{{position:relative;overflow:hidden;}}
.art{{position:absolute;inset:0;{bg_style}background-size:cover;background-position:center top;background-color:#0a0a0a;}}
.art-mask{{position:absolute;inset:0;background:linear-gradient(to bottom,rgba(0,0,0,0.05) 0%,rgba(0,0,0,0.4) 60%,rgba(0,0,0,1) 100%);}}
.data-zone{{position:relative;z-index:10;display:flex;flex-direction:column;padding:20px 56px 28px 56px;gap:10px;background:rgba(0,0,0,0.65);border-top:1px solid rgba(139,0,0,0.4);}}
.dossier-label{{font-family:'Share Tech Mono',monospace;font-size:19px;letter-spacing:6px;color:#cc2200;}}
.exercise-name{{font-family:'Cinzel Decorative',serif;font-size:64px;color:#e8e0d0;line-height:1;letter-spacing:2px;}}
.status-tag{{font-family:'Share Tech Mono',monospace;font-size:22px;letter-spacing:6px;color:{status_color};}}
.divider{{width:100%;height:1px;background:linear-gradient(to right,rgba(139,0,0,0.6),rgba(139,0,0,0.1));margin:2px 0;}}
.stats{{display:grid;grid-template-columns:repeat(3,1fr);width:100%;}}
.stat{{text-align:center;}}
.stat-label{{font-family:'Share Tech Mono',monospace;font-size:17px;letter-spacing:3px;color:#555;margin-bottom:3px;}}
.stat-value{{font-family:'Cinzel',serif;font-size:44px;color:#d4c9b0;}}
.stat-value.red{{color:#cc2200;}}
.rec-label{{font-family:'Share Tech Mono',monospace;font-size:17px;letter-spacing:4px;color:#cc2200;margin-top:2px;}}
.rec-row{{display:flex;justify-content:space-between;align-items:baseline;}}
.rec-date{{font-family:'Share Tech Mono',monospace;font-size:16px;color:#555;min-width:110px;}}
.rec-data{{font-family:'Share Tech Mono',monospace;font-size:16px;color:#888;}}
.footer{{font-family:'Share Tech Mono',monospace;font-size:17px;letter-spacing:4px;color:#333;text-align:center;margin-top:4px;}}
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
      <span>EXERCISE DOSSIER</span>
    </div>
    <div class="header-right">DEADLIFT RADIO</div>
  </div>
  <div class="art-zone">
    <div class="art"></div>
    <div class="art-mask"></div>
  </div>
  <div class="data-zone">
    <div class="dossier-label">&#9632; ARCHIVE FILE</div>
    <div class="exercise-name">{dossier["exercise_name"]}</div>
    <div class="status-tag">STATUS: {status}</div>
    <div class="divider"></div>
    <div class="stats">
      <div class="stat">
        <div class="stat-label">Best e1RM</div>
        <div class="stat-value red">{fmt(dossier["best_e1rm"])}</div>
      </div>
      <div class="stat">
        <div class="stat-label">Best Set</div>
        <div class="stat-value">{best_set_str}</div>
      </div>
      <div class="stat">
        <div class="stat-label">Last Seen</div>
        <div class="stat-value">{dossier["last_seen"] or "-"}</div>
      </div>
    </div>
    <div class="stats" style="margin-top:4px;">
      <div class="stat">
        <div class="stat-label">30d Volume</div>
        <div class="stat-value">{fmt(dossier["volume_30d"])} lbs</div>
      </div>
      <div class="stat">
        <div class="stat-label">30d Sessions</div>
        <div class="stat-value">{dossier["appearances_30d"]}</div>
      </div>
      <div class="stat"></div>
    </div>
    <div class="divider"></div>
    <div class="rec-label">&#9632; RECENT APPEARANCES</div>
    {recent_rows}
    <div class="footer">TRANSMISSION LOGGED</div>
  </div>
</div>
</body>
</html>"""


def render_exercise_dossier_card(exercise_name, db_path=DB_PATH):
    os.makedirs(EXPORT_DIR, exist_ok=True)
    dossier = build_exercise_dossier(exercise_name, db_path)
    if not dossier:
        print(f"[dossier] No data found for: {exercise_name}")
        return None

    slug = exercise_name.lower().replace(" ", "_")
    date_slug = datetime.today().strftime("%Y-%m-%d")
    card_path = os.path.join(EXPORT_DIR, f"dossier_{slug}_{date_slug}.png")

    # Background — data_hall default, necron for heavy barbell lifts
    heavy_lifts = {"deadlift", "squat", "bench", "press", "row"}
    is_heavy = any(h in exercise_name.lower() for h in heavy_lifts)
    context = {"is_summary": not is_heavy, "is_heavy": is_heavy}
    bg_b64 = get_background_base64(context)

    html = build_exercise_dossier_card_html(dossier, bg_b64)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1080, "height": 1080})
        page.set_content(html, wait_until="networkidle")
        page.screenshot(path=card_path, clip={"x": 0, "y": 0, "width": 1080, "height": 1080})
        browser.close()

    print(f"[dossier card] Saved -> {card_path}")

    if os.path.isdir(INBOX_PATH):
        shutil.copy2(card_path, os.path.join(INBOX_PATH, os.path.basename(card_path)))
        print(f"[delivery] -> {INBOX_PATH}")

    return card_path


if __name__ == "__main__":
    name = input("Exercise name: ").strip()
    render_exercise_dossier_card(name)
