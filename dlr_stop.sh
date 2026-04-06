#!/bin/bash
if [ -f /tmp/dlr_pids.txt ]; then
    kill $(cat /tmp/dlr_pids.txt) 2>/dev/null
    rm /tmp/dlr_pids.txt
    echo "Stopped."
else
    pkill -f "uvicorn api.server" && pkill -f "uvicorn dashboard.app"
    echo "Stopped via pkill."
fi
