#!/bin/bash

echo "Starting Clinic Scheduler Server..."
echo ""
echo "Make sure all dependencies are installed:"
echo "pip install -r requirements.txt"
echo ""
echo "Server will be accessible at:"
echo "http://[YOUR_IP]:8000"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Python3 not found. Please install Python 3.8 or higher."
    exit 1
fi

# Check if requirements are installed
if ! python3 -c "import uvicorn, fastapi" &> /dev/null; then
    echo "Dependencies not found. Installing..."
    pip3 install -r requirements.txt
fi

# Start the server
python3 run_production.py
