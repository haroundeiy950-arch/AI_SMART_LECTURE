@echo off
setlocal
cd /d "%~dp0"

if not exist venv311\Scripts\python.exe (
  echo Creating Python 3.11 virtual environment...
  py -3.11 -m venv venv311
)

call venv311\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if not exist .env copy .env.example .env >nul

echo.
echo =============================================
echo Smart AI Glasses Web
 echo Open: http://localhost:8000
 echo Username: admin
 echo Initial password: ChangeMe@12345
 echo =============================================
python run.py
pause
