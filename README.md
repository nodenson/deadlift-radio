# Deadlift Radio

> Build → Record → Analyze → Ascend

A terminal-based strength intelligence system for serious lifters.
Deadlift Radio logs workouts, preserves training history, and analyzes
tonnage, fatigue, readiness, and progression over time.

---

## Features

- Log workouts from raw terminal input — no forms, no friction
- Parse exercise names, sets, reps, and load automatically
- Track estimated 1RM progression per exercise
- Weekly tonnage, push/pull balance, and workload change reports
- Fatigue analysis with training signals and recommendations
- Readiness score — GREEN / YELLOW / RED before every session
- Joint and tendon exposure tracking for injury prevention
- Export sessions to Markdown
- Generate strength progress graphs and training heatmaps
- SQLite storage — no dependencies, no cloud, no bullshit

---

## Structure
```
deadlift-radio/
├── main.py                  # Entry point
├── db/                      # Schema and query layer
├── ingestion/               # Workout log parser and ingest engine
├── analytics/               # Tonnage, fatigue, readiness, exposure
├── reports/                 # Graphs and markdown export
├── cli/                     # Menu and display layer
├── classification/          # Movement and exercise classification
├── utils/                   # Spinner and shared utilities
└── exports/                 # Generated graphs and session reports
```

---

## Run
```bash
python3 main.py
```

## Example Input
```
March 13 2026
BW 185

Bench
135 x 8
185 x 5
225 x 3
245 x 1

T bar rows empty chest supported
90 x 10 x 4

Hammer curls db
35 x 12 x 3
```

---

## Vision

Deadlift Radio is the data layer for a larger strength media system.
Future modules: AI session summaries, automated video briefings, and
social media exports via the AI Media Lab pipeline.