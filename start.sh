#!/bin/bash
cd /home/bune/deadlift_radio
source venv/bin/activate

echo "Starting Deadlift Radio..."

# Kill anything already on these ports
kill $(lsof -t -i:8000) 2>/dev/null
kill $(lsof -t -i:8001) 2>/dev/null

# Start API in background
uvicorn api.server:app --host 0.0.0.0 --port 8000 &
echo "✓ API running on port 8000"

# Start Dashboard in background  
uvicorn dashboard.app:app --host 0.0.0.0 --port 8001 &
echo "✓ Dashboard running at http://localhost:8001"

# Start Expo
cd mobile
echo "✓ Starting Expo..."
npx expo start
