# TASK: Self-Hosted Agent Web UI

## Priority: Medium
## Status: Not started

## Goal
Simple web UI on Ubuntu server that accepts natural language tasks
and runs aider against the local Ollama model on the 3090.
Accessible from phone via browser over LAN or Tailscale.

## Stack
- Flask or FastAPI (Python, already in venv)
- Simple textarea input + submit button
- Spawns aider subprocess with task as --message
- Streams output back to browser
- No auth needed on LAN (add Tailscale for remote access)

## Architecture
Phone browser → Ubuntu :5000 → aider → Ollama 192.168.1.2:11434

## Rules
- No new dependencies beyond Flask
- Single file app (server.py)
- Repo: deadlift-radio or new infra repo
- Zero cloud tokens
