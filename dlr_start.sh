#!/bin/bash
cd ~/deadlift_radio && source venv/bin/activate

echo "[1/2] Starting API server..."
uvicorn api.server:app --host 0.0.0.0 --port 8000 &
API_PID=$!
echo "API PID: $API_PID"

echo "[2/2] Starting dashboard..."
uvicorn dashboard.app:app --host 0.0.0.0 --port 8001 &
DASH_PID=$!
echo "Dashboard PID: $DASH_PID"

echo "$API_PID $DASH_PID" > /tmp/dlr_pids.txt
echo "Done. API: :8000  Dashboard: :8001"
echo "Run dlr_stop.sh to kill both."
