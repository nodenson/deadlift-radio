# /home/bune/deadlift_radio/reports/movement_ledger_cli.py


def print_movement_ledger(ledger: dict) -> None:
    movements = ledger.get("movements", [])

    print("\n+++ MOVEMENT LEDGER +++")
    print(f"Window: {ledger['start']} to {ledger['end']} ({ledger['days']} days)")
    print(f"Total tonnage: {ledger.get('total_tonnage', 0):,} lbs\n")

    if not movements:
        print("No movement data found in this window.")
        return

    for i, m in enumerate(movements, 1):
        print(f"{i}. {m['movement'].upper().replace('_', ' ')}")
        print(f"   Sets: {m['sets']}  Reps: {m['reps']}  Tonnage: {m['tonnage']:,} lbs  ({m['share']}% of volume)")
        if m["top_exercises"]:
            print(f"   Exercises: {', '.join(m['top_exercises'])}")
        print()
