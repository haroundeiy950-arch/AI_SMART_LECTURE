@echo off
title Face Recognition Security System
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo Python was not found. Install Python 3.11, 3.12 or 3.13.
        pause
        exit /b 1
    )
)

call ".venv\Scripts\activate.bat"

echo Updating pip...
python -m pip install --upgrade pip

echo Installing requirements...
python -m pip uninstall -y opencv-python opencv-python-headless opencv-contrib-python-headless >nul 2>&1
python -m pip install -r requirements.txt

echo Starting application...
python main.py
pause
