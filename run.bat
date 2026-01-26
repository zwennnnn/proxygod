@echo off
title ProxyGod Launcher
echo Checking for Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python not found! Please install Python from https://python.org
    pause
    exit
)

echo Installing/Updating Dependencies...
python -m pip install -r requirements.txt >nul 2>&1

echo Starting ProxyGod...
python main.py
pause
