@echo off
setlocal
cd /d "%~dp0"


if not exist "backend\.venv\Scripts\python.exe" (
  echo Creating virtual environment...
  where py >nul 2>&1 && (py -m venv backend\.venv) || (python -m venv backend\.venv)
  cd /d backend
  .venv\Scripts\python.exe -m pip install -r requirements.txt
  cd /d ..
)

start "Backend" cmd /k "cd /d backend && .venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000"

start "Frontend" cmd /k "cd /d "mik frontend" && python -m http.server 8080"

timeout /t 3 >nul
start "" http://localhost:8080/loginpag/login.html

exit /b 0
