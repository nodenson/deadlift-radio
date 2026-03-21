# TASK: Program Loader — Protocols Feature

## Priority: High
## Module: supabase/ + mobile/
## Status: Redirected — build in Supabase/mobile, not Python CLI

## Decision
Antigravity already built a Protocols table and Today screen shell.
The program loader lives here, not in a Python programs/ module.

## Schema additions needed (supabase/migrations/01_protocols.sql)
- protocol_weeks (protocol_id, week_number)
- protocol_days (week_id, day_number, label)
- prescribed_sets (day_id, exercise, sets, reps, load, notes)
- protocol_enrollments (protocol_id, user_id, start_date, active)

## Mobile work needed
- Today screen: fetch active enrollment, calculate current day, show prescribed sets
- Protocols screen: list available protocols, enroll button
- Post-session: compare logged vs prescribed

## Import
- CSV importer script (Python or Node) to load Joe's program into Supabase
- Columns: week, day, exercise, sets, reps, load, notes

## Next action
Export Joe's program from Google Sheets as CSV, then build the migration and importer.
