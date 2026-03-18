import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from .models import RawScoutItem, ScoredItem
from .scoring import score_items, DEFAULT_WEIGHTS
from .report import build_report, report_to_dict, format_brief
from ..db.scout_schema import (
    get_connection, init_schema, get_db_path,
    save_run, save_item, upsert_creator,
    get_recent_runs, get_top_creators,
)

def make_run_id():
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    return f"scout_{now}_{str(uuid.uuid4())[:6]}"

class ScoutRunner:
    def __init__(self, provider, weights=None, db_path=None):
        self.provider = provider
        self.weights = weights or DEFAULT_WEIGHTS
        self.db_path = db_path or get_db_path()
        init_schema(self.db_path)

    def run(self, query, limit=20, top_n=10):
        run_id = make_run_id()
        print(f"[openclaw] run_id:    {run_id}")
        print(f"[openclaw] query:     {query}")
        print(f"[openclaw] provider:  {self.provider.name}")
        print(f"[openclaw] fetching...")
        raw_items = self.provider.search(query, limit=limit)
        print(f"[openclaw] got {len(raw_items)} items")
        scored = score_items(raw_items, query, run_id, self.weights)
        report = build_report(run_id, query, self.provider.name, scored, top_n=top_n)
        brief = format_brief(report)
        report_dict = report_to_dict(report)
        print(f"[openclaw] persisting to {self.db_path}...")
        conn = get_connection(self.db_path)
        try:
            save_run(conn, run_id, query, self.provider.name,
                     report.generated_at, report.total_items, json.dumps(report_dict))
            for si in scored:
                save_item(conn, run_id, query, si.item, si)
            for profile in report.creator_profiles:
                upsert_creator(conn, profile)
            conn.commit()
            print(f"[openclaw] saved {len(scored)} items, {len(report.creator_profiles)} creators")
        finally:
            conn.close()
        return {"run_id": run_id, "report": report, "report_dict": report_dict, "brief": brief}

    def recent_runs(self, limit=10):
        conn = get_connection(self.db_path)
        try:
            return get_recent_runs(conn, limit)
        finally:
            conn.close()

    def top_creators(self, limit=20):
        conn = get_connection(self.db_path)
        try:
            return get_top_creators(conn, limit)
        finally:
            conn.close()

    def print_top_creators(self, limit=20):
        rows = self.top_creators(limit)
        if not rows:
            print("No creators yet. Run a scout first.")
            return
        print("\n── TOP CREATORS (all-time) ──")
        for r in rows:
            print(f"  {r['handle']} ({r['platform']}) | avg: {r['avg_score']:.2f} | appearances: {r['total_appearances']} | {r['followers']:,} followers")

    def print_recent_runs(self, limit=10):
        rows = self.recent_runs(limit)
        if not rows:
            print("No scout runs yet.")
            return
        print("\n── RECENT SCOUT RUNS ──")
        for r in rows:
            print(f"  {r['run_id']} | query: \"{r['query']}\' | {r['total_items']} items | {r['generated_at']}")
