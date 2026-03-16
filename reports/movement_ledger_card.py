# /home/bune/deadlift_radio/reports/movement_ledger_card.py

import os
import sys
import shutil
import base64
from datetime import datetime
from playwright.sync_api import sync_playwright

sys.path.insert(0, '/home/bune/deadlift_radio')

from analytics.movement_ledger import build_movement_ledger
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


def build_movement_ledger_card_html(ledger, bg_b64=""):
    bg_style = f'background-image:url("data:image/png;base64,{bg_b64}");' if bg_b64 else ""
    movements = ledger.get("movements", [])

    rows_html = ""
    for m in movements:
        label = m["movement"].replace("_", " ").upper()
        exes = ", ".join(m["top_exercises"]) if m["top_exercises"] else "-"
        bar_width = max(4, int(m["share"]))
        rows_html += f"""
        <div class="ledger-row">
            <div class="row-header">
                <span class="row-label">{label}</span>
                <span class="row-share">{m["share"]}%</span>
            </div>
            <div class="bar-track">
                <div class="bar-fill" style="width:{bar_width}%"></div>
            </div>
            <div class="row-stats">
                {m["sets"]} sets &nbsp;·&nbsp; {m["reps"]} reps &nbsp;·&nbsp; {m["tonnage"]:,} lbs
            </div>
            <div class="row-exercises">{exes}</div>
        </div>"""

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Cinzel+Decorative:wght@700&family=Cinzel:wght@400;600;700&family=Share+Tech+Mono&display=swap" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box;}}
body{{width:1080px;height:1080px;overflow:hidden;background:#000;font-family:'Cinzel',serif;}}
.card{{width:1080px;height:1080px;display:grid;grid-template-rows:80px 1fr 600px;position:relative;overflow:hidden;}}
.header{{position:relative;z-index:10;display:flex;align-items:center;justify-content:space-between;padding:0 56px;background:rgba(0,0,0,0.7);border-bottom:2px solid #8b0000;}}
.header-left{{font-family:'Share Tech Mono',monospace;font-size:22px;letter-spacing:5px;color:#cc2200;display:flex;align-items:center;gap:16px;}}
.header-right{{font-family:'Share Tech Mono',monospace;font-size:18px;letter-spacing:3px;color:#555;}}
.art-zone{{position:relative;overflow:hidden;}}
.art{{position:absolute;inset:0;{bg_style}background-size:cover;background-position:center top;background-color:#0a0a0a;}}
.art-mask{{position:absolute;inset:0;background:linear-gradient(to bottom,rgba(0,0,0,0.05) 0%,rgba(0,0,0,0.5) 60%,rgba(0,0,0,1) 100%);}}
.data-zone{{position:relative;z-index:10;display:flex;flex-direction:column;padding:18px 56px 20px 56px;gap:6px;background:rgba(0,0,0,0.65);border-top:1px solid rgba(139,0,0,0.4);overflow:hidden;}}
.ledger-label{{font-family:'Share Tech Mono',monospace;font-size:19px;letter-spacing:6px;color:#cc2200;}}
.window-label{{font-family:'Share Tech Mono',monospace;font-size:15px;letter-spacing:2px;color:#444;}}
.divider{{width:100%;height:1px;background:linear-gradient(to right,rgba(139,0,0,0.6),rgba(139,0,0,0.1));margin:2px 0;}}
.ledger-row{{padding:4px 0;border-bottom:1px solid rgba(255,255,255,0.04);}}
.row-header{{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:2px;}}
.row-label{{font-family:'Share Tech Mono',monospace;font-size:16px;color:#d4c9b0;letter-spacing:2px;}}
.row-share{{font-family:'Share Tech Mono',monospace;font-size:16px;color:#cc2200;}}
.bar-track{{width:100%;height:3px;background:rgba(255,255,255,0.06);margin-bottom:3px;}}
.bar-fill{{height:3px;background:linear-gradient(to right,#8b0000,#cc2200);}}
.row-stats{{font-family:'Share Tech Mono',monospace;font-size:14px;color:#555;margin-bottom:1px;}}
.row-exercises{{font-family:'Share Tech Mono',monospace;font-size:13px;color:#444;}}
.footer{{font-family:'Share Tech Mono',monospace;font-size:17px;letter-spacing:4px;color:#333;text-align:center;margin-top:auto;padding-top:6px;}}
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
      <span>MOVEMENT LEDGER</span>
    </div>
    <div class="header-right">DEADLIFT RADIO</div>
  </div>
  <div class="art-zone">
    <div class="art"></div>
    <div class="art-mask"></div>
  </div>
  <div class="data-zone">
    <div class="ledger-label">&#9632; VOLUME DISTRIBUTION</div>
    <div class="window-label">{ledger["start"]} — {ledger["end"]} &nbsp;·&nbsp; {ledger["total_tonnage"]:,} lbs total</div>
    <div class="divider"></div>
    {rows_html}
    <div class="footer">TRANSMISSION LOGGED</div>
  </div>
</div>
</body>
</html>"""


def render_movement_ledger_card(days=30, db_path=DB_PATH):
    os.makedirs(EXPORT_DIR, exist_ok=True)
    ledger = build_movement_ledger(days=days, db_path=db_path)

    if not ledger["movements"]:
        print("[ledger card] No movement data found.")
        return None

    date_slug = datetime.today().strftime("%Y-%m-%d")
    card_path = os.path.join(EXPORT_DIR, f"movement_ledger_{date_slug}.png")

    context = {"is_summary": True}
    bg_b64 = get_background_base64(context)
    html = build_movement_ledger_card_html(ledger, bg_b64)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1080, "height": 1080})
        page.set_content(html, wait_until="networkidle")
        page.screenshot(path=card_path, clip={"x": 0, "y": 0, "width": 1080, "height": 1080})
        browser.close()

    print(f"[ledger card] Saved -> {card_path}")

    if os.path.isdir(INBOX_PATH):
        shutil.copy2(card_path, os.path.join(INBOX_PATH, os.path.basename(card_path)))
        print(f"[delivery] -> {INBOX_PATH}")

    return card_path


if __name__ == "__main__":
    raw = input("Window in days? (default 30): ").strip()
    days = int(raw) if raw.isdigit() else 30
    render_movement_ledger_card(days=days)
