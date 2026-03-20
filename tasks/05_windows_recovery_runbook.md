# TASK: Windows Dev Environment — Fast Recovery Runbook

## Priority: Medium
## Project: Infrastructure / Productivity
## Status: Not started

---

## Problem
When the Windows workstation (RTX 3090 / brain) restarts or crashes, the local AI stack
goes offline and aider on Ubuntu stalls waiting for the model. Recovery currently takes
too long because the steps aren't documented.

---

## Goal
Create a startup runbook and optionally automate Ollama startup so the brain comes back
online in under 2 minutes after any Windows reboot.

---

## Files to Create
- `OPERATIONS.md` in a new `infra/` repo or appended to deadlift-radio repo
- Optional: Windows Task Scheduler entry or startup script for Ollama

---

## Recovery Steps (Current Manual Process)
Document and automate these steps:

1. **Ollama auto-start on Windows boot**
   - Create a Windows Task Scheduler task that runs `ollama serve` on login
   - Or place a shortcut in `shell:startup` folder
   - Verify: `ollama list` returns models within 60s of login

2. **OLLAMA_HOST env var persistence**
   - Already set at Machine level via registry — survives reboots
   - Verify after reboot: `[System.Environment]::GetEnvironmentVariable("OLLAMA_HOST", "Machine")`
   - Expected: `0.0.0.0:11434`

3. **Firewall rule persistence**
   - Already set via Windows Defender GUI — survives reboots
   - Verify: `netstat -an | Select-String "11434"` shows `0.0.0.0:11434 LISTENING`

4. **Ubuntu aider recovery**
   - If aider was mid-task when brain went offline, Ctrl+C and relaunch
   - Always relaunch with: `export OLLAMA_API_BASE=http://192.168.1.2:11434`
   - Check git diff before relaunching to see what completed before crash

5. **Verify brain is reachable from Ubuntu**
   - `curl http://192.168.1.2:11434/api/tags`
   - Should return model list with qwen2.5-coder:32b-instruct-q4_K_M

---

## Automation Opportunity
Create a Windows startup script `start_brain.ps1`:

```powershell
# start_brain.ps1 — Run on Windows login to bring up the AI stack
$env:OLLAMA_HOST = "0.0.0.0:11434"
Start-Process "ollama" -ArgumentList "serve" -WindowStyle Hidden
Write-Host "Ollama started. Brain is online."
```

Add to Task Scheduler:
- Trigger: At log on
- Action: `powershell -File C:\Users\bradf\start_brain.ps1`
- Run with highest privileges: No (not needed)

---

## Future Improvements
- Health check script on Ubuntu that pings brain and alerts if down
- Auto-reconnect aider session after brain comes back
- `.aider.conf.yml` committed to each repo so model config is never lost
- Consider Tailscale for brain access when off LAN

---

## Related
- Architecture: Windows (brain) + Ubuntu (execution) + aider (agent)
- Brain IP: 192.168.1.2
- Model: qwen2.5-coder:32b-instruct-q4_K_M (19GB, Q4_K_M)
- Ollama port: 11434
