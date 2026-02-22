@echo off
:: Windows double-click launcher for Source Monitor.
cd /d "%~dp0"

if exist "venv\Scripts\python.exe" (
    venv\Scripts\python.exe launch.py
) else (
    python launch.py
)
pause
