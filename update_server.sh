#!/bin/bash

# Deployment script for updating the clinic scheduler

echo "=== Clinic Scheduler Update Script ==="
echo ""

# Check if server is running
if pgrep -f "python.*run" > /dev/null; then
    echo "Server is currently running. Stopping..."
    pkill -f "python.*run"
    sleep 3
    echo "Server stopped."
else
    echo "No server currently running."
fi

echo ""
echo "Starting updated server..."

# Start the server in background
nohup python run_production.py > server.log 2>&1 &

# Wait a moment for server to start
sleep 2

# Check if server started successfully
if pgrep -f "python.*run" > /dev/null; then
    echo "✅ Server started successfully!"
    echo "📝 Logs are being written to server.log"
    echo "🌐 Access the application at: http://$(hostname -I | awk '{print $1}'):8000"
else
    echo "❌ Failed to start server. Check server.log for errors."
    exit 1
fi

echo ""
echo "=== Update Complete ==="
