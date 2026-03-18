TASK: Add scheduled OpenClaw scout runner

FILES: openclaw/scheduler.py (NEW FILE)

Create openclaw/scheduler.py that:
1. Reads a list of queries from openclaw/scout_queries.txt (one per line)
2. Runs each query through ScoutRunner with YouTubeProvider
3. Saves results to DB (already handled by runner)
4. Writes a summary to openclaw/schedule_log.txt with timestamp
5. Can be called from cron

Also create openclaw/scout_queries.txt with these default queries:
deadlift, powerlifting
bodybuilding, hypertrophy
strength training, barbell
climbing, bouldering

Usage: python -m openclaw.scheduler

RULES:
- No new dependencies
- Must run without user input
- Must handle API errors gracefully and continue to next query
- Log all runs with timestamps
