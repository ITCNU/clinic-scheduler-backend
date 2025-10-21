@echo off
echo Clinic Scheduler Database Browser
echo ================================
echo.
echo Choose an option:
echo 1. Show all tables
echo 2. Show user statistics
echo 3. Show schedule statistics
echo 4. Interactive mode
echo 5. View specific table data
echo.
set /p choice="Enter your choice (1-5): "

if "%choice%"=="1" (
    python db_browser.py tables
) else if "%choice%"=="2" (
    python db_browser.py users
) else if "%choice%"=="3" (
    python db_browser.py schedule
) else if "%choice%"=="4" (
    python db_browser.py
) else if "%choice%"=="5" (
    set /p table="Enter table name: "
    set /p limit="Enter limit (default 10): "
    if "%limit%"=="" set limit=10
    python db_browser.py data %table% %limit%
) else (
    echo Invalid choice
)

echo.
pause
