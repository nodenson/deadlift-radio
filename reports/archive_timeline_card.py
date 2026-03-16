# /home/bune/deadlift_radio/reports/archive_timeline_card.py

import os
import sys
import shutil
import base64
from datetime import datetime
from playwright.sync_api import sync_playwright

sys.path.insert(0, '/home/bune/deadlift_radio')

from analytics.timeline import build_timeline
from assets.backgrounds.loader import pick_background_for_session
from db.schema import DB_PATH

EXPORT_DIR = "/home/bune/deadlift_radio/exports"
INBOX_PATH = "/home/bune/ai_lab/inbox"

with open("/home/bune/deadlift_radio/assets/logo_transparent.png", "rb") as _f:
    LOGO_B64 = base64.b64encode(_f.read()).decode()


def get_background_base64(context):
    path = pick_background_for_session(context)
    if path and os.path.exists(path):
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""


def build_timeline_card_html(timeline, bg_b64=""):
    bg_style = f'background-image:url("data:image/png;base64,{bg_b64}");' if bg_b64 else ""
    entries = timeline.get("entries", [])

    rows_html = ""
    for e in entries:
        pr_tag = ' <span class="pr-tag">[PR]</span>' if e["pr"] else ""
        bw = f' &nbsp;·&nbsp; {e["bodyweight"]} lbs' if e["bodyweight"] else ""
        lifts = "  |  ".join(e["top_lifts"]) if e["top_lifts"] else "-"
        rows_html += f"""
        <div class="entry">
            <div class="entry-header">
                <span class="entry-date">{e["date"]}{pr_tag}</span>
                <span class="entry-bw">{bw}</span>
            </div>
            <div class="entry-stats">
                {e["total_sets"]} sets &nbsp;·&nbsp;
                {e["total_reps"]} reps &nbsp;·&nbsp;
                {e["tonnage"]:,} lbs
            </div>
            <div class="entry-lifts">{lifts}</div>
        </div>"""

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Cinzel+Decorative:wght@700&family=Cinzel:wght@400;600;700&family=Share+Tech+Mono&display=swap" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box;}}
body{{width:1080px;height:1080px;overflow:hidden;background:#000;font-family:'Cinzel',serif;}}
.card{{width:1080px;height:1080px;display:grid;grid-template-rows:80px 1fr 560px;position:relative;overflow:hidden;}}
.header{{position:relative;z-index:10;display:flex;align-items:center;justify-content:space-between;padding:0 56px;background:rgba(0,0,0,0.7);border-bottom:2px solid #8b0000;}}
.header-left{{font-family:'Share Tech Mono',monospace;font-size:22px;letter-spacing:5px;color:#cc2200;display:flex;align-items:center;gap:16px;}}
.header-right{{font-family:'Share Tech Mono',monospace;font-size:18px;letter-spacing:3px;color:#555;}}
.art-zone{{position:relative;overflow:hidden;}}
.art{{position:absolute;inset:0;{bg_style}background-size:cover;background-position:center top;background-color:#0a0a0a;}}
.art-mask{{position:absolute;inset:0;background:linear-gradient(to bottom,rgba(0,0,0,0.05) 0%,rgba(0,0,0,0.5) 60%,rgba(0,0,0,1) 100%);}}
.data-zone{{position:relative;z-index:10;display:flex;flex-direction:column;padding:20px 56px 24px 56px;gap:8px;background:rgba(0,0,0,0.65);border-top:1px solid rgba(139,0,0,0.4);overflow:hidden;}}
.timeline-label{{font-family:'Share Tech Mono',monospace;font-size:19px;letter-spacing:6px;color:#cc2200;}}
.divider{{width:100%;height:1px;background:linear-gradient(to right,rgba(139,0,0,0.6),rgba(139,0,0,0.1));margin:2px 0;}}
.entry{{padding:6px 0;border-bottom:1px solid rgba(255,255,255,0.05);}}
.entry-header{{display:flex;align-items:baseline;gap:12px;margin-bottom:3px;}}
.entry-date{{font-family:'Share Tech Mono',monospace;font-size:19px;color:#d4c9b0;letter-spacing:2px;}}
.entry-bw{{font-family:'Share Tech Mono',monospace;font-size:16px;color:#555;}}
.pr-tag{{color:#cc2200;font-size:16px;letter-spacing:2px;}}
.entry-stats{{font-family:'Share Tech Mono',monospace;font-size:16px;color:#666;margin-bottom:2px;}}
.entry-lifts{{font-family:'Share Tech Mono',monospace;font-size:15px;color:#888;}}
.footer{{font-family:'Share Tech Mono',monospace;font-size:17px;letter-spacing:4px;color:#333;text-align:center;margin-top:auto;padding-top:8px;}}
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
      <span>ARCHIVE TIMELINE</span>
    </div>
    <div class="header-right">DEADLIFT RADIO</div>
  </div>
  <div class="art-zone">
    <div class="art"></div>
    <div class="art-mask"></div>
  </div>
  <div class="data-zone">
    <div class="timeline-label">&#9632; SESSION LOG — LAST {timeline["limit"]} ENTRIES</div>
    <div class="divider"></div>
    {rows_html}
    <div class="footer">TRANSMISSION LOGGED</div>
  </div>
</div>
</body>
</html>"""


def render_archive_timeline_card(limit=5, db_path=DB_PATH):
    os.makedirs(EXPORT_DIR, exist_ok=True)
    timeline = build_timeline(limit=limit, db_path=db_path)

    if not timeline["entries"]:
        print("[timeline card] No sessions found.")
        return None

    date_slug = datetime.today().strftime("%Y-%m-%d")
    card_path = os.path.join(EXPORT_DIR, f"timeline_{date_slug}.png")

    context = {"is_summary": True}
    bg_b64 = get_background_base64(context)
    html = build_timeline_card_html(timeline, bg_b64)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1080, "height": 1080})
        page.set_content(html, wait_until="networkidle")
        page.screenshot(path=card_path, clip={"x": 0, "y": 0, "width": 1080, "height": 1080})
        browser.close()

    print(f"[timeline card] Saved -> {card_path}")

    if os.path.isdir(INBOX_PATH):
        shutil.copy2(card_path, os.path.join(INBOX_PATH, os.path.basename(card_path)))
        print(f"[delivery] -> {INBOX_PATH}")

    return card_path


if __name__ == "__main__":
    raw = input("How many sessions? (default 5): ").strip()
    limit = int(raw) if raw.isdigit() else 5
    render_archive_timeline_card(limit=limit)
