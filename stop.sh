#!/bin/bash
echo "Stopping Deadlift Radio..."
kill $(lsof -t -i:8000) 2>/dev/null && echo "✓ API stopped" || echo "- API was not running"
kill $(lsof -t -i:8001) 2>/dev/null && echo "✓ Dashboard stopped" || echo "- Dashboard was not running"
kill $(lsof -t -i:8081) 2>/dev/null && echo "✓ Expo stopped" || echo "- Expo was not running"
echo "Done."
