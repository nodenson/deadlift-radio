# /home/bune/deadlift_radio/reports/archive_timeline_cli.py


def print_timeline(timeline: dict) -> None:
    entries = timeline.get("entries", [])
    if not entries:
        print("\n+++ ARCHIVE TIMELINE +++")
        print("No sessions found.")
        return

    print("\n+++ ARCHIVE TIMELINE +++")
    print(f"Retrieving last {timeline['limit']} session(s)\n")

    for e in entries:
        pr_tag = "  [PR]" if e["pr"] else ""
        bw = f"  bw {e['bodyweight']} lbs" if e["bodyweight"] else ""
        print(f"--- {e['date']}{pr_tag}{bw}")
        print(f"    Sets: {e['total_sets']}  Reps: {e['total_reps']}  Tonnage: {e['tonnage']:,} lbs")
        if e["top_lifts"]:
            print(f"    Top lifts: {'  |  '.join(e['top_lifts'])}")
        print()
