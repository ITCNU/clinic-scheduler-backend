#!/usr/bin/env python3
"""
Startup script for Render deployment
Runs migrations and data migration before starting the FastAPI app
"""

import os
import sys
import subprocess
import time

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        if e.stderr:
            print(f"Error: {e.stderr}")
        return False

def main():
    """Main startup process"""
    print("🚀 Starting CNU Dental Clinic Scheduler...")
    
    # Step 1: Run database migrations
    if not run_command("python migrate.py", "Database migration"):
        print("⚠️  Database migration failed, but continuing...")
    
    # Step 2: Test database connection
    if not run_command("python test_db.py", "Database connection test"):
        print("⚠️  Database connection test failed, but continuing...")
    
    # Step 3: Import data from JSON files (if they exist)
    if os.path.exists("data/users.json"):
        if not run_command("python import_data.py", "Data import from JSON files"):
            print("⚠️  Data import failed, but continuing...")
    else:
        print("ℹ️  No data files found, skipping data import")
    
    # Step 3: Start the FastAPI application
    print("🌐 Starting FastAPI application...")
    start_command = "uvicorn app.main:app --host 0.0.0.0 --port $PORT"
    
    # Replace $PORT with actual port
    port = os.getenv("PORT", "8000")
    start_command = start_command.replace("$PORT", port)
    
    print(f"🚀 Starting server on port {port}...")
    
    # Start the server
    try:
        subprocess.run(start_command, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to start server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
