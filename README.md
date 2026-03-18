# Deadlift Radio / OpenClaw / Iron Forge

A local-first, sovereign AI stack for strength intelligence, social scouting, and autonomous research.

## Systems

### Deadlift Radio
Personal strength logging and analytics engine. Freehand workout log ingestion, SQLite storage, session cards, PR tracking, fatigue analysis, bodyweight trend.

### OpenClaw
Social intelligence scout. YouTube provider live, creator scoring, intelligence briefs. Apify/Instagram stubs ready for expansion.

### Iron Forge (Research Engine) — IN DESIGN
Autonomous research pipeline. Staged intake → retrieval → analysis → dossier → lessons learned. Modular skills layer. Local-first execution.

## Stack
- Python 3.10, SQLite, Playwright
- Ollama (local LLM — llama3.1:70b primary)
- Groq free tier (fallback)
- Aider (coding agent, constrained mode)

## Compute priority
1. Local Ollama (4x RTX 3060 Ti, 32GB VRAM)
2. Groq free tier
3. Paid APIs (last resort only)

## Quick start
```bash
cd ~/deadlift_radio
export $(cat .env | xargs)
python main.py          # Deadlift Radio CLI
python -m openclaw.main scout "query"  # OpenClaw scout
```

## Aider (safe mode)
```bash
bash aider_safe.sh ollama/llama3.1:70b
```

## Design rules
- Open source / free tier first
- Local hardware before cloud
- No auto-commits without review
- No parent directory access
- Audit log all agent sessions
- Secrets in .env only, never committed
