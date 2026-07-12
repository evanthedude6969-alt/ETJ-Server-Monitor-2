@echo off
title ETJ Server Monitor Setup

echo.
echo ========================================
echo       ETJ SERVER MONITOR SETUP
echo ========================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH.
    pause
    exit /b 1
)

echo Installing requirements...
python -m pip install -r requirements.txt

if not exist .env (
    copy .env.example .env
    echo.
    echo ========================================
    echo IMPORTANT
    echo ========================================
    echo .env has been created.
    echo Add your Jellyfin API key to .env.
    echo.
    notepad .env
)

echo.
echo Starting ETJ Server Monitor...
echo Open http://127.0.0.1:5000
echo.

python app.py

pause
