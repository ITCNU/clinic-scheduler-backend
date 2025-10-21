@echo off
echo === Clinic Scheduler Update Script ===
echo.

REM Check if server is running
tasklist /FI "IMAGENAME eq python.exe" /FI "WINDOWTITLE eq *run*" 2>NUL | find /I "python.exe" >NUL
if %ERRORLEVEL% == 0 (
    echo Server is currently running. Stopping...
    taskkill /F /IM python.exe
    timeout /t 3 /nobreak >NUL
    echo Server stopped.
) else (
    echo No server currently running.
)

echo.
echo Starting updated server...

REM Start the server
start /B python run_production.py > server.log 2>&1

REM Wait a moment
timeout /t 2 /nobreak >NUL

REM Check if server started
tasklist /FI "IMAGENAME eq python.exe" 2>NUL | find /I "python.exe" >NUL
if %ERRORLEVEL% == 0 (
    echo ✅ Server started successfully!
    echo 📝 Logs are being written to server.log
    echo 🌐 Access the application at: http://localhost:8000
) else (
    echo ❌ Failed to start server. Check server.log for errors.
    pause
    exit /b 1
)

echo.
echo === Update Complete ===
pause
