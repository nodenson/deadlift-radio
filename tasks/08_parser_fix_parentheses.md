# TASK: Fix parser choking on parentheses in exercise names

## FILES: ingestion/parser.py

## Problem
Exercise names with parentheses get truncated or orphaned during ingestion.
Examples:
- "Lat Pulldowns (Wide)" → sets orphaned, exercise not logged
- "T-Bar Rows (Inside Grip)" → truncated to just "T"

## Goal
Parser should handle parentheses in exercise names without breaking.

## Rules
- Do not break existing parsing logic
- All changes wrapped in try/except
- Test with: Lat Pulldowns (Wide), T-Bar Rows (Inside Grip), Rear Delt Flies (Reverse Grip)
