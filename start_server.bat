@echo off
echo Starting Clinic Scheduler Server...
echo.
echo Make sure all dependencies are installed:
echo pip install -r requirements.txt
echo.
echo Server will be accessible at:
echo http://[YOUR_IP]:8000
echo.
echo Press Ctrl+C to stop the server
echo.
python run_production.py
pause
