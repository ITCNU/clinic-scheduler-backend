@echo off
REM Render Deployment Script for Clinic Scheduler (Windows)
REM This script helps you deploy your app to Render

echo 🚀 Clinic Scheduler - Render Deployment Script
echo ==============================================

REM Check if git is initialized
if not exist ".git" (
    echo ❌ Git repository not initialized. Please run:
    echo    git init
    echo    git add .
    echo    git commit -m "Initial commit"
    pause
    exit /b 1
)

REM Check if files are staged
git status --porcelain > temp_status.txt
if %errorlevel% neq 0 (
    echo ❌ Error checking git status
    pause
    exit /b 1
)

for /f %%i in (temp_status.txt) do (
    echo 📝 Staging changes...
    git add .
    
    echo 💾 Committing changes...
    git commit -m "Prepare for Render deployment"
    goto :push
)

echo ✅ No changes to commit

:push
del temp_status.txt 2>nul

REM Check if remote origin exists
git remote get-url origin >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ No GitHub remote configured. Please:
    echo    1. Create a repository on GitHub
    echo    2. Run: git remote add origin https://github.com/yourusername/your-repo.git
    echo    3. Run: git push -u origin main
    pause
    exit /b 1
)

REM Push to GitHub
echo 📤 Pushing to GitHub...
git push origin main

echo.
echo ✅ Code pushed to GitHub successfully!
echo.
echo 🎯 Next Steps:
echo 1. Go to https://render.com
echo 2. Sign up/Login with your GitHub account
echo 3. Click "New +" → "Web Service"
echo 4. Connect your GitHub repository
echo 5. Use these settings:
echo    - Name: clinic-scheduler
echo    - Environment: Python 3
echo    - Build Command: pip install -r requirements.txt ^&^& python migrate.py
echo    - Start Command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
echo    - Plan: Free
echo.
echo 6. Create a PostgreSQL database:
echo    - Click "New +" → "PostgreSQL"
echo    - Name: clinic-scheduler-db
echo    - Plan: Free
echo.
echo 7. Add environment variables in your web service:
echo    - DATABASE_URL: (copy from your PostgreSQL service)
echo    - SECRET_KEY: (generate a strong secret key)
echo    - DEBUG: False
echo.
echo 8. Deploy and test your application!
echo.
echo 📚 For detailed instructions, see RENDER_DEPLOYMENT_GUIDE.md
pause
