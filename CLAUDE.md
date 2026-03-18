# Deadlift Radio + OpenClaw

## What this is
Personal strength logging system (Deadlift Radio) + social intelligence scout (OpenClaw).
Local-first, CLI-driven, SQLite backend, Python 3.10.

## Design philosophy
1. Local hardware first (Ollama on this server)
2. Free API tiers second (Groq, YouTube API)
3. Paid APIs last (Anthropic, OpenAI, Apify)
Always build open source path before paid path.

## Server
- robotchickenman: i7-2600, 8 cores, 7.6GB RAM, Ubuntu
- Garage server: 4x 3060 Ti, Ollama, heavy compute
- Ollama models available: llama3.2, qwen3, llama3, gemma3

## Key files
- main.py — entry point, runs CLI menu
- cli/menu.py — all menu options, main interaction loop
- ingestion/ingest.py — workout log parsing and DB insert
- ingestion/parser.py — regex parsers for set/rep/weight formats
- classification/movements.py — exercise name normalization and aliases
- analytics/ — tonnage, fatigue, exposure, bodyweight, dossier, timeline
- reports/ — Playwright PNG cards, CLI print views, markdown export
- openclaw/ — social intelligence scout, YouTube provider, scoring, briefs
- db/schema.py — DB_PATH, init_db (uses archive_dev.db)

## Database
- Primary: archive_dev.db (in project root)
- Tables: sessions, exercises, sets, exposures, personal_records
- OpenClaw tables: scout_runs, scout_items, scout_creators

## Environment variables (.env, never commit)
- YOUTUBE_API_KEY
- GROQ_API_KEY
- ANTHROPIC_API_KEY
- APIFY_API_TOKEN

## Current state (March 2026)
- Parser handles: plate notation, bodyweight sets, freehand exercise names
- Preamble auto-detection working (no # required)
- Exercise aliases: leg press, hamstring curl, leg extension, bulgarian split squat
- Bodyweight trend tracking (menu option 27)
- OpenClaw YouTube scout live, scoring working, recency fixed
- Aider installed, connected to Groq free tier

## Known debt
- Exercise alias DB table not built yet
- No AI preprocessing for parser (use Groq/Ollama when ready)
- No scheduled/automated scout runs
- No test suite
- .pre_* backup files in root need cleanup

## Aider usage
aider --model groq/llama-3.3-70b-versatile --no-auto-commits
Use for simple, well-scoped tasks only.
Complex refactors: use Claude chat with full context.

## Compute priority for LLM features
1. Ollama local (llama3.2 for speed, qwen3 for reasoning)
2. Groq free tier (llama-3.3-70b-versatile)
3. Anthropic Claude (paid, last resort)

## Planned: Provider Intelligence Registry
Track all LLM/API providers, free tier limits, model capabilities.
Auto-select best provider per task. Alert on new free offerings.
Lives in openclaw/providers/registry.py
Sources: provider docs, HuggingFace, Together.ai, Fireworks, Groq, Mistral, Cohere

## Iron Forge (Research Engine) — planned
Autonomous research pipeline. Same functional class as AutoResearchClaw but our own product.
Stages: intake → scope check → plan → source discovery → retrieval → extraction → analysis → review → synthesis → artifacts → lessons → archive
Output artifacts per run: dossier.md, brief.md, source_map.json, risk_register.json, tasks.md, lessons_learned.json, eval_report.json
Lives in: iron_forge/

## Skills Layer — planned
Modular reusable procedural skills. Inspired by agentskills.io pattern.
Lives in: skills/
Categories: research/, coding/, security/, ops/, content/, product/
Each skill: metadata header + content body + version + provenance

## Agent rules (non-negotiable)
- Constrained to repo directory only
- No parent directory access
- No auto-commit without review
- No URL fetching unless explicitly allowed
- Audit log all sessions in .aider_sessions/
- Secrets from .env only
