# TASK: Workout Sonnet Summary

## FILES: reports/card.py, utils/llm_summary.py (NEW)

After a workout session is logged, generate a short poetic summary
written in the style of a Shakespearean sonnet — 14 lines, iambic
feel, grimdark/iron tone matching the rest of Deadlift Radio's voice.

## Implementation

Create utils/llm_summary.py:
- Function: generate_workout_sonnet(session_data: dict) -> str
- Builds a prompt from session_data fields:
  - date, exercises, total tonnage, top set, PR flags
- Calls Ollama REST API directly (no new dependencies):
  POST http://localhost:11434/api/generate
  model: qwen2.5-coder:32b-instruct-q4_K_M
- Returns the sonnet as a plain string
- Falls back to a default grimdark haiku if Ollama is unreachable

Prompt template:
"You are a grimdark poet. Write a 14-line Shakespearean sonnet
summarizing this workout. Tone: iron, suffering, glory.
Session: {date}, Exercises: {exercises}, Tonnage: {tonnage}kg,
Top set: {top_set}, PRs: {prs}. Return only the sonnet, no preamble."

In reports/card.py:
- After session card is generated, call generate_workout_sonnet()
- Print the sonnet to stdout at the end of the session report
- Also save it to exports/{date}_sonnet.txt

## RULES
- Use only requests library (already installed)
- Do not break existing card generation
- Wrap Ollama call in try/except with fallback
- Keep utils/llm_summary.py under 60 lines
