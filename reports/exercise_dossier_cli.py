# /home/bune/deadlift_radio/reports/exercise_dossier_cli.py

def format_load(n):
    if n is None:
        return "-"
    return int(n) if isinstance(n, float) and n == int(n) else round(n, 1)


def print_exercise_dossier(dossier: dict) -> None:
    if not dossier:
        print("\nNo historical entries found for this exercise.")
        return

    print("\n+++ EXERCISE DOSSIER +++")
    print(f"\nExercise: {dossier['exercise_name']}")
    print(f"Last seen: {dossier['last_seen'] or 'unknown'}")

    print(f"\n30-day archive window")
    print(f"Appearances: {dossier['appearances_30d']}")
    print(f"Volume: {format_load(dossier['volume_30d'])} lbs")

    if dossier["best_set"]:
        bs = dossier["best_set"]
        print(f"\nBest observed set: {format_load(bs['load'])} x {bs['reps']}")
    else:
        print("\nBest observed set: -")

    print(f"Best estimated 1RM: {format_load(dossier['best_e1rm'])}")

    print(f"\nRecent appearances:")
    if not dossier["recent"]:
        print("  None recorded.")
    else:
        for r in dossier["recent"]:
            print(
                f"  {r['date']} | "
                f"top {format_load(r['top_load'])} x {r['top_reps']} | "
                f"tonnage {format_load(r['tonnage'])} | "
                f"e1RM {format_load(r['e1rm'])}"
            )

    print(f"\nArchive status: {dossier['status']}")
